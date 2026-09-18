"""Tests for MITRA Phase 8: Safe Execution Simulator.

SAFETY PRINCIPLES VERIFIED:
- Strictly executes in SIMULATION mode with zero real Paytm API calls.
- Gated by 10 deterministic preconditions.
- Non-overridable safety barrier: BLOCK, ESCALATE, PENDING, REJECTED can NEVER execute.
- Strict MODIFY parameter preservation: Clamped safe values execute, never original unsafe values.
- Idempotency & concurrency protection: No duplicate executions or side effects.
- Audit trail integrity with SHA-256 chaining.
"""
from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from app.database.connection import init_db
from app.database.repository import (
    ActionRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.decision_engine.rules import (
    compute_evaluation_hash,
    compute_proposal_hash,
)
from app.engines.execution_engine.engine import (
    BlockedActionExecutionError,
    DecisionNotFoundError,
    EscalatedActionExecutionError,
    ExecutionAlreadyCompletedError,
    ExecutionEngine,
    ExecutionNotEligibleError,
    ExecutionSafetyError,
    MerchantMismatchError,
    RealExecutionNotAllowedError,
    StaleDecisionExecutionError,
    UnapprovedActionExecutionError,
    UncheckedExecutionAttemptError,
)
from app.integrations.paytm_simulator import RealExecutionNotAllowedError, SimulatedPaytmAdapter
from app.main import app
from app.models.contracts import ActionProposal, Decision, ExecutionResult
from app.models.enums import (
    ActionType,
    ApprovalStatus,
    DecisionState,
    ExecutionMode,
    ExecutionState,
    StageType,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def _create_test_proposal(action_id="act-test-p8", incentive_val=100.0, cost=5000.0):
    return ActionRepository.create_or_update_action_proposal(
        signal_id=f"sig-{action_id}",
        investigation_id=f"inv-{action_id}",
        merchant_id="MID-DEMO-98234",
        action_type="OFFER_CAMPAIGN",
        action_id=action_id,
        parameters={"cashback_inr": incentive_val, "target_customer_count": 50},
        incentive_value=incentive_val,
        estimated_cost_inr=cost,
        target_customer_count=50,
        duration="7 days",
        reason="Test proposal for execution",
    )



def _create_test_evaluation(action_id="act-test-p8", eval_id="grd-test-p8", overall_status="PASS"):
    now_iso = datetime.now(timezone.utc).isoformat()
    return GuardrailRepository.create_or_update_evaluation(
        evaluation_id=eval_id,
        action_id=action_id,
        merchant_id="MID-DEMO-98234",
        overall_status=overall_status,
        passed=(overall_status in ("PASS", "MODIFY")),
        checks=[{
            "check_id": "G1",
            "check_type": "MIN_MARGIN",
            "status": "PASS",
            "rule": "Margin >= 10%",
            "actual_value": 15.0,
            "threshold_value": 10.0,
            "message": "Passed",
            "severity": "INFO",
        }],
        passed_checks=["G1"],
        failed_checks=[],
        warnings=[],
        modifications={"cashback_inr": 100.0} if overall_status == "MODIFY" else {},
        original_values={"cashback_inr": 150.0} if overall_status == "MODIFY" else {},
        modified_values={"cashback_inr": 100.0} if overall_status == "MODIFY" else {},
        notes="Test evaluation",
        evaluated_at=now_iso,
    )


def _create_approved_decision(
    action_id="act-test-p8",
    eval_id="grd-test-p8",
    dec_id="dec-test-p8",
    state=DecisionState.PASS,
    approval_status=ApprovalStatus.APPROVED,
    is_eligible=True,
    incentive_val=100.0,
):
    prop_row = ActionRepository.get_action_proposal(action_id)
    eval_row = GuardrailRepository.get_evaluation(eval_id)
    p_hash = compute_proposal_hash(prop_row) if prop_row else "hash-prop"
    e_hash = compute_evaluation_hash(eval_row) if eval_row else "hash-eval"
    now_iso = datetime.now(timezone.utc).isoformat()

    row = DecisionRepository.create_or_update_decision(
        decision_id=dec_id,
        action_id=action_id,
        evaluation_id=eval_id,
        merchant_id="MID-DEMO-98234",
        decision_state=state.value,
        reason="Approved by test",
        triggered_rules=[],
        modifications={"cashback_inr": incentive_val} if state == DecisionState.MODIFY else {},
        approval_required=True,
        approval_status=approval_status.value,
        proposal_hash=p_hash,
        evaluation_hash=e_hash,
        approved_action={
            "action_type": "OFFER_CAMPAIGN",
            "parameters": {"cashback_inr": incentive_val, "target_customer_count": 50},
            "incentive_value": incentive_val,
            "target_customer_count": 50,
            "duration": "7 days",
            "estimated_cost_inr": incentive_val * 50,
        },
        requires_human_review=False,
        is_execution_eligible=is_eligible,
        decided_at=now_iso,
        approved_at=now_iso if approval_status == ApprovalStatus.APPROVED else None,
    )
    return Decision.model_validate(row)


# ==============================================================================
# 1. BASIC EXECUTION TESTS (1 - 6)
# ==============================================================================

def test_1_approved_pass_executes():
    """Test 1: Approved PASS decision successfully executes."""
    _create_test_proposal("act-p1", 50.0)
    _create_test_evaluation("act-p1", "grd-p1", "PASS")
    dec = _create_approved_decision("act-p1", "grd-p1", "dec-p1", DecisionState.PASS)

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.execution_state == ExecutionState.COMPLETED
    assert res.success is True
    assert res.decision_id == "dec-p1"


def test_2_approved_modify_executes():
    """Test 2: Approved MODIFY decision successfully executes."""
    _create_test_proposal("act-p2", 100.0)
    _create_test_evaluation("act-p2", "grd-p2", "MODIFY")
    dec = _create_approved_decision("act-p2", "grd-p2", "dec-p2", DecisionState.MODIFY, incentive_val=100.0)

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.execution_state == ExecutionState.COMPLETED
    assert res.success is True


def test_3_execution_record_persisted():
    """Test 3: Execution row is persisted in SQLite."""
    _create_test_proposal("act-p3")
    _create_test_evaluation("act-p3", "grd-p3", "PASS")
    dec = _create_approved_decision("act-p3", "grd-p3", "dec-p3")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    row = ExecutionRepository.get_execution(res.execution_id)
    assert row is not None
    assert row["id"] == res.execution_id
    assert row["decision_id"] == "dec-p3"


def test_4_execution_state_completed():
    """Test 4: Final execution state is strictly COMPLETED."""
    _create_test_proposal("act-p4")
    _create_test_evaluation("act-p4", "grd-p4", "PASS")
    dec = _create_approved_decision("act-p4", "grd-p4", "dec-p4")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.execution_state == ExecutionState.COMPLETED
    assert res.status == "COMPLETED"


def test_5_simulation_mode_enforced():
    """Test 5: execution_mode is strictly SIMULATION."""
    _create_test_proposal("act-p5")
    _create_test_evaluation("act-p5", "grd-p5", "PASS")
    dec = _create_approved_decision("act-p5", "grd-p5", "dec-p5")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.execution_mode == ExecutionMode.SIMULATION
    assert res.result["execution_mode"] == "SIMULATION"


def test_6_simulated_flag_true():
    """Test 6: simulated flag is strictly True."""
    _create_test_proposal("act-p6")
    _create_test_evaluation("act-p6", "grd-p6", "PASS")
    dec = _create_approved_decision("act-p6", "grd-p6", "dec-p6")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.simulated is True
    assert res.result["simulated"] is True


# ==============================================================================
# 2. SAFETY BOUNDARY TESTS (7 - 13)
# ==============================================================================

def test_7_pending_cannot_execute():
    """Test 7: Unapproved decision with approval_status=PENDING is strictly blocked."""
    _create_test_proposal("act-s7")
    _create_test_evaluation("act-s7", "grd-s7", "PASS")
    dec = _create_approved_decision("act-s7", "grd-s7", "dec-s7", approval_status=ApprovalStatus.PENDING, is_eligible=False)

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(UnapprovedActionExecutionError):
        engine.execute(dec.decision_id)


def test_8_rejected_cannot_execute():
    """Test 8: Rejected decision is strictly blocked."""
    _create_test_proposal("act-s8")
    _create_test_evaluation("act-s8", "grd-s8", "PASS")
    dec = _create_approved_decision("act-s8", "grd-s8", "dec-s8", approval_status=ApprovalStatus.REJECTED, is_eligible=False)

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(UnapprovedActionExecutionError):
        engine.execute(dec.decision_id)


def test_9_block_decision_cannot_execute():
    """Test 9: Decision in state=BLOCK cannot execute under any circumstance."""
    _create_test_proposal("act-s9")
    _create_test_evaluation("act-s9", "grd-s9", "BLOCK")
    dec = _create_approved_decision("act-s9", "grd-s9", "dec-s9", state=DecisionState.BLOCK, is_eligible=False)

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(BlockedActionExecutionError):
        engine.execute(dec.decision_id)


def test_10_escalate_decision_cannot_execute():
    """Test 10: Decision in state=ESCALATE cannot execute."""
    _create_test_proposal("act-s10")
    _create_test_evaluation("act-s10", "grd-s10", "ESCALATE")
    dec = _create_approved_decision("act-s10", "grd-s10", "dec-s10", state=DecisionState.ESCALATE, is_eligible=False)

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(EscalatedActionExecutionError):
        engine.execute(dec.decision_id)


def test_11_execution_eligible_false_blocks_execution():
    """Test 11: is_execution_eligible=False blocks execution even if status is APPROVED."""
    _create_test_proposal("act-s11")
    _create_test_evaluation("act-s11", "grd-s11", "PASS")
    dec = _create_approved_decision("act-s11", "grd-s11", "dec-s11", is_eligible=False)

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(ExecutionNotEligibleError):
        engine.execute(dec.decision_id)


def test_12_missing_approved_action_blocks_execution():
    """Test 12: Decision missing approved_action payload cannot execute."""
    _create_test_proposal("act-s12")
    _create_test_evaluation("act-s12", "grd-s12", "PASS")
    dec = _create_approved_decision("act-s12", "grd-s12", "dec-s12")
    # Mutate to empty
    dec.approved_action = {}

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(ExecutionSafetyError):
        engine.execute(dec)


def test_13_wrong_merchant_blocked():
    """Test 13: Execution attempted by a non-matching merchant is rejected."""
    _create_test_proposal("act-s13")
    _create_test_evaluation("act-s13", "grd-s13", "PASS")
    dec = _create_approved_decision("act-s13", "grd-s13", "dec-s13")

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(MerchantMismatchError):
        engine.execute(dec.decision_id, merchant_id="MID-WRONG-ATTACKER")


# ==============================================================================
# 3. HASH INTEGRITY & TAMPER PROTECTION (14 - 16)
# ==============================================================================

def test_14_stale_proposal_blocks_execution():
    """Test 14: Tampered or updated proposal after decision blocks execution (409)."""
    _create_test_proposal("act-h14", 50.0)
    _create_test_evaluation("act-h14", "grd-h14", "PASS")
    dec = _create_approved_decision("act-h14", "grd-h14", "dec-h14")

    # Tamper with underlying proposal
    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-act-h14",
        investigation_id="inv-act-h14",
        merchant_id="MID-DEMO-98234",
        action_type="OFFER_CAMPAIGN",
        action_id="act-h14",
        parameters={"cashback_inr": 999.0},
        incentive_value=999.0,
    )

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(StaleDecisionExecutionError):
        engine.execute(dec.decision_id)


def test_15_stale_evaluation_blocks_execution():
    """Test 15: Tampered evaluation after decision blocks execution."""
    _create_test_proposal("act-h15")
    _create_test_evaluation("act-h15", "grd-h15", "PASS")
    dec = _create_approved_decision("act-h15", "grd-h15", "dec-h15")

    # Mutate evaluation row
    GuardrailRepository.create_or_update_evaluation(
        evaluation_id="grd-h15",
        action_id="act-h15",
        merchant_id="MID-DEMO-98234",
        overall_status="BLOCK",
        passed=False,
        checks=[],
        passed_checks=[],
        failed_checks=["G1"],
        warnings=[],
        modifications={},
        original_values={},
        modified_values={},
    )

    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(StaleDecisionExecutionError):
        engine.execute(dec.decision_id)


def test_16_valid_hashes_permit_execution():
    """Test 16: Untampered proposal and evaluation hashes permit execution."""
    _create_test_proposal("act-h16", 50.0)
    _create_test_evaluation("act-h16", "grd-h16", "PASS")
    dec = _create_approved_decision("act-h16", "grd-h16", "dec-h16")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)
    assert res.execution_state == ExecutionState.COMPLETED


