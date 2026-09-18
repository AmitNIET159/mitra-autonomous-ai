import json
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from app.database.connection import get_connection, init_db
from app.database.repository import (
    ActionRepository,
    DecisionRepository,
    GuardrailRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.decision_engine.engine import DecisionEngine
from app.engines.decision_engine.rules import (
    BlockedDecisionApprovalError,
    EscalatedDecisionApprovalError,
    GuardrailActionMismatchError,
    GuardrailMerchantMismatchError,
    MerchantAuthorizationError,
    MissingGuardrailEvaluationError,
    StaleDecisionError,
    compute_evaluation_hash,
    compute_proposal_hash,
    evaluate_decision_state,
    synthesize_approved_action,
    verify_decision_integrity,
    verify_evaluation_precondition,
)
from app.engines.execution_engine.engine import (
    BlockedActionExecutionError,
    EscalatedActionExecutionError,
    ExecutionEngine,
    UnapprovedActionExecutionError,
    UncheckedExecutionAttemptError,
)
from app.main import app
from app.models.contracts import ActionProposal, Decision, GuardrailCheck, GuardrailEvaluation
from app.models.enums import ActionType, ApprovalStatus, DecisionState, StageType


@pytest.fixture(autouse=True)
def setup_test_database():
    """Ensures database schema is up-to-date for every test."""
    init_db()


def make_test_proposal(action_id: str = "act-test-01", merchant_id: str = "MID-DEMO-98234") -> ActionProposal:
    return ActionProposal(
        proposal_id=action_id,
        action_id=action_id,
        signal_id="sig-test-01",
        merchant_id=merchant_id,
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount_amount": 50.0, "target_segment": "repeat_customer"},
        reason="Test proposal for evening traffic",
        incentive_value=50.0,
        target_customer_count=100,
        estimated_cost_inr=5000.0,
        duration="4_DAYS",
    )


def make_test_evaluation(
    action_id: str = "act-test-01",
    status: DecisionState = DecisionState.PASS,
    merchant_id: str = "MID-DEMO-98234",
    modifications: dict = None,
) -> GuardrailEvaluation:
    mods = modifications or {}
    checks = [
        GuardrailCheck(
            check_id="G1",
            check_type="MIN_MARGIN",
            status="PASS" if status != DecisionState.BLOCK else "FAIL",
            rule="Minimum Margin >= 10%",
            actual_value=12.5 if status != DecisionState.BLOCK else 7.8,
            threshold_value=10.0,
            message="Safe margin" if status != DecisionState.BLOCK else "Margin below 10%",
        ),
    ]
    return GuardrailEvaluation(
        evaluation_id=f"grd-{action_id}",
        action_id=action_id,
        merchant_id=merchant_id,
        overall_status=status,
        passed=(status in (DecisionState.PASS, DecisionState.MODIFY)),
        checks=checks,
        passed_checks=["G1"] if status != DecisionState.BLOCK else [],
        failed_checks=["G1"] if status == DecisionState.BLOCK else [],
        modifications=mods,
        modified_values=mods,
        notes="Evaluated by test fixture",
    )


def save_test_proposal(
    action_id: str,
    investigation_id: str = "inv-test",
    merchant_id: str = "MID-DEMO-98234",
    signal_id: str = "sig-test",
    action_type: str = "OFFER_CAMPAIGN",
    parameters: dict = None,
    incentive_value: float = 20.0,
    estimated_cost_inr: float = 1000.0,
) -> dict:
    return ActionRepository.create_or_update_action_proposal(
        signal_id=signal_id,
        investigation_id=investigation_id,
        merchant_id=merchant_id,
        action_type=action_type,
        action_id=action_id,
        parameters=parameters or {"discount": 20},
        incentive_value=incentive_value,
        estimated_cost_inr=estimated_cost_inr,
        reason="Test action proposal",
    )


def save_test_evaluation(
    action_id: str,
    merchant_id: str = "MID-DEMO-98234",
    overall_status: str = "PASS",
    passed: bool = True,
    checks: list = None,
    passed_checks: list = None,
    failed_checks: list = None,
    modifications: dict = None,
    modified_values: dict = None,
    notes: str = "Test notes",
) -> dict:
    return GuardrailRepository.create_or_update_evaluation(
        evaluation_id=f"grd-{action_id}",
        action_id=action_id,
        merchant_id=merchant_id,
        overall_status=overall_status,
        passed=passed,
        checks=checks or [{"check_id": "G1", "status": "PASS", "rule": "Rule", "message": "OK"}],
        passed_checks=passed_checks or ["G1"],
        failed_checks=failed_checks or [],
        warnings=[],
        modifications=modifications or {},
        original_values={},
        modified_values=modified_values or modifications or {},
        notes=notes,
    )


# ---------------------------------------------------------------------------
# 1. Precondition & Architectural Boundary Tests
# ---------------------------------------------------------------------------

def test_1_decision_requires_existing_guardrail_evaluation():
    """Decision creation fails with MissingGuardrailEvaluationError if evaluation is missing."""
    engine = DecisionEngine()
    # Save action proposal without guardrails
    save_test_proposal(
        action_id="act-missing-guard-01",
        investigation_id="inv-boundary-01",
        signal_id="sig-boundary-01",
        parameters={"discount": 20},
    )

    with pytest.raises(MissingGuardrailEvaluationError):
        engine.create_decision_from_persisted_evaluation("act-missing-guard-01")


def test_2_decision_does_not_invoke_guardrail_engine():
    """Phase 7 strictly consumes persisted Phase 6 output and NEVER invokes GuardrailEngine."""
    with patch("app.engines.guardrail_engine.engine.GuardrailEngine.evaluate") as mock_guard_eval:
        engine = DecisionEngine()
        proposal = make_test_proposal("act-no-guard-invoke")
        evaluation = make_test_evaluation("act-no-guard-invoke")

        decision = engine.decide(proposal, evaluation)
        assert decision.decision_state == DecisionState.PASS
        # GuardrailEngine.evaluate was NEVER called!
        mock_guard_eval.assert_not_called()


def test_3_missing_guardrail_evaluation_returns_conflict():
    """API endpoint returns HTTP 409 Conflict when GuardrailEvaluation is missing."""
    client = TestClient(app)
    # Save proposal but no evaluation
    save_test_proposal(
        action_id="act-api-no-guard-409",
        investigation_id="inv-api-409",
        signal_id="sig-api-409",
        parameters={"discount": 20},
    )

    res = client.post("/api/decisions/create/act-api-no-guard-409")
    assert res.status_code == 409
    assert res.json()["detail"] == "Guardrail evaluation required before decision creation."


def test_4_decision_uses_persisted_guardrail_result():
    """DecisionEngine reads persisted evaluation from SQLite correctly."""
    engine = DecisionEngine()
    action_id = "act-persisted-eval-01"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-persisted-01",
        signal_id="sig-persisted-01",
        parameters={"discount": 20},
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
        notes="Saved in Phase 6",
    )

    decision = engine.create_decision_from_persisted_evaluation(action_id)
    assert decision.action_id == action_id
    assert decision.decision_state == DecisionState.PASS
    assert decision.approval_status == ApprovalStatus.PENDING
    assert decision.is_execution_eligible is False


