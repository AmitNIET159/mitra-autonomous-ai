"""Unit and Integration Tests for MITRA Phase 12: Human-in-the-Loop & Controlled Autonomy.

SAFETY CRITICAL INVARIANTS:
1. BLOCK + FULL_AUTONOMY = BLOCKED (No autonomy mode can bypass hard guardrails).
2. BLOCK cannot be approved by merchant or autonomy.
3. ESCALATE + ANY AUTONOMY = ESCALATED (Requires human review).
4. MODIFY: Proposed ₹150 -> Guardrail clamped ₹100 -> Autonomy evaluates ₹100 -> Executed ₹100.
   The original unsafe ₹150 is NEVER executed.
5. Zero LLM authority: Rule-based deterministic decision matrix.
6. Cryptographic audit chaining & correlation_id preservation.
"""
from datetime import datetime, timezone
import json
import pytest
from starlette.testclient import TestClient

from app.database.connection import get_connection, init_db
from app.database.repository import (
    ActionRepository,
    AuditRepository,
    AutonomyRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
    MerchantRepository,
    SignalRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.autonomy_engine.engine import AutonomyPolicyEngine
from app.engines.autonomy_engine.rules import (
    AUTO_APPROVE_SAFE_RISK_THRESHOLD,
    FULL_AUTONOMY_RISK_THRESHOLD,
    BlockedAutonomyOverrideError,
    StaleAutonomyEvaluationError,
    determine_autonomy_verdict,
    evaluate_16_safety_conditions,
    extract_effective_parameters,
)
from app.engines.decision_engine.engine import DecisionEngine
from app.engines.execution_engine.engine import ExecutionEngine
from app.engines.explainability_engine.engine import ExplainabilityEngine
from app.main import app
from app.models.contracts import ActionProposal, AutonomyEvaluation, Decision, GuardrailEvaluation
from app.models.enums import (
    ActionType,
    ActorType,
    ApprovalSource,
    ApprovalStatus,
    AutonomyMode,
    AutonomyStatus,
    DecisionState,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initializes local test database and clean state for each test."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_events WHERE id != 'AUDIT-INIT-001'")
        cursor.execute("DELETE FROM autonomy_evaluations")
        cursor.execute("DELETE FROM business_impacts")
        cursor.execute("DELETE FROM outcomes")
        cursor.execute("DELETE FROM executions")
        cursor.execute("DELETE FROM decisions")
        cursor.execute("DELETE FROM guardrail_evaluations")
        cursor.execute("DELETE FROM actions")
        cursor.execute("DELETE FROM investigations")
        cursor.execute("DELETE FROM signals")
        conn.commit()
    finally:
        conn.close()

    # Reset merchant policy to default
    MerchantRepository.upsert_merchant({
        "id": "MID-DEMO-98234",
        "name": "Sharma Kirana & General Store",
        "category": "Retail / Grocery",
        "location": "Delhi NCR",
        "minimum_margin": 0.10,
        "daily_budget": 12000.0,
        "max_discount": 100.0,
        "max_campaign_frequency": 3,
        "autonomy_level": "APPROVAL_REQUIRED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    MerchantRepository.update_autonomy_policy(
        "MID-DEMO-98234",
        autonomy_mode="APPROVAL_REQUIRED",
        auto_approval_risk_threshold=0.30,
        full_autonomy_risk_threshold=0.50,
        auto_approval_max_budget=12000.0,
        auto_approval_max_discount=100.0,
        require_human_for_modify=False,
        require_human_for_escalation=True,
    )


def create_mock_pipeline(
    signal_id: str = "sig-auto-01",
    action_id: str = "act-auto-01",
    guardrail_status: str = "PASS",
    risk_score: float = 0.18,
    incentive_value: float = 50.0,
    target_count: int = 100,
    budget_inr: float = 5000.0,
    modified_discount: Optional[float] = None,
    modifications: Optional[dict] = None,
    failed_checks: Optional[list] = None,
):
    """Helper to set up signal -> action -> guardrail -> decision in database."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Signal
    cursor.execute(
        """
        INSERT INTO signals (
            id, merchant_id, signal_type, severity, metric_name,
            baseline_value, observed_value, change_percentage,
            decline_percentage, description, detected_at, status, context_data
        ) VALUES (?, 'MID-DEMO-98234', 'EVENING_ORDER_DECLINE', 'HIGH', 'evening_orders', 410.0, 291.0, -29.0, 29.0, 'Anomaly', ?, 'ACTIVE', '{}')
        """,
        (signal_id, now_iso),
    )

    # 2. Action
    params = {
        "discount_amount": incentive_value,
        "target_count": target_count,
        "budget_inr": budget_inr,
        "risk_score": risk_score,
    }
    cursor.execute(
        """
        INSERT INTO actions (
            id, merchant_id, signal_id, action_type, parameters, status, created_at
        ) VALUES (?, 'MID-DEMO-98234', ?, 'OFFER_CAMPAIGN', ?, 'PROPOSED', ?)
        """,
        (action_id, signal_id, json.dumps(params), now_iso),
    )
    conn.commit()
    conn.close()

    # 3. Guardrail Evaluation
    mods = modifications or {}
    origs = {}
    if modified_discount is not None:
        mods["discount_amount"] = modified_discount
        origs["discount_amount"] = incentive_value

    grd_id = f"grd-{action_id[4:]}"
    f_checks = failed_checks or ([] if guardrail_status != "BLOCK" else ["DAILY_BUDGET_EXCEEDED"])
    p_checks = ["MIN_MARGIN", "CUSTOMER_ELIGIBILITY"] if guardrail_status != "BLOCK" else []
    
    GuardrailRepository.create_or_update_evaluation(
        evaluation_id=grd_id,
        action_id=action_id,
        merchant_id="MID-DEMO-98234",
        overall_status=guardrail_status,
        passed=guardrail_status in ("PASS", "MODIFY"),
        checks=[{"rule": "MIN_MARGIN", "status": "PASS"}],
        passed_checks=p_checks,
        failed_checks=f_checks,
        warnings=[],
        modifications=mods,
        original_values=origs,
        modified_values=mods,
        notes="Guardrail evaluated",
    )

    # 4. Decision via DecisionEngine
    dec_engine = DecisionEngine()
    decision = dec_engine.create_decision_from_persisted_evaluation(
        action_id=action_id,
        merchant_id="MID-DEMO-98234",
    )

    return signal_id, action_id, grd_id, decision.decision_id


# ==============================================================================
# SECTION 1: ENUM VALIDATION & DEFAULT POLICY TESTS
# ==============================================================================

def test_autonomy_mode_enums():
    """Verifies supported AutonomyMode enum values."""
    assert AutonomyMode.APPROVAL_REQUIRED.value == "APPROVAL_REQUIRED"
    assert AutonomyMode.AUTO_APPROVE_SAFE.value == "AUTO_APPROVE_SAFE"
    assert AutonomyMode.FULL_AUTONOMY.value == "FULL_AUTONOMY"


def test_approval_source_enums():
    """Verifies ApprovalSource enum values."""
    assert ApprovalSource.HUMAN_APPROVED.value == "HUMAN_APPROVED"
    assert ApprovalSource.AUTO_APPROVED.value == "AUTO_APPROVED"
    assert ApprovalSource.REJECTED.value == "REJECTED"
    assert ApprovalSource.BLOCKED.value == "BLOCKED"
    assert ApprovalSource.ESCALATED.value == "ESCALATED"
    assert ApprovalSource.PENDING.value == "PENDING"


def test_actor_type_enums():
    """Verifies ActorType enum values."""
    assert ActorType.MERCHANT.value == "MERCHANT"
    assert ActorType.AUTONOMY_POLICY.value == "AUTONOMY_POLICY"
    assert ActorType.SYSTEM.value == "SYSTEM"


def test_default_merchant_autonomy_mode():
    """Demo merchant profile defaults strictly to APPROVAL_REQUIRED."""
    policy = MerchantRepository.get_autonomy_policy("MID-DEMO-98234")
    assert policy["autonomy_mode"] == "APPROVAL_REQUIRED"
    assert policy["auto_approval_risk_threshold"] == 0.30
    assert policy["full_autonomy_risk_threshold"] == 0.50


# ==============================================================================
# SECTION 2: CRITICAL SAFETY INVARIANTS (BLOCK, MODIFY, ESCALATE)
# ==============================================================================

def test_safety_invariant_block_plus_full_autonomy_remains_blocked():
    """CRITICAL: Guardrail BLOCK + FULL_AUTONOMY must remain strictly BLOCKED."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="FULL_AUTONOMY")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-blk-01",
        action_id="act-blk-01",
        guardrail_status="BLOCK",
        risk_score=0.10,  # Even with ultra-low risk score!
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.blocked is True
    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_source == ApprovalSource.BLOCKED
    assert eval_result.autonomy_status == AutonomyStatus.BLOCKED
    assert "cannot be bypassed" in eval_result.auto_approval_reason


def test_safety_invariant_block_plus_approval_required_remains_blocked():
    """CRITICAL: Guardrail BLOCK + APPROVAL_REQUIRED must remain strictly BLOCKED."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="APPROVAL_REQUIRED")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-blk-02",
        action_id="act-blk-02",
        guardrail_status="BLOCK",
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.blocked is True
    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_source == ApprovalSource.BLOCKED


def test_safety_invariant_blocked_action_cannot_be_merchant_approved():
    """CRITICAL: Merchant cannot sign off / approve an action that was BLOCKED."""
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-blk-03",
        action_id="act-blk-03",
        guardrail_status="BLOCK",
    )

    client = TestClient(app)
    resp = client.post(f"/api/autonomy/{action_id}/approve", json={"merchant_id": "MID-DEMO-98234"})
    assert resp.status_code == 400
    assert "Blocked actions cannot be approved" in resp.json()["detail"]


def test_safety_invariant_modify_clamping_enforced():
    """CRITICAL: Proposed ₹150 -> Clamped ₹100 -> Autonomy evaluates ₹100 -> Executed ₹100."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-mod-01",
        action_id="act-mod-01",
        guardrail_status="MODIFY",
        incentive_value=150.0,  # Proposed ₹150 (violates ₹100 max)
        modified_discount=100.0,  # Clamped to ₹100
        risk_score=0.20,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is True
    assert eval_result.approval_source == ApprovalSource.AUTO_APPROVED
    assert eval_result.approved_action["clamped"] is True
    assert eval_result.approved_action["parameters"]["discount_amount"] == 100.0

    # Verify ExecutionEngine executes ₹100, not ₹150
    exec_engine = ExecutionEngine()
    exec_result = exec_engine.execute(dec_id)
    assert exec_result.success is True
    assert exec_result.approved_action["parameters"]["discount_amount"] == 100.0


def test_safety_invariant_escalate_requires_human_review_under_full_autonomy():
    """CRITICAL: Guardrail ESCALATE cannot be auto-approved even in FULL_AUTONOMY mode."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="FULL_AUTONOMY")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-esc-01",
        action_id="act-esc-01",
        guardrail_status="ESCALATE",
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.escalated is True
    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_source == ApprovalSource.ESCALATED
    assert "Automatic execution is strictly prohibited" in eval_result.auto_approval_reason


# ==============================================================================
# SECTION 3: DETERMINISTIC POLICY MODES & RISK THRESHOLD TESTS
# ==============================================================================

def test_mode_approval_required_gates_execution():
    """APPROVAL_REQUIRED requires merchant approval even for low-risk actions."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="APPROVAL_REQUIRED")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-appr-01",
        action_id="act-appr-01",
        guardrail_status="PASS",
        risk_score=0.12,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.approval_required is True
    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_source == ApprovalSource.PENDING

    # Verify execution is blocked until merchant approves
    exec_engine = ExecutionEngine()
    with pytest.raises(Exception):
        exec_engine.execute(dec_id)


def test_mode_auto_approve_safe_clears_qualifying_action():
    """AUTO_APPROVE_SAFE auto-approves actions with risk <= 0.30 that pass all conditions."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-safe-01",
        action_id="act-safe-01",
        guardrail_status="PASS",
        risk_score=0.18,  # <= 0.30
        incentive_value=50.0,
        target_count=100,
        budget_inr=5000.0,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is True
    assert eval_result.approval_required is False
    assert eval_result.approval_source == ApprovalSource.AUTO_APPROVED
    assert eval_result.actor_type == ActorType.AUTONOMY_POLICY
    assert len(eval_result.passed_checks) == 16
    assert len(eval_result.failed_checks) == 0

    # Verify Decision is now execution eligible
    dec_row = DecisionRepository.get_decision_by_action(action_id)
    assert dec_row["approval_status"] == "APPROVED"
    assert dec_row["is_execution_eligible"] == 1

    # Verify execution succeeds immediately
    exec_engine = ExecutionEngine()
    exec_res = exec_engine.execute(dec_id)
    assert exec_res.success is True


def test_mode_auto_approve_safe_rejects_exceeded_risk():
    """AUTO_APPROVE_SAFE falls back to human approval if risk > 0.30."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-safe-02",
        action_id="act-safe-02",
        guardrail_status="PASS",
        risk_score=0.35,  # > 0.30 threshold
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_required is True
    assert eval_result.approval_source == ApprovalSource.PENDING
    assert any("exceeds threshold" in c for c in eval_result.failed_checks)


def test_mode_full_autonomy_allows_higher_risk():
    """FULL_AUTONOMY clears actions up to risk <= 0.50."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="FULL_AUTONOMY")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-full-01",
        action_id="act-full-01",
        guardrail_status="PASS",
        risk_score=0.45,  # > 0.30 but <= 0.50
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is True
    assert eval_result.approval_source == ApprovalSource.AUTO_APPROVED


def test_mode_full_autonomy_rejects_extreme_risk():
    """FULL_AUTONOMY falls back to human approval if risk > 0.50."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="FULL_AUTONOMY")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-full-02",
        action_id="act-full-02",
        guardrail_status="PASS",
        risk_score=0.65,  # > 0.50
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_required is True


# ==============================================================================
# SECTION 4: THE 16 DETERMINISTIC CONDITIONS TESTS
# ==============================================================================

def test_condition_budget_limit_exceeded():
    """Condition 7: Campaign budget exceeding threshold prevents auto-approval."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-cond-01",
        action_id="act-cond-01",
        guardrail_status="PASS",
        budget_inr=15000.0,  # Exceeds 12000 default
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is False
    assert any("Campaign cost" in c and "exceeds limit" in c for c in eval_result.failed_checks)


def test_condition_discount_limit_exceeded():
    """Condition 8: Discount exceeding maximum limit prevents auto-approval."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-cond-02",
        action_id="act-cond-02",
        guardrail_status="PASS",
        incentive_value=120.0,  # Exceeds 100 default
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is False
    assert any("Clamped discount" in c and "exceeds max limit" in c for c in eval_result.failed_checks)


def test_condition_audience_out_of_bounds():
    """Condition 6: Customer count of 0 or exceeding maximum prevents auto-approval."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-cond-03",
        action_id="act-cond-03",
        guardrail_status="PASS",
        target_count=800,  # Exceeds 600
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    assert eval_result.auto_approval_allowed is False
    assert any("Target customer count" in c and "out of bounds" in c for c in eval_result.failed_checks)


# ==============================================================================
# SECTION 5: HUMAN APPROVAL & REJECTION WORKFLOWS
# ==============================================================================

def test_human_sign_off_records_merchant_actor():
    """Merchant approval tags approval_source as HUMAN_APPROVED and actor as MERCHANT."""
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-hmn-01",
        action_id="act-hmn-01",
        guardrail_status="PASS",
    )

    client = TestClient(app)
    resp = client.post(
        f"/api/autonomy/{action_id}/approve",
        json={"merchant_id": "MID-DEMO-98234", "approver": "Ramesh Sharma"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approval_source"] == ApprovalSource.HUMAN_APPROVED.value
    assert data["actor_type"] == ActorType.MERCHANT.value
    assert data["approval_required"] is False


def test_human_rejection_marks_rejected_and_bars_execution():
    """Merchant rejection tags REJECTED and permanently bars execution."""
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-rej-01",
        action_id="act-rej-01",
        guardrail_status="PASS",
    )

    client = TestClient(app)
    resp = client.post(
        f"/api/autonomy/{action_id}/reject",
        json={"merchant_id": "MID-DEMO-98234", "reason": "Budget cut"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["approval_source"] == ApprovalSource.REJECTED.value

    # Verify execution is strictly rejected
    exec_engine = ExecutionEngine()
    with pytest.raises(Exception):
        exec_engine.execute(dec_id)


# ==============================================================================
# SECTION 6: STALE STATE & IDEMPOTENCY TESTS
# ==============================================================================

def test_stale_hash_rejection():
    """Altering action proposal after decision synthesis raises Stale error."""
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-stl-01",
        action_id="act-stl-01",
        guardrail_status="PASS",
    )

    # Mutate parameters out of band
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE actions SET parameters = ? WHERE id = ?",
        (json.dumps({"discount_amount": 999.0, "budget_inr": 99999.0}), action_id),
    )
    conn.commit()
    conn.close()

    engine = AutonomyPolicyEngine()
    with pytest.raises(StaleAutonomyEvaluationError):
        engine.evaluate(action_id)


def test_idempotent_autonomy_evaluation():
    """Repeated evaluation on unchanged action returns consistent result."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-idm-01",
        action_id="act-idm-01",
        guardrail_status="PASS",
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval1 = engine.evaluate(action_id)
    eval2 = engine.evaluate(action_id)

    assert eval1.autonomy_mode == eval2.autonomy_mode
    assert eval1.auto_approval_allowed == eval2.auto_approval_allowed
    assert eval1.approval_source == eval2.approval_source


# ==============================================================================
# SECTION 7: AUDIT CHAINING & EXPLAINABILITY INTEGRATION
# ==============================================================================

def test_audit_event_generation_and_chaining():
    """Autonomy evaluation creates tamper-evident audit events with valid SHA-256 chain."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-aud-01",
        action_id="act-aud-01",
        guardrail_status="PASS",
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)

    events = AuditRepository.get_events_by_correlation_id(eval_result.correlation_id)
    assert len(events) >= 2

    # Check for AUTO_APPROVAL_GRANTED event
    approval_events = [e for e in events if "Auto-approval granted" in e.get("description", "")]
    assert len(approval_events) == 1

    # Verify cryptographic integrity
    audit_engine = AuditEngine()
    verification = audit_engine.verify_audit_chain(eval_result.correlation_id, events)
    assert verification.verified is True
    assert verification.tampered is False


def test_explainability_summary_includes_autonomy():
    """ExplainabilityEngine includes structured autonomy explanation and facts."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-exp-01",
        action_id="act-exp-01",
        guardrail_status="PASS",
        risk_score=0.15,
    )

    aut_engine = AutonomyPolicyEngine()
    eval_res = aut_engine.evaluate(action_id)

    exp_engine = ExplainabilityEngine()
    summary = exp_engine.generate_explanation(eval_res.correlation_id)

    assert summary.autonomy_summary is not None
    assert summary.autonomy_summary["autonomy_mode"] == "AUTO_APPROVE_SAFE"
    assert summary.autonomy_summary["auto_approval_allowed"] is True
    assert "AUTO-APPROVED BY DETERMINISTIC POLICY" in summary.autonomy_summary["explanation"]

    # Verify autonomy facts exist
    fact_types = [f.fact_type for f in summary.facts]
    assert "AUTONOMY_MODE" in fact_types
    assert "EVALUATED_RISK" in fact_types


# ==============================================================================
# SECTION 8: REST API ENDPOINTS
# ==============================================================================

def test_api_merchant_autonomy_get_and_put():
    """Tests GET and PUT on /api/merchants/{id}/autonomy."""
    client = TestClient(app)

    # GET default
    res = client.get("/api/merchants/MID-DEMO-98234/autonomy")
    assert res.status_code == 200
    assert res.json()["autonomy_mode"] == "APPROVAL_REQUIRED"

    # PUT update mode
    update_res = client.put(
        "/api/merchants/MID-DEMO-98234/autonomy",
        json={"autonomy_mode": "FULL_AUTONOMY", "auto_approval_risk_threshold": 0.25},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["autonomy_mode"] == "FULL_AUTONOMY"
    assert data["auto_approval_risk_threshold"] == 0.25


def test_api_autonomy_evaluate_endpoint():
    """Tests POST /api/autonomy/evaluate/{action_id}."""
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-api-01",
        action_id="act-api-01",
        guardrail_status="PASS",
        risk_score=0.15,
    )

    client = TestClient(app)
    res = client.post(f"/api/autonomy/evaluate/{action_id}?merchant_id=MID-DEMO-98234")
    assert res.status_code == 200
    assert res.json()["approval_required"] is True


def test_api_autonomy_workflow_endpoint():
    """Tests GET /api/autonomy/workflow/{correlation_id}."""
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-wf-01",
        action_id="act-wf-01",
        guardrail_status="PASS",
        risk_score=0.15,
    )

    aut_engine = AutonomyPolicyEngine()
    eval_res = aut_engine.evaluate(action_id)

    client = TestClient(app)
    res = client.get(f"/api/autonomy/workflow/{eval_res.correlation_id}")
    assert res.status_code == 200
    assert res.json()["action_id"] == action_id