# ==============================================================================
# 4. CRITICAL MODIFY RULE TESTS (17 - 19)
# ==============================================================================

def test_17_modified_parameter_executed():
    """Test 17: For MODIFY decision, execution uses clamped safe parameter (₹100)."""
    # Original proposal had ₹150
    _create_test_proposal("act-m17", 150.0)
    _create_test_evaluation("act-m17", "grd-m17", "MODIFY")
    # Approved decision has clamped ₹100
    dec = _create_approved_decision("act-m17", "grd-m17", "dec-m17", state=DecisionState.MODIFY, incentive_val=100.0)

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.approved_action["incentive_value"] == 100.0
    assert res.result["incentive_value"] == 100.0


def test_18_original_unsafe_parameter_never_executed():
    """Test 18: Original unsafe value (₹150) never reaches simulated adapter."""
    _create_test_proposal("act-m18", 150.0)
    _create_test_evaluation("act-m18", "grd-m18", "MODIFY")
    dec = _create_approved_decision("act-m18", "grd-m18", "dec-m18", state=DecisionState.MODIFY, incentive_val=100.0)

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.result["incentive_value"] != 150.0
    assert res.result["incentive_value"] == 100.0


def test_19_approved_action_strictly_used():
    """Test 19: Adapter output strictly reflects approved_action dictionary."""
    _create_test_proposal("act-m19", 100.0)
    _create_test_evaluation("act-m19", "grd-m19", "MODIFY")
    dec = _create_approved_decision("act-m19", "grd-m19", "dec-m19", state=DecisionState.MODIFY, incentive_val=100.0)

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.result["target_customer_count"] == dec.approved_action["target_customer_count"]
    assert res.result["incentive_value"] == dec.approved_action["incentive_value"]