def test_5_guardrail_evaluation_action_mismatch_rejected():
    """Rejects evaluation belonging to a different action."""
    proposal = make_test_proposal("act-target")
    evaluation = make_test_evaluation("act-different")

    with pytest.raises(GuardrailActionMismatchError):
        verify_evaluation_precondition("act-target", evaluation)


def test_6_guardrail_evaluation_merchant_mismatch_rejected():
    """Rejects evaluation belonging to a different merchant."""
    proposal = make_test_proposal("act-mismatch", merchant_id="MID-MERCHANT-A")
    evaluation = make_test_evaluation("act-mismatch", merchant_id="MID-MERCHANT-B")

    with pytest.raises(GuardrailMerchantMismatchError):
        verify_evaluation_precondition("act-mismatch", evaluation, merchant_id="MID-MERCHANT-A")


# ---------------------------------------------------------------------------
# 2. Decision State Mapping & Modification Integrity
# ---------------------------------------------------------------------------

def test_7_decision_state_pass_from_guardrails():
    """Guardrail PASS maps to DecisionState.PASS."""
    engine = DecisionEngine()
    proposal = make_test_proposal("act-pass-01")
    evaluation = make_test_evaluation("act-pass-01", status=DecisionState.PASS)

    decision = engine.decide(proposal, evaluation)
    assert decision.decision_state == DecisionState.PASS
    assert decision.approved_action is not None
    assert decision.approved_action["action_type"] == ActionType.OFFER_CAMPAIGN.value