# ==============================================================================
# SECTION 9: ADDITIONAL SAFETY ASSERTIONS & PARAMETER EXTRACTION
# ==============================================================================

def test_autonomy_status_enums():
    """Verifies AutonomyStatus enum values."""
    assert AutonomyStatus.APPROVAL_REQUIRED.value == "APPROVAL_REQUIRED"
    assert AutonomyStatus.AUTO_APPROVED.value == "AUTO_APPROVED"
    assert AutonomyStatus.HUMAN_APPROVED.value == "HUMAN_APPROVED"
    assert AutonomyStatus.BLOCKED.value == "BLOCKED"
    assert AutonomyStatus.ESCALATED.value == "ESCALATED"
    assert AutonomyStatus.REJECTED.value == "REJECTED"


def test_policy_threshold_constants():
    """Verifies demo policy threshold constants."""
    assert AUTO_APPROVE_SAFE_RISK_THRESHOLD == 0.30
    assert FULL_AUTONOMY_RISK_THRESHOLD == 0.50


def test_extract_effective_parameters_unmodified():
    """Verifies parameters remain unchanged when no guardrail modifications exist."""
    prop = ActionProposal(
        action_id="act-test-01",
        signal_id="sig-test-01",
        merchant_id="MID-DEMO-98234",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount_amount": 50.0, "budget_inr": 2500.0},
        reason="Test",
    )
    grd = GuardrailEvaluation(
        action_id="act-test-01",
        overall_status=DecisionState.PASS,
        passed=True,
    )
    eff = extract_effective_parameters(prop, grd)
    assert eff["discount_amount"] == 50.0
    assert eff["budget_inr"] == 2500.0