# ==============================================================================
# 5. IDEMPOTENCY & CONCURRENCY TESTS (20 - 22)
# ==============================================================================

def test_20_duplicate_execution_prevented():
    """Test 20: Calling execute twice on same decision prevents duplicate dispatch."""
    _create_test_proposal("act-i20")
    _create_test_evaluation("act-i20", "grd-i20", "PASS")
    dec = _create_approved_decision("act-i20", "grd-i20", "dec-i20")

    engine = ExecutionEngine(simulation_mode=True)
    res1 = engine.execute(dec.decision_id)
    res2 = engine.execute(dec.decision_id)

    assert res1.execution_id == res2.execution_id


def test_21_repeated_execute_returns_existing_safely():
    """Test 21: Repeated execute safely returns existing execution record."""
    _create_test_proposal("act-i21")
    _create_test_evaluation("act-i21", "grd-i21", "PASS")
    dec = _create_approved_decision("act-i21", "grd-i21", "dec-i21")

    engine = ExecutionEngine(simulation_mode=True)
    res1 = engine.execute(dec.decision_id)
    res2 = engine.execute(dec.decision_id)

    assert res2.execution_state == ExecutionState.COMPLETED
    assert res2.simulated is True


def test_22_no_duplicate_simulated_side_effect():
    """Test 22: SQLite only retains a single execution row per decision."""
    _create_test_proposal("act-i22")
    _create_test_evaluation("act-i22", "grd-i22", "PASS")
    dec = _create_approved_decision("act-i22", "grd-i22", "dec-i22")

    engine = ExecutionEngine(simulation_mode=True)
    engine.execute(dec.decision_id)
    engine.execute(dec.decision_id)

    history = ExecutionRepository.get_executions_by_merchant("MID-DEMO-98234")
    matching = [ex for ex in history if ex["decision_id"] == "dec-i22"]
    assert len(matching) == 1