def test_8_decision_state_modify_with_clamped_parameters():
    """Guardrail MODIFY maps to DecisionState.MODIFY with modifications applied."""
    engine = DecisionEngine()
    proposal = make_test_proposal("act-mod-01")
    evaluation = make_test_evaluation(
        "act-mod-01",
        status=DecisionState.MODIFY,
        modifications={"discount_amount": 30.0, "max_discount": 30.0},
    )

    decision = engine.decide(proposal, evaluation)
    assert decision.decision_state == DecisionState.MODIFY
    assert decision.approved_action is not None
    assert decision.approved_action["parameters"]["discount_amount"] == 30.0


def test_9_modify_uses_modified_values():
    """MODIFY INTEGRITY: Clamped ₹100 is approved; requested ₹150 is NEVER approved."""
    engine = DecisionEngine()
    proposal = ActionProposal(
        proposal_id="act-cashback-150",
        action_id="act-cashback-150",
        signal_id="sig-cb",
        merchant_id="MID-DEMO-98234",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"cashback_inr": 150.0, "target_segment": "repeat_customer"},
        incentive_value=150.0,
        estimated_cost_inr=7500.0,
        duration="4_DAYS",
        reason="Requested 150 cashback",
    )
    # Phase 6 clamped ₹150 -> ₹100
    evaluation = GuardrailEvaluation(
        evaluation_id="grd-cb",
        action_id="act-cashback-150",
        overall_status=DecisionState.MODIFY,
        passed=True,
        modifications={"cashback_inr": 100.0, "incentive_value": 100.0},
        modified_values={"cashback_inr": 100.0, "incentive_value": 100.0},
        notes="G3 Maximum Discount limit clamped cashback from 150 to 100 INR",
    )

    decision = engine.decide(proposal, evaluation)
    assert decision.decision_state == DecisionState.MODIFY
    assert decision.approved_action["incentive_value"] == 100.0
    assert decision.approved_action["parameters"]["cashback_inr"] == 100.0
    # Requested 150 is nowhere in approved parameters!
    assert decision.approved_action["parameters"]["cashback_inr"] != 150.0


def test_10_decision_state_block_for_margin_violation():
    """Guardrail BLOCK maps to DecisionState.BLOCK with NO approved action."""
    engine = DecisionEngine()
    proposal = make_test_proposal("act-block-01")
    evaluation = make_test_evaluation("act-block-01", status=DecisionState.BLOCK)

    decision = engine.decide(proposal, evaluation)
    assert decision.decision_state == DecisionState.BLOCK
    assert decision.approved_action is None
    assert decision.is_execution_eligible is False


def test_11_decision_state_escalate_for_human_review():
    """Guardrail ESCALATE maps to DecisionState.ESCALATE with review required."""
    engine = DecisionEngine()
    proposal = make_test_proposal("act-esc-01")
    evaluation = make_test_evaluation("act-esc-01", status=DecisionState.ESCALATE)

    decision = engine.decide(proposal, evaluation)
    assert decision.decision_state == DecisionState.ESCALATE
    assert decision.requires_human_review is True
    assert decision.is_execution_eligible is False


# ---------------------------------------------------------------------------
# 3. Approval Semantics & Authorization Barrier
# ---------------------------------------------------------------------------