def test_extract_effective_parameters_clamped():
    """Verifies parameters strictly adopt clamped values when guardrail modified them."""
    prop = ActionProposal(
        action_id="act-test-02",
        signal_id="sig-test-02",
        merchant_id="MID-DEMO-98234",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount_amount": 150.0, "budget_inr": 7500.0},
        reason="Test",
    )
    grd = GuardrailEvaluation(
        action_id="act-test-02",
        overall_status=DecisionState.MODIFY,
        passed=True,
        modifications={"discount_amount": 100.0},
        modified_values={"discount_amount": 100.0},
        original_values={"discount_amount": 150.0},
    )
    eff = extract_effective_parameters(prop, grd)
    assert eff["discount_amount"] == 100.0
    assert eff["discount_amount"] != 150.0


def test_extract_effective_parameters_with_decision_approved_action():
    """Verifies decision approved_action parameters take authoritative precedence."""
    prop = ActionProposal(
        action_id="act-test-03",
        signal_id="sig-test-03",
        merchant_id="MID-DEMO-98234",
        action_type=ActionType.OFFER_CAMPAIGN,
        parameters={"discount_amount": 150.0},
        reason="Test",
    )
    grd = GuardrailEvaluation(
        action_id="act-test-03",
        overall_status=DecisionState.MODIFY,
        passed=True,
    )
    dec = Decision(
        decision_id="dec-test-03",
        action_id="act-test-03",
        approved_action={"parameters": {"discount_amount": 100.0}},
    )
    eff = extract_effective_parameters(prop, grd, dec)
    assert eff["discount_amount"] == 100.0


