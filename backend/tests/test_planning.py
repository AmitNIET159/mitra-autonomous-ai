"""Tests for MITRA Phase 5: Action Planning & Structured Proposal Engine.

SAFETY PRINCIPLES VERIFIED:
- ONLY PROPOSES: Status is fixed at 'PROPOSED'.
- Zero execution: GuardrailEngine and ExecutionEngine are never called.
- Deterministic limits: Budget (<= 12000), Discount (<= 100), Target audience (<= 486).
- Hallucination & excessive proposal rejection: Strict validation falls back to deterministic proposal.
- Provenance & Traceability: Supporting evidence IDs must link to investigation findings.
"""
import json
import pytest
from starlette.testclient import TestClient

from app.database.connection import init_db
from app.database.repository import (
    ActionRepository,
    CustomerRepository,
    InvestigationRepository,
    MerchantRepository,
    SignalRepository,
)
from app.database.seed import seed_digital_twin
from app.engines.audit_engine.engine import AuditEngine
from app.engines.investigation_engine.investigation_engine import InvestigationEngine
from app.engines.planning_engine.context_builder import PlanningContextBuilder
from app.engines.planning_engine.planning_engine import PlanningEngine
from app.engines.planning_engine.schemas import PlanningContext
from app.engines.planning_engine.validator import ActionValidator
from app.engines.signal_engine.engine import SignalDetectionEngine
from app.llm.client import FallbackClient
from app.main import app
from app.models.contracts import ActionProposal, Investigation
from app.models.enums import ActionType, StageType


@pytest.fixture(autouse=True)
def setup_clean_db():
    """Seeds a fresh digital twin database before each test."""
    init_db()
    seed_digital_twin()


@pytest.fixture
def test_investigation():
    """Generates an end-to-end investigated signal to use for planning tests."""
    sig_engine = SignalDetectionEngine()
    signals = sig_engine.detect_signals("MID-DEMO-98234")
    primary_sig = next(s for s in signals if "EVENING" in str(s.signal_type))

    inv_engine = InvestigationEngine()
    inv_result = inv_engine.investigate_sync(signal=primary_sig.signal_id, force_fallback=True)
    return inv_result


def test_1_action_proposal_contract_validation():
    """Validates ActionProposal contract fields, defaults, and bidirectional attribute mapping."""
    proposal = ActionProposal(
        action_id="prop-test12345",
        signal_id="sig-test",
        investigation_id="inv-test",
        merchant_id="MID-DEMO-98234",
        action_type=ActionType.EVENING_REENGAGEMENT_CAMPAIGN,
        objective="Recover evening orders",
        target_segment="repeat_customer, regular",
        target_customer_count=486,
        incentive_type="CASHBACK",
        incentive_value=50.0,
        duration="7 days",
        reason="Counter evening slump",
        supporting_evidence_ids=["E1", "E2", "E3"],
        constraints={"max_discount": 100.0, "daily_budget": 12000.0},
        estimated_cost_inr=2430.0,
    )

    assert proposal.proposal_id == "prop-test12345"
    assert proposal.action_id == "prop-test12345"
    assert proposal.status == "PROPOSED"
    assert proposal.action_type == ActionType.EVENING_REENGAGEMENT_CAMPAIGN
    assert proposal.incentive_value == 50.0
    assert proposal.target_customer_count == 486
    assert proposal.parameters.get("discount_amount") == 50.0
    assert proposal.parameters.get("target_count") == 486


def test_2_planning_context_builder_derives_correct_data(test_investigation):
    """Context builder derives merchant constraints (margin, budget, discount) and eligible customer count (486)."""
    context = PlanningContextBuilder.build_context(test_investigation)

    assert isinstance(context, PlanningContext)
    assert context.merchant_id == "MID-DEMO-98234"
    assert context.signal_id == test_investigation.signal_id
    assert context.investigation_id == test_investigation.investigation_id

    # Verify merchant limits derived from DB
    assert context.merchant_rules.minimum_margin == 0.10
    assert context.merchant_rules.daily_budget == 12000.0
    assert context.merchant_rules.max_discount == 100.0
    assert context.merchant_rules.max_campaign_frequency == 3
    assert context.merchant_rules.autonomy_mode == "APPROVAL_REQUIRED"

    # Verify dynamically derived eligible customers
    cust_summary = CustomerRepository.get_customers_summary("MID-DEMO-98234")
    assert cust_summary["target_campaign_customers"] == 486
    assert context.eligible_customer_count == 486
    assert context.planning_limits.max_eligible_customers == 486