def test_12_approval_required_defaults_to_pending():
    """When require_approval=True, initial status is PENDING."""
    engine = DecisionEngine()
    proposal = make_test_proposal("act-appr-req")
    evaluation = make_test_evaluation("act-appr-req")

    decision = engine.decide(proposal, evaluation, require_approval=True)
    assert decision.approval_required is True
    assert decision.approval_status == ApprovalStatus.PENDING
    assert decision.is_execution_eligible is False


def test_13_pending_decision_is_not_execution_eligible():
    """Decision with PENDING status has is_execution_eligible == False."""
    decision = Decision(
        action_id="act-pending",
        decision_state=DecisionState.PASS,
        approval_required=True,
        approval_status=ApprovalStatus.PENDING,
    )
    assert decision.is_execution_eligible is False


def test_14_merchant_approve_sets_approved_and_eligible():
    """Merchant approval updates decision to APPROVED and makes it execution-eligible."""
    engine = DecisionEngine()
    action_id = "act-signoff-flow"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-signoff",
        signal_id="sig-signoff",
        parameters={"discount": 20},
        incentive_value=20.0,
        estimated_cost_inr=1000.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
        notes="Safe",
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)
    assert created.approval_status == ApprovalStatus.PENDING
    assert created.is_execution_eligible is False

    approved = engine.approve_decision(created.decision_id, approver_name="Merchant Owner")
    assert approved.approval_status == ApprovalStatus.APPROVED
    assert approved.is_execution_eligible is True
    assert approved.approved_at is not None


def test_15_merchant_reject_sets_rejected_and_ineligible():
    """Merchant rejection updates status to REJECTED and execution ineligible."""
    engine = DecisionEngine()
    action_id = "act-reject-flow"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-rej",
        signal_id="sig-rej",
        parameters={"discount": 20},
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)
    rejected = engine.reject_decision(created.decision_id, reason="Too costly for this weekend")

    assert rejected.approval_status == ApprovalStatus.REJECTED
    assert rejected.is_execution_eligible is False
    assert rejected.rejected_at is not None


def test_16_block_cannot_be_overridden_by_approval():
    """SAFETY GUARANTEE: Attempting to approve a BLOCKED decision raises BlockedDecisionApprovalError."""
    engine = DecisionEngine()
    action_id = "act-block-attempt"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-blk",
        signal_id="sig-blk",
        parameters={"discount": 80},
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="BLOCK",
        passed=False,
        failed_checks=["G1_MARGIN"],
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)
    assert created.decision_state == DecisionState.BLOCK

    with pytest.raises(BlockedDecisionApprovalError):
        engine.approve_decision(created.decision_id)


def test_17_escalate_cannot_be_overridden_by_approval():
    """SAFETY GUARANTEE: Attempting to approve an ESCALATED decision raises EscalatedDecisionApprovalError."""
    engine = DecisionEngine()
    action_id = "act-esc-attempt"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-esc",
        signal_id="sig-esc",
        parameters={"discount": 40},
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="ESCALATE",
        passed=False,
        failed_checks=["POLICY_ESCALATION"],
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)
    assert created.decision_state == DecisionState.ESCALATE

    with pytest.raises(EscalatedDecisionApprovalError):
        engine.approve_decision(created.decision_id)


def test_18_wrong_merchant_cannot_approve():
    """Cross-merchant approval attempt raises MerchantAuthorizationError."""
    engine = DecisionEngine()
    action_id = "act-cross-merchant"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-cross",
        signal_id="sig-cross",
        merchant_id="MID-DEMO-98234",
        parameters={"discount": 10},
    )
    save_test_evaluation(
        action_id=action_id,
        merchant_id="MID-DEMO-98234",
        overall_status="PASS",
        passed=True,
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)

    with pytest.raises(MerchantAuthorizationError):
        engine.approve_decision(created.decision_id, approver_merchant_id="MID-ATTACKER-999")


def test_19_approval_cannot_modify_action():
    """Sign-off records approval without modifying proposed parameters."""
    engine = DecisionEngine()
    action_id = "act-immutable-params"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-imm",
        signal_id="sig-imm",
        parameters={"discount": 25.0, "segment": "repeat"},
        incentive_value=25.0,
        estimated_cost_inr=1500.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)
    original_approved_action = dict(created.approved_action)

    approved = engine.approve_decision(created.decision_id)
    assert approved.approved_action == original_approved_action