def test_safety_assertion_llm_cannot_change_autonomy_status():
    """ASSERT: LLM outputs cannot modify or bypass autonomy policy decisions."""
    # LLM raw proposal carries risk_score=0.99
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-llm-01",
        action_id="act-llm-01",
        guardrail_status="PASS",
        risk_score=0.99,
    )

    engine = AutonomyPolicyEngine()
    eval_result = engine.evaluate(action_id)
    # LLM cannot force auto-approval
    assert eval_result.auto_approval_allowed is False
    assert eval_result.approval_required is True


def test_safety_assertion_llm_cannot_approve_action():
    """ASSERT: LLM cannot approve an action directly."""
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-llm-02",
        action_id="act-llm-02",
        guardrail_status="PASS",
    )

    # Attempting to execute with unapproved decision fails
    exec_engine = ExecutionEngine()
    with pytest.raises(Exception):
        exec_engine.execute(dec_id)


def test_safety_assertion_llm_cannot_bypass_guardrails():
    """ASSERT: LLM cannot bypass guardrails regardless of requested autonomy."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="FULL_AUTONOMY")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-llm-03",
        action_id="act-llm-03",
        guardrail_status="BLOCK",
        risk_score=0.01,
    )

    engine = AutonomyPolicyEngine()
    eval_res = engine.evaluate(action_id)
    assert eval_res.blocked is True
    assert eval_res.auto_approval_allowed is False


def test_safety_assertion_rejected_decision_cannot_execute():
    """ASSERT: REJECTED decision cannot execute under any circumstance."""
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-rej-02",
        action_id="act-rej-02",
        guardrail_status="PASS",
    )

    client = TestClient(app)
    client.post(f"/api/autonomy/{action_id}/reject", json={"merchant_id": "MID-DEMO-98234"})

    exec_engine = ExecutionEngine()
    with pytest.raises(Exception):
        exec_engine.execute(dec_id)


def test_safety_assertion_escalated_decision_cannot_auto_execute():
    """ASSERT: ESCALATED decision cannot auto-execute."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="FULL_AUTONOMY")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-esc-02",
        action_id="act-esc-02",
        guardrail_status="ESCALATE",
    )

    engine = AutonomyPolicyEngine()
    eval_res = engine.evaluate(action_id)
    assert eval_res.auto_approval_allowed is False

    exec_engine = ExecutionEngine()
    with pytest.raises(Exception):
        exec_engine.execute(dec_id)