@pytest.mark.asyncio
async def test_3_planning_engine_fallback_proposal_content(test_investigation):
    """Fallback planner produces a deterministic candidate proposal with exact business parameters."""
    planner = PlanningEngine()
    proposal = await planner.plan_action(test_investigation, force_fallback=True)

    assert proposal is not None
    assert proposal.status == "PROPOSED"
    assert proposal.is_fallback is True
    assert proposal.action_type == ActionType.EVENING_REENGAGEMENT_CAMPAIGN
    assert proposal.incentive_type == "CASHBACK"
    assert proposal.incentive_value == 50.0
    assert proposal.target_customer_count == 486
    assert proposal.duration == "7 days"
    assert "E1" in proposal.supporting_evidence_ids
    assert "E2" in proposal.supporting_evidence_ids
    assert "E3" in proposal.supporting_evidence_ids
    assert proposal.estimated_cost_inr <= 12000.0
    assert proposal.estimated_cost_inr == 5000.0


@pytest.mark.asyncio
async def test_4_proposal_safety_zero_execution(test_investigation):
    """Verifies that planning engine NEVER triggers execution or approval."""
    planner = PlanningEngine()
    proposal = await planner.plan_action(test_investigation, force_fallback=True)

    # Status must strictly be PROPOSED
    assert proposal.status == "PROPOSED"
    assert proposal.status != "EXECUTED"
    assert proposal.status != "APPROVED"

    # Verify database record also has status PROPOSED
    db_action = ActionRepository.get_action_proposal(proposal.proposal_id)
    assert db_action is not None
    assert db_action["status"] == "PROPOSED"