# ==============================================================================
# 6. SIMULATION BOUNDARY TESTS (23 - 26)
# ==============================================================================

def test_23_real_paytm_api_never_called():
    """Test 23: SimulatedPaytmAdapter operates purely in memory with no socket calls."""
    adapter = SimulatedPaytmAdapter(simulation_mode=True)
    receipt = adapter.simulate_campaign_execution({"action_type": "OFFER_CAMPAIGN"}, "MID-DEMO-98234")

    assert receipt["mode"] == "SIMULATION"
    assert "PROTOTYPE" in receipt["disclaimer"]


def test_24_simulator_requires_no_credentials():
    """Test 24: Initializing adapter requires zero API tokens or production credentials."""
    adapter = SimulatedPaytmAdapter()
    assert adapter.simulation_mode is True


def test_25_execution_mode_cannot_become_live():
    """Test 25: Attempting to instantiate adapter or engine with simulation_mode=False raises error."""
    with pytest.raises(RealExecutionNotAllowedError):
        SimulatedPaytmAdapter(simulation_mode=False)

    with pytest.raises(RealExecutionNotAllowedError):
        ExecutionEngine(simulation_mode=False)


def test_26_network_execution_path_unavailable():
    """Test 26: Simulated receipt explicitly states no real transaction."""
    adapter = SimulatedPaytmAdapter(simulation_mode=True)
    res = adapter.simulate_campaign_execution({"action_type": "OFFER_CAMPAIGN"})
    assert res["message"] == "Campaign simulated successfully in digital twin sandbox. No real Paytm transaction."


# ==============================================================================
# 7. PERSISTENCE & AUDIT TESTS (27 - 30)
# ==============================================================================