# ---------------------------------------------------------------------------
# 4. Hash Integrity & Stale Decision Protection
# ---------------------------------------------------------------------------

def test_20_canonical_proposal_hash_generation():
    """Canonical proposal hash is deterministic regardless of dictionary insertion order."""
    p1 = ActionProposal(
        action_id="act-hash-1",
        signal_id="sig-hash-1",
        merchant_id="MID-DEMO",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"a": 1, "b": 2},
        incentive_value=50.0,
        estimated_cost_inr=1000.0,
        duration="4_DAYS",
        reason="Hash test 1",
    )
    p2 = ActionProposal(
        action_id="act-hash-1",
        signal_id="sig-hash-1",
        merchant_id="MID-DEMO",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"b": 2, "a": 1},
        incentive_value=50.0,
        estimated_cost_inr=1000.0,
        duration="4_DAYS",
        reason="Hash test 2",
    )
    assert compute_proposal_hash(p1) == compute_proposal_hash(p2)


def test_21_canonical_evaluation_hash_generation():
    """Canonical evaluation hash is deterministic regardless of failed_checks ordering."""
    e1 = GuardrailEvaluation(
        action_id="act-hash-e",
        overall_status=DecisionState.PASS,
        failed_checks=["G1", "G2"],
        modifications={"a": 1},
    )
    e2 = GuardrailEvaluation(
        action_id="act-hash-e",
        overall_status=DecisionState.PASS,
        failed_checks=["G2", "G1"],
        modifications={"a": 1},
    )
    assert compute_evaluation_hash(e1) == compute_evaluation_hash(e2)


def test_22_stale_proposal_blocks_approval():
    """Modifying proposal parameters after decision creation causes approval to fail with StaleDecisionError."""
    engine = DecisionEngine()
    action_id = "act-stale-p"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-stale-p",
        signal_id="sig-stale-p",
        parameters={"discount": 20},
        incentive_value=20.0,
        estimated_cost_inr=1000.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)

    # Sneakily tamper with action in DB post-decision creation
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE actions SET parameters = ? WHERE id = ?",
            (json.dumps({"discount": 99}), action_id),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(StaleDecisionError):
        engine.approve_decision(created.decision_id)


def test_23_stale_evaluation_blocks_approval():
    """Modifying evaluation after decision creation causes approval to fail with StaleDecisionError."""
    engine = DecisionEngine()
    action_id = "act-stale-e"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-stale-e",
        signal_id="sig-stale-e",
        parameters={"discount": 20},
        incentive_value=20.0,
        estimated_cost_inr=1000.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)

    # Sneakily tamper with evaluation in DB post-decision creation
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE guardrail_evaluations SET overall_status = 'BLOCK' WHERE action_id = ?",
            (action_id,),
        )
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(StaleDecisionError):
        engine.approve_decision(created.decision_id)


def test_24_stale_proposal_requires_fresh_guardrails():
    """Stale proposal detection requires fresh Phase 6 re-evaluation."""
    proposal = make_test_proposal("act-fresh-guard-req")
    evaluation = make_test_evaluation("act-fresh-guard-req")
    decision = DecisionEngine().decide(proposal, evaluation)

    # Proposal altered
    tampered_proposal = make_test_proposal("act-fresh-guard-req")
    tampered_proposal.parameters = {"discount": 99}

    is_intact, reason = verify_decision_integrity(decision, tampered_proposal, evaluation)
    assert is_intact is False
    assert "Proposal payload has changed" in reason


def test_25_stale_evaluation_requires_fresh_decision():
    """Stale evaluation detection blocks approval until fresh decision created."""
    proposal = make_test_proposal("act-fresh-dec-req")
    evaluation = make_test_evaluation("act-fresh-dec-req")
    decision = DecisionEngine().decide(proposal, evaluation)

    # Evaluation altered
    tampered_evaluation = make_test_evaluation("act-fresh-dec-req", status=DecisionState.MODIFY)

    is_intact, reason = verify_decision_integrity(decision, proposal, tampered_evaluation)
    assert is_intact is False
    assert "Guardrail evaluation has changed" in reason