def test_safety_assertion_execution_amount_matches_clamped_not_proposed():
    """ASSERT: Execution amount strictly matches clamped ₹100, NEVER original ₹150."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-clm-01",
        action_id="act-clm-01",
        guardrail_status="MODIFY",
        incentive_value=150.0,
        modified_discount=100.0,
        risk_score=0.20,
    )

    engine = AutonomyPolicyEngine()
    eval_res = engine.evaluate(action_id)
    assert eval_res.auto_approval_allowed is True

    exec_engine = ExecutionEngine()
    res = exec_engine.execute(dec_id)
    assert res.approved_action["parameters"]["discount_amount"] == 100.0
    assert res.approved_action["parameters"]["discount_amount"] != 150.0


def test_autonomy_eval_missing_action_raises_404():
    """Evaluating autonomy for nonexistent action raises 404."""
    client = TestClient(app)
    res = client.post("/api/autonomy/evaluate/act-nonexistent-99")
    assert res.status_code == 404


def test_autonomy_eval_missing_guardrail_raises_409():
    """Evaluating autonomy when guardrail is missing raises 409 Conflict."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO signals (id, merchant_id, signal_type, severity, metric_name, baseline_value, observed_value, description, detected_at, status)
            VALUES ('sig-dummy-01', 'MID-DEMO-98234', 'OFFER_CAMPAIGN', 'HIGH', 'evening_orders', 100, 70, 'desc', ?, 'ACTIVE')
            """,
            (now_iso,),
        )
        cursor.execute(
            """
            INSERT INTO actions (id, merchant_id, signal_id, action_type, parameters, status, created_at)
            VALUES ('act-nogrd-01', 'MID-DEMO-98234', 'sig-dummy-01', 'OFFER_CAMPAIGN', '{}', 'PROPOSED', ?)
            """,
            (now_iso,),
        )
        conn.commit()
    finally:
        conn.close()

    client = TestClient(app)
    res = client.post("/api/autonomy/evaluate/act-nogrd-01")
    assert res.status_code == 409


def test_autonomy_eval_repository_get_by_decision():
    """Verifies AutonomyRepository.get_by_decision retrieval."""
    _, action_id, _, dec_id = create_mock_pipeline(
        signal_id="sig-rep-01",
        action_id="act-rep-01",
        guardrail_status="PASS",
    )

    engine = AutonomyPolicyEngine()
    eval_res = engine.evaluate(action_id)

    fetched = AutonomyRepository.get_by_decision(dec_id)
    assert fetched is not None
    assert fetched["action_id"] == action_id
    assert fetched["decision_id"] == dec_id


def test_autonomy_eval_repository_get_by_id():
    """Verifies AutonomyRepository.get_evaluation by evaluation_id."""
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-rep-02",
        action_id="act-rep-02",
        guardrail_status="PASS",
    )

    engine = AutonomyPolicyEngine()
    eval_res = engine.evaluate(action_id)

    fetched = AutonomyRepository.get_evaluation(eval_res.autonomy_evaluation_id)
    assert fetched is not None
    assert fetched["id"] == eval_res.autonomy_evaluation_id


def test_merchant_autonomy_put_invalid_mode_raises_422():
    """Updating merchant autonomy policy with invalid enum string returns 422."""
    client = TestClient(app)
    res = client.put(
        "/api/merchants/MID-DEMO-98234/autonomy",
        json={"autonomy_mode": "INVALID_SUPER_MODE"},
    )
    assert res.status_code == 422


def test_merchant_autonomy_put_nonexistent_merchant_raises_404():
    """Updating autonomy for nonexistent merchant returns 404."""
    client = TestClient(app)
    res = client.put(
        "/api/merchants/MID-NOTFOUND-9999/autonomy",
        json={"autonomy_mode": "AUTO_APPROVE_SAFE"},
    )
    assert res.status_code == 404


def test_audit_payload_sanitization_for_autonomy_events():
    """Verifies sensitive tokens in audit payloads are redacted in autonomy events."""
    audit_engine = AuditEngine()
    sanitized = audit_engine.sanitize_payload({
        "action_id": "act-123",
        "api_key": "sec_live_12345",
        "token": "bearer_secret_tok",
        "nested": {"password": "admin_password", "risk": 0.2},
    })
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["nested"]["password"] == "[REDACTED]"
    assert sanitized["nested"]["risk"] == 0.2


def test_simulation_mode_boundary_flag_is_true():
    """Verifies prototype simulation boundary flag is True across all autonomy models."""
    MerchantRepository.update_autonomy_policy("MID-DEMO-98234", autonomy_mode="AUTO_APPROVE_SAFE")
    _, action_id, _, _ = create_mock_pipeline(
        signal_id="sig-sim-01",
        action_id="act-sim-01",
        guardrail_status="PASS",
        risk_score=0.15,
    )

    engine = AutonomyPolicyEngine()
    eval_res = engine.evaluate(action_id)
    assert eval_res.simulation_mode is True

    policy = MerchantRepository.get_autonomy_policy("MID-DEMO-98234")
    assert policy["simulated"] is True