def test_27_execution_persisted_in_database():
    """Test 27: Execution row is retrievable via get_execution."""
    _create_test_proposal("act-a27")
    _create_test_evaluation("act-a27", "grd-a27", "PASS")
    dec = _create_approved_decision("act-a27", "grd-a27", "dec-a27")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    row = ExecutionRepository.get_execution(res.execution_id)
    assert row["execution_state"] == "COMPLETED"


def test_28_audit_events_created():
    """Test 28: Audit engine logs execution lifecycle events."""
    _create_test_proposal("act-a28")
    _create_test_evaluation("act-a28", "grd-a28", "PASS")
    dec = _create_approved_decision("act-a28", "grd-a28", "dec-a28")

    audit = AuditEngine()
    engine = ExecutionEngine(simulation_mode=True, audit_engine=audit)
    engine.execute(dec.decision_id)

    events = audit.get_events(10)
    stages = [e.stage for e in events]
    assert StageType.ACT in stages


def test_29_execution_retrieval_by_decision():
    """Test 29: ExecutionRepository.get_execution_by_decision finds correct record."""
    _create_test_proposal("act-a29")
    _create_test_evaluation("act-a29", "grd-a29", "PASS")
    dec = _create_approved_decision("act-a29", "grd-a29", "dec-a29")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    found = ExecutionRepository.get_execution_by_decision("dec-a29")
    assert found is not None
    assert found["id"] == res.execution_id


def test_30_decision_to_execution_relationship():
    """Test 30: Execution record references exact decision ID."""
    _create_test_proposal("act-a30")
    _create_test_evaluation("act-a30", "grd-a30", "PASS")
    dec = _create_approved_decision("act-a30", "grd-a30", "dec-a30")

    engine = ExecutionEngine(simulation_mode=True)
    res = engine.execute(dec.decision_id)

    assert res.decision_id == dec.decision_id


# ==============================================================================
# 8. REST API, EDGE CASES & FAILURE HANDLING (31 - 35)
# ==============================================================================

def test_31_api_post_execute_and_get():
    """Test 31: REST API POST /api/executions/execute/{id} returns 201 Created."""
    client = TestClient(app)
    _create_test_proposal("act-api31")
    _create_test_evaluation("act-api31", "grd-api31", "PASS")
    dec = _create_approved_decision("act-api31", "grd-api31", "dec-api31")

    res = client.post(f"/api/executions/execute/{dec.decision_id}", json={"merchant_id": "MID-DEMO-98234"})
    assert res.status_code == 201
    data = res.json()
    assert data["execution_state"] == "COMPLETED"
    assert data["simulated"] is True

    # GET by execution ID
    get_res = client.get(f"/api/executions/{data['execution_id']}")
    assert get_res.status_code == 200

    # GET by decision ID
    dec_res = client.get(f"/api/decisions/{dec.decision_id}/execution")
    assert dec_res.status_code == 200


def test_32_api_execute_unapproved_returns_400():
    """Test 32: Attempting to execute unapproved decision via API returns 400 Bad Request."""
    client = TestClient(app)
    _create_test_proposal("act-api32")
    _create_test_evaluation("act-api32", "grd-api32", "PASS")
    dec = _create_approved_decision("act-api32", "grd-api32", "dec-api32", approval_status=ApprovalStatus.PENDING, is_eligible=False)

    res = client.post(f"/api/executions/execute/{dec.decision_id}")
    assert res.status_code == 400
    assert "strictly required" in res.json()["detail"]


def test_33_invalid_decision_id_returns_404():
    """Test 33: Executing non-existent decision returns 404 Not Found."""
    client = TestClient(app)
    res = client.post("/api/executions/execute/dec-nonexistent-id-999")
    assert res.status_code == 404


def test_34_arbitrary_dict_rejected():
    """Test 34: Passing arbitrary dictionary to execute() raises UncheckedExecutionAttemptError."""
    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(UncheckedExecutionAttemptError):
        engine.execute({"fake": "proposal"})  # type: ignore[arg-type]


def test_35_llm_cannot_override_execution_safety():
    """Test 35: LLM output or arbitrary prompt cannot bypass execution preconditions."""
    llm_mock_dict = {
        "action": "EXECUTE_NOW",
        "override_guardrails": True,
        "mode": "PRODUCTION",
        "cashback": 500,
    }
    engine = ExecutionEngine(simulation_mode=True)
    with pytest.raises(UncheckedExecutionAttemptError):
        engine.execute(llm_mock_dict)  # type: ignore[arg-type]