# ---------------------------------------------------------------------------
# 5. Execution Barrier Safety Tests
# ---------------------------------------------------------------------------

def test_26_execution_engine_rejects_pending_decision():
    """ExecutionEngine strictly rejects decision with approval_status == PENDING."""
    engine = ExecutionEngine(simulation_mode=True)
    decision = Decision(
        action_id="act-exec-pending",
        decision_state=DecisionState.PASS,
        approval_required=True,
        approval_status=ApprovalStatus.PENDING,
        approved_action={"action_type": "OFFER_CAMPAIGN", "parameters": {}},
    )

    with pytest.raises(UnapprovedActionExecutionError):
        engine.execute(decision)


def test_27_execution_engine_rejects_rejected_decision():
    """ExecutionEngine strictly rejects decision with approval_status == REJECTED."""
    engine = ExecutionEngine(simulation_mode=True)
    decision = Decision(
        action_id="act-exec-rejected",
        decision_state=DecisionState.PASS,
        approval_required=True,
        approval_status=ApprovalStatus.REJECTED,
        approved_action={"action_type": "OFFER_CAMPAIGN", "parameters": {}},
    )

    with pytest.raises(UnapprovedActionExecutionError):
        engine.execute(decision)


def test_28_execution_engine_accepts_approved_pass():
    """ExecutionEngine successfully executes APPROVED PASS decision."""
    engine = ExecutionEngine(simulation_mode=True)
    decision = Decision(
        action_id="act-exec-ok",
        decision_state=DecisionState.PASS,
        approval_required=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_action={"action_type": "OFFER_CAMPAIGN", "parameters": {"discount": 10}},
    )

    res = engine.execute(decision)
    assert res.success is True
    assert res.status == "COMPLETED"
    assert res.simulated is True


def test_29_execution_engine_accepts_approved_modify():
    """ExecutionEngine successfully executes APPROVED MODIFY decision with modified parameters."""
    engine = ExecutionEngine(simulation_mode=True)
    decision = Decision(
        action_id="act-exec-mod-ok",
        decision_state=DecisionState.MODIFY,
        approval_required=True,
        approval_status=ApprovalStatus.APPROVED,
        approved_action={"action_type": "OFFER_CAMPAIGN", "parameters": {"discount": 30}},
    )

    res = engine.execute(decision)
    assert res.success is True
    assert res.output_details["applied_parameters"]["discount"] == 30


def test_30_idempotent_decision_creation():
    """Calling create_decision_from_persisted_evaluation repeatedly returns the same decision."""
    engine = DecisionEngine()
    action_id = "act-idempotent-01"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-idem",
        signal_id="sig-idem",
        parameters={"discount": 20},
        incentive_value=20.0,
        estimated_cost_inr=1000.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    dec1 = engine.create_decision_from_persisted_evaluation(action_id)
    dec2 = engine.create_decision_from_persisted_evaluation(action_id)
    assert dec1.decision_id == dec2.decision_id


def test_31_audit_trail_records_decision_and_approval_events():
    """Audit trail records cryptographic events for decision creation and approval."""
    audit_engine = AuditEngine()
    engine = DecisionEngine(audit_engine=audit_engine)
    action_id = "act-audit-test"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-aud",
        signal_id="sig-aud",
        parameters={"discount": 20},
        incentive_value=20.0,
        estimated_cost_inr=1000.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    created = engine.create_decision_from_persisted_evaluation(action_id)
    engine.approve_decision(created.decision_id)

    events = audit_engine.get_events(limit=10)
    decide_events = [e for e in events if e.stage == StageType.DECIDE]
    assert len(decide_events) >= 2
    # Verify hash chaining
    assert all(e.integrity_hash is not None for e in events)