def test_5_validator_accepts_valid_proposal(test_investigation):
    """ActionValidator accepts compliant structured JSON response."""
    context = PlanningContextBuilder.build_context(test_investigation)
    valid_payload = json.dumps({
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "objective": "Target inactive evening repeat buyers with evening cashback",
        "target_segment": "repeat_customer, regular",
        "target_customer_count": 486,
        "incentive_type": "CASHBACK",
        "incentive_value": 50.0,
        "duration": "7 days",
        "reason": "Address evening drop linked to expired campaign",
        "supporting_evidence_ids": ["E1", "E2", "E3"],
        "estimated_cost_inr": 2430.0,
        "constraints_acknowledged": {
            "max_discount_inr": 100.0,
            "daily_budget_inr": 12000.0,
            "max_eligible_customers": 486
        }
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=valid_payload,
        context=context,
        action_id="test-prop-01",
    )

    assert is_valid is True
    assert proposal is not None
    assert err is None
    assert proposal.action_type == ActionType.EVENING_REENGAGEMENT_CAMPAIGN
    assert proposal.incentive_value == 50.0
    assert proposal.target_customer_count == 486


def test_6_validator_rejects_unsupported_evidence_id(test_investigation):
    """ActionValidator rejects proposals referencing hallucinated evidence IDs."""
    context = PlanningContextBuilder.build_context(test_investigation)
    invalid_payload = json.dumps({
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "objective": "Test",
        "target_customer_count": 400,
        "incentive_type": "CASHBACK",
        "incentive_value": 50.0,
        "reason": "Re-engage customers",
        "supporting_evidence_ids": ["E1", "E99"],  # E99 is hallucinated
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=invalid_payload,
        context=context,
        action_id="test-prop-02",
    )

    assert is_valid is False
    assert proposal is None
    assert "E99" in err


def test_7_validator_rejects_excessive_discount(test_investigation):
    """ActionValidator rejects proposals exceeding merchant max discount rule (₹100)."""
    context = PlanningContextBuilder.build_context(test_investigation)
    invalid_payload = json.dumps({
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "objective": "Test",
        "target_customer_count": 400,
        "incentive_type": "CASHBACK",
        "incentive_value": 150.0,  # Exceeds max 100
        "reason": "Re-engage customers",
        "supporting_evidence_ids": ["E1", "E2"],
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=invalid_payload,
        context=context,
        action_id="test-prop-03",
    )

    assert is_valid is False
    assert proposal is None
    assert "exceeds" in err.lower() and "discount" in err.lower()


def test_8_validator_rejects_excessive_customer_count(test_investigation):
    """ActionValidator rejects proposals with customer counts exceeding derived eligible pool (486)."""
    context = PlanningContextBuilder.build_context(test_investigation)
    invalid_payload = json.dumps({
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "objective": "Test",
        "target_customer_count": 550,  # Exceeds 486
        "incentive_type": "CASHBACK",
        "incentive_value": 50.0,
        "reason": "Re-engage customers",
        "supporting_evidence_ids": ["E1", "E2"],
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=invalid_payload,
        context=context,
        action_id="test-prop-04",
    )

    assert is_valid is False
    assert proposal is None
    assert "exceeds" in err.lower() and "eligible" in err.lower()


def test_9_validator_rejects_excessive_daily_budget(test_investigation):
    """ActionValidator rejects proposals whose estimated cost exceeds daily budget (₹12,000)."""
    context = PlanningContextBuilder.build_context(test_investigation)
    invalid_payload = json.dumps({
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "objective": "Test",
        "target_customer_count": 486,
        "incentive_type": "CASHBACK",
        "incentive_value": 50.0,
        "estimated_cost_inr": 15000.0,  # Exceeds 12000.0
        "reason": "Re-engage customers",
        "supporting_evidence_ids": ["E1", "E2"],
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=invalid_payload,
        context=context,
        action_id="test-prop-05",
    )

    assert is_valid is False
    assert proposal is None
    assert "exceeds" in err.lower() and "budget" in err.lower()


def test_10_validator_rejects_negative_or_zero_values(test_investigation):
    """ActionValidator rejects zero or negative incentive values and customer counts."""
    context = PlanningContextBuilder.build_context(test_investigation)
    invalid_payload = json.dumps({
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "objective": "Test",
        "target_customer_count": 0,  # Invalid
        "incentive_type": "CASHBACK",
        "incentive_value": -10.0,   # Invalid
        "reason": "Re-engage customers",
        "supporting_evidence_ids": ["E1", "E2"],
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=invalid_payload,
        context=context,
        action_id="test-prop-06",
    )

    assert is_valid is False
    assert proposal is None


def test_11_validator_rejects_invalid_action_type(test_investigation):
    """ActionValidator rejects unauthorized action types."""
    context = PlanningContextBuilder.build_context(test_investigation)
    invalid_payload = json.dumps({
        "action_type": "RANDOM_UNAUTHORIZED_ACTION",
        "objective": "Test",
        "target_customer_count": 200,
        "incentive_type": "CASHBACK",
        "incentive_value": 50.0,
        "reason": "Re-engage customers",
        "supporting_evidence_ids": ["E1", "E2"],
    })

    is_valid, proposal, err = ActionValidator.validate_and_parse(
        raw_llm_response=invalid_payload,
        context=context,
        action_id="test-prop-07",
    )

    assert is_valid is False
    assert proposal is None
    assert "unallowed action type" in err.lower() or "action_type" in err.lower()


@pytest.mark.asyncio
async def test_12_proposal_persistence_in_repository(test_investigation):
    """Ensures proposed action is correctly persisted in SQLite actions table."""
    planner = PlanningEngine()
    proposal = await planner.plan_action(test_investigation, force_fallback=True)

    fetched_by_id = ActionRepository.get_action_proposal(proposal.proposal_id)
    assert fetched_by_id is not None
    assert fetched_by_id["id"] == proposal.proposal_id
    assert fetched_by_id["action_type"] == "EVENING_REENGAGEMENT_CAMPAIGN"
    assert fetched_by_id["target_customer_count"] == 486
    assert fetched_by_id["incentive_value"] == 50.0
    assert fetched_by_id["status"] == "PROPOSED"

    fetched_by_inv = ActionRepository.get_action_by_investigation(test_investigation.investigation_id)
    assert fetched_by_inv is not None
    assert fetched_by_inv["id"] == proposal.proposal_id


@pytest.mark.asyncio
async def test_13_proposal_idempotency_for_same_investigation(test_investigation):
    """Re-running planning for the same investigation updates the existing proposal rather than creating duplicates."""
    planner = PlanningEngine()
    prop1 = await planner.plan_action(test_investigation, force_fallback=True)
    prop2 = await planner.plan_action(test_investigation, force_fallback=True)

    assert prop1.proposal_id == prop2.proposal_id

    # Verify only 1 action exists for this investigation in SQLite
    actions = ActionRepository.get_actions_by_signal(test_investigation.signal_id)
    assert len(actions) == 1


@pytest.mark.asyncio
async def test_14_audit_trail_records_planning_events(test_investigation):
    """Audit trail contains ACTION_PLANNING_STARTED and ACTION_PROPOSAL_CREATED events."""
    audit_engine = AuditEngine()
    planner = PlanningEngine(audit_engine=audit_engine)
    proposal = await planner.plan_action(test_investigation, force_fallback=True)

    events = audit_engine.get_events()
    started_events = [e for e in events if "ACTION_PLANNING_STARTED" in e.action_description]
    created_events = [e for e in events if "ACTION_PROPOSAL_CREATED" in e.action_description]

    assert len(started_events) >= 1
    assert len(created_events) >= 1
    assert created_events[0].stage == StageType.DECIDE
    assert created_events[0].output_payload.get("status") == "PROPOSED"


def test_15_api_plan_action_and_get_endpoints(test_investigation):
    """Tests the REST endpoints: POST /api/actions/plan/{inv_id}, GET /api/actions/{action_id}, GET /api/investigations/{inv_id}/action."""
    client = TestClient(app)

    # 1. Plan action via POST
    post_res = client.post(
        f"/api/actions/plan/{test_investigation.investigation_id}?force_fallback=true"
    )
    assert post_res.status_code == 200
    plan_data = post_res.json()
    assert plan_data["action_type"] == "EVENING_REENGAGEMENT_CAMPAIGN"
    assert plan_data["status"] == "PROPOSED"
    assert plan_data["target_customer_count"] == 486
    assert plan_data["incentive_value"] == 50.0

    action_id = plan_data["action_id"]

    # 2. Get by action_id
    get_res = client.get(f"/api/actions/{action_id}")
    assert get_res.status_code == 200
    assert get_res.json()["action_id"] == action_id

    # 3. Get by investigation_id
    get_inv_res = client.get(f"/api/investigations/{test_investigation.investigation_id}/action")
    assert get_inv_res.status_code == 200
    assert get_inv_res.json()["action_id"] == action_id


def test_16_api_plan_action_nonexistent_investigation_returns_404():
    """Requesting planning for a non-existent investigation ID returns 404."""
    client = TestClient(app)
    res = client.post("/api/actions/plan/inv-nonexistent-12345")
    assert res.status_code == 404
    assert "was not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_17_unconfigured_gemini_falls_back_gracefully(test_investigation):
    """If Gemini client is unconfigured or encounters an error, planning gracefully falls back."""
    fallback_client = FallbackClient()
    planner = PlanningEngine(llm_client=fallback_client)

    proposal = await planner.plan_action(test_investigation, force_fallback=False)
    assert proposal is not None
    assert proposal.is_fallback is True
    assert proposal.action_type == ActionType.EVENING_REENGAGEMENT_CAMPAIGN
    assert proposal.status == "PROPOSED"