# ---------------------------------------------------------------------------
# 6. REST API Endpoints & Safety Demo Tests
# ---------------------------------------------------------------------------

def test_32_api_decision_crud_and_status_endpoints():
    """Tests POST /api/decisions/create, GET /api/decisions/{id}, GET /api/actions/{id}/decision, POST /approve, POST /reject."""
    client = TestClient(app)
    action_id = "act-api-lifecycle"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-api-life",
        signal_id="sig-api-life",
        parameters={"discount": 20},
        incentive_value=20.0,
        estimated_cost_inr=1000.0,
    )
    save_test_evaluation(
        action_id=action_id,
        overall_status="PASS",
        passed=True,
    )

    # 1. Create Decision
    res_create = client.post(f"/api/decisions/create/{action_id}")
    assert res_create.status_code == 201
    dec_data = res_create.json()
    dec_id = dec_data["decision_id"]
    assert dec_data["approval_status"] == "PENDING"
    assert dec_data["is_execution_eligible"] is False

    # 2. Get Decision by ID
    res_get = client.get(f"/api/decisions/{dec_id}")
    assert res_get.status_code == 200
    assert res_get.json()["decision_id"] == dec_id

    # 3. Get Decision by Action
    res_action = client.get(f"/api/actions/{action_id}/decision")
    assert res_action.status_code == 200
    assert res_action.json()["decision_id"] == dec_id

    # 4. Approve Decision
    res_appr = client.post(f"/api/decisions/{dec_id}/approve", json={"merchant_id": "MID-DEMO-98234", "approver": "Owner"})
    assert res_appr.status_code == 200
    assert res_appr.json()["approval_status"] == "APPROVED"
    assert res_appr.json()["is_execution_eligible"] is True


def test_33_safety_demo_forced_margin_block_cannot_execute():
    """SAFETY DEMO: Margin 7.8% BLOCK cannot be approved via API or executed by ExecutionEngine."""
    client = TestClient(app)
    action_id = "act-safety-demo-margin"

    save_test_proposal(
        action_id=action_id,
        investigation_id="inv-demo-blk",
        signal_id="sig-demo-blk",
        parameters={"discount": 80},
    )
    # Phase 6 GuardrailEvaluation is BLOCK
    save_test_evaluation(
        action_id=action_id,
        overall_status="BLOCK",
        passed=False,
        failed_checks=["G1_MINIMUM_MARGIN"],
        notes="Projected margin 7.8% < 10% policy threshold",
    )

    # Decision Engine creates BLOCK decision
    res_create = client.post(f"/api/decisions/create/{action_id}")
    assert res_create.status_code == 201
    dec_id = res_create.json()["decision_id"]
    assert res_create.json()["decision_state"] == "BLOCK"
    assert res_create.json()["is_execution_eligible"] is False

    # Sign-off attempt FAILS with HTTP 400
    res_appr = client.post(f"/api/decisions/{dec_id}/approve")
    assert res_appr.status_code == 400
    assert "Blocked decisions cannot be approved" in res_appr.json()["detail"]

    # Execution Engine strictly refuses execution
    row = DecisionRepository.get_decision(dec_id)
    dec_obj = DecisionEngine._row_to_decision(row)
    with pytest.raises(BlockedActionExecutionError):
        ExecutionEngine(simulation_mode=True).execute(dec_obj)


def test_34_arbitrary_dict_rejected():
    """ExecutionEngine strictly rejects arbitrary dictionary inputs."""
    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(UncheckedExecutionAttemptError):
        engine.execute({"state": "PASS", "approved_action": {}})


def test_35_llm_cannot_override_decision():
    """LLM outputs cannot override authoritative deterministic decisions."""
    engine = DecisionEngine()
    proposal = make_test_proposal("act-llm-override")
    # Even if LLM claimed a decision in its reasoning text, guardrails BLOCK overrides everything
    evaluation = make_test_evaluation("act-llm-override", status=DecisionState.BLOCK)

    decision = engine.decide(proposal, evaluation)
    assert decision.decision_state == DecisionState.BLOCK
    assert decision.approved_action is None
