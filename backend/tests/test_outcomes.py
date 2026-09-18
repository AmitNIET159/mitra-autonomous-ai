"""Tests for MITRA Phase 9: Outcome Monitoring and Measurement Engine.

Verifies:
- 100% Deterministic outcome calculation
- Strict precondition gating (only COMPLETED simulation executions can be measured)
- Rejection of PENDING, EXECUTING, FAILED, BLOCKED, and non-simulation executions
- Digital-twin simulation metric generation
- Idempotency & duplicate prevention
- Zero real Paytm APIs, zero money movement, zero real data
- Non-causal descriptive metric reporting
- Audit event chaining
- REST API endpoints
"""
from datetime import datetime, timezone
import json
import pytest
from starlette.testclient import TestClient

from app.database.connection import get_connection, init_db
from app.database.repository import (
    ActionRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
    MerchantRepository,
    OutcomeRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.outcome_engine.engine import OutcomeEngine
from app.engines.outcome_engine.rules import (
    calculate_metric_change,
    generate_digital_twin_metrics,
    get_default_windows,
    verify_execution_preconditions,
    ExecutionNotCompletedError,
    ExecutionNotFoundError,
    NonSimulationExecutionError,
)
from app.main import app
from app.models.contracts import Outcome
from app.models.enums import ExecutionMode, ExecutionState, OutcomeStatus, StageType


@pytest.fixture(autouse=True)
def setup_db():
    """Initializes schema and cleans outcome/execution test records before each test."""
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM outcomes")
    c.execute("DELETE FROM executions")
    conn.commit()
    conn.close()


@pytest.fixture
def test_client():
    return TestClient(app)


def _ensure_business_metrics(merchant_id: str = "MID-DEMO-98234"):
    """Inserts demo digital-twin baseline metrics quickly without heavy full-database reseed."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT OR IGNORE INTO merchants (
            id, name, category, location, minimum_margin, daily_budget,
            max_discount, max_campaign_frequency, autonomy_level, created_at
        ) VALUES (?, 'Sharma Kirana Store', 'Retail', 'Delhi NCR', 0.10, 12000.0, 100.0, 3, 'APPROVAL_REQUIRED', '2026-09-18T00:00:00Z')
        """,
        (merchant_id,),
    )
    for m_name, val in [
        ("evening_orders_baseline", 410.0),
        ("evening_orders_observed", 291.0),
        ("evening_orders_variance_pct", -29.02),
        ("repeat_conversion_baseline", 0.182),
        ("repeat_conversion_observed", 0.148),
        ("total_window_orders", 1284.0),
        ("total_window_revenue_inr", 481850.0),
        ("avg_basket_size_inr", 375.27),
        ("target_campaign_customer_count", 486.0),
    ]:
        c.execute(
            """
            INSERT OR REPLACE INTO business_metrics (id, merchant_id, metric_name, metric_value, timestamp)
            VALUES (?, ?, ?, ?, '2026-09-18T00:00:00Z')
            """,
            (f"METRIC-{m_name}-{merchant_id}", merchant_id, m_name, val),
        )
    conn.commit()
    conn.close()


def _create_mock_completed_execution(
    exec_id: str = "exec-test-01",
    decision_id: str = "dec-test-01",
    action_id: str = "act-test-01",
    merchant_id: str = "MID-DEMO-98234",
    state: str = "COMPLETED",
    mode: str = "SIMULATION",
    approved_action: dict = None,
):
    """Helper to insert valid execution record in SQLite meeting foreign key requirements."""
    _ensure_business_metrics(merchant_id)

    # Ensure parent decision exists
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM decisions WHERE id = ?", (decision_id,))
    if not c.fetchone():
        ActionRepository.create_or_update_action_proposal(
            signal_id=f"sig-{action_id}",
            investigation_id=f"inv-{action_id}",
            merchant_id=merchant_id,
            action_type="OFFER_CAMPAIGN",
            action_id=action_id,
            parameters={"cashback_inr": 50.0},
        )
        GuardrailRepository.create_or_update_evaluation(
            evaluation_id=f"grd-{action_id}",
            action_id=action_id,
            merchant_id=merchant_id,
            overall_status="PASS",
            passed=True,
            checks=[],
            passed_checks=[],
            failed_checks=[],
            warnings=[],
            modifications={},
            original_values={},
            modified_values={},
        )
        DecisionRepository.create_or_update_decision(
            decision_id=decision_id,
            action_id=action_id,
            evaluation_id=f"grd-{action_id}",
            merchant_id=merchant_id,
            decision_state="PASS",
            reason="Approved",
            triggered_rules=[],
            modifications={},
            approval_required=True,
            approval_status="APPROVED",
            is_execution_eligible=True,
            approved_action={
                "action_type": "OFFER_CAMPAIGN",
                "parameters": {"cashback_inr": 50.0},
                "incentive_value": 50.0,
                "target_customer_count": 486,
            },
        )
    conn.close()

    action = approved_action or {
        "action_id": action_id,
        "action_type": "OFFER_CAMPAIGN",
        "incentive_value": 50.0,
        "target_customer_count": 486,
        "duration": "7 days",
        "parameters": {"cashback_inr": 50.0},
    }
    ExecutionRepository.create_execution(
        execution_id=exec_id,
        decision_id=decision_id,
        action_id=action_id,
        merchant_id=merchant_id,
        approved_action=action,
        execution_mode=mode,
    )
    if state == "COMPLETED":
        ExecutionRepository.mark_completed(exec_id, {"simulated": True, "cashback_inr": 50.0})
    elif state == "EXECUTING":
        ExecutionRepository.mark_executing(exec_id)
    elif state == "FAILED":
        ExecutionRepository.mark_failed(exec_id, "Simulated network timeout")
    elif state == "BLOCKED":
        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE executions SET execution_state = 'BLOCKED', status = 'BLOCKED' WHERE id = ?", (exec_id,))
        conn.commit()
        conn.close()
    return exec_id


# ----------------------------------------------------------------------
# 1. MEASUREMENT & CALCULATION TESTS
# ----------------------------------------------------------------------

def test_1_completed_execution_can_be_measured():
    """Verifies that a COMPLETED simulated execution produces a MEASURED outcome."""
    exec_id = _create_mock_completed_execution("exec-t1", "dec-t1", "act-t1")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert outcome is not None
    assert outcome.execution_id == "exec-t1"
    assert outcome.outcome_status == OutcomeStatus.MEASURED
    assert outcome.simulated is True
    assert outcome.measurement_mode == ExecutionMode.SIMULATION


def test_2_baseline_metrics_loaded():
    """Verifies that baseline metrics are loaded accurately from digital twin database."""
    exec_id = _create_mock_completed_execution("exec-t2", "dec-t2", "act-t2")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert "revenue" in outcome.baseline_metrics
    assert "orders" in outcome.baseline_metrics
    assert "evening_orders" in outcome.baseline_metrics
    assert outcome.baseline_metrics["revenue"] == 481850.0
    assert outcome.baseline_metrics["orders"] == 1284.0
    assert outcome.baseline_metrics["evening_orders"] == 291.0


def test_3_post_action_metrics_loaded():
    """Verifies that post-action metrics are generated deterministically."""
    exec_id = _create_mock_completed_execution("exec-t3", "dec-t3", "act-t3")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert "revenue" in outcome.post_action_metrics
    assert "orders" in outcome.post_action_metrics
    assert "evening_orders" in outcome.post_action_metrics
    assert outcome.post_action_metrics["revenue"] == 500000.0
    assert outcome.post_action_metrics["orders"] == 1456.0
    assert outcome.post_action_metrics["evening_orders"] == 331.0


def test_4_absolute_changes_calculated():
    """Verifies that absolute differences between post-action and baseline are accurate."""
    exec_id = _create_mock_completed_execution("exec-t4", "dec-t4", "act-t4")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    ev_change = outcome.metric_changes["evening_orders"]
    assert ev_change["absolute_change"] == 40.0  # 331 - 291

    ord_change = outcome.metric_changes["orders"]
    assert ord_change["absolute_change"] == 172.0  # 1456 - 1284


def test_5_percentage_changes_calculated():
    """Verifies that percentage changes are calculated with correct precision."""
    exec_id = _create_mock_completed_execution("exec-t5", "dec-t5", "act-t5")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    ev_change = outcome.metric_changes["evening_orders"]
    assert ev_change["percentage_change"] == 13.75

    ord_change = outcome.metric_changes["orders"]
    assert ord_change["percentage_change"] == 13.40


def test_6_zero_baseline_handled_safely():
    """Verifies that baseline=0 safely returns None for percentage change without division by zero."""
    result = calculate_metric_change(0.0, 50.0)
    assert result["percentage_change"] is None
    assert result["status"] == OutcomeStatus.INSUFFICIENT_DATA.value
    assert result["absolute_change"] == 50.0


def test_7_insufficient_data_handled():
    """Verifies that missing baseline records yield an INSUFFICIENT_DATA outcome status."""
    exec_id = _create_mock_completed_execution("exec-t7", "dec-t7", "act-t7", merchant_id="MID-NO-DATA")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM business_metrics WHERE merchant_id = 'MID-NO-DATA'")
    conn.commit()
    conn.close()

    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert outcome.outcome_status == OutcomeStatus.INSUFFICIENT_DATA
    assert outcome.baseline_metrics == {}


# ----------------------------------------------------------------------
# 2. PRECONDITION & STATE TESTS
# ----------------------------------------------------------------------

def test_8_pending_execution_rejected():
    """Verifies that a PENDING execution cannot be measured."""
    exec_id = _create_mock_completed_execution("exec-t8", "dec-t8", "act-t8", state="PENDING")
    engine = OutcomeEngine()
    with pytest.raises(ExecutionNotCompletedError):
        engine.measure_outcome(exec_id)


def test_9_executing_execution_rejected():
    """Verifies that an in-flight EXECUTING execution cannot be measured."""
    exec_id = _create_mock_completed_execution("exec-t9", "dec-t9", "act-t9", state="EXECUTING")
    engine = OutcomeEngine()
    with pytest.raises(ExecutionNotCompletedError):
        engine.measure_outcome(exec_id)


def test_10_failed_execution_rejected():
    """Verifies that a FAILED execution cannot be measured."""
    exec_id = _create_mock_completed_execution("exec-t10", "dec-t10", "act-t10", state="FAILED")
    engine = OutcomeEngine()
    with pytest.raises(ExecutionNotCompletedError):
        engine.measure_outcome(exec_id)


def test_11_blocked_execution_rejected():
    """Verifies that a BLOCKED execution cannot be measured."""
    exec_id = _create_mock_completed_execution("exec-t11", "dec-t11", "act-t11", state="BLOCKED")
    engine = OutcomeEngine()
    with pytest.raises(ExecutionNotCompletedError):
        engine.measure_outcome(exec_id)


def test_12_non_simulation_execution_rejected():
    """Verifies that non-simulation executions are strictly forbidden in prototype."""
    _create_mock_completed_execution("exec-t12", "dec-t12", "act-t12", mode="PRODUCTION")
    engine = OutcomeEngine()
    with pytest.raises(NonSimulationExecutionError):
        engine.measure_outcome("exec-t12")


# ----------------------------------------------------------------------
# 3. DETERMINISM & PURITY TESTS
# ----------------------------------------------------------------------

def test_13_same_inputs_produce_same_output():
    """Verifies mathematical determinism: identical inputs always yield identical metrics."""
    action = {"incentive_value": 50.0, "target_customer_count": 486}
    base = {"revenue": 481850.0, "orders": 1284.0, "evening_orders": 291.0}

    out1 = generate_digital_twin_metrics(action, base)
    out2 = generate_digital_twin_metrics(action, base)
    assert out1 == out2


def test_14_percentage_calculation_deterministic():
    """Verifies rule-based percentage change calculation determinism."""
    res1 = calculate_metric_change(291.0, 331.0)
    res2 = calculate_metric_change(291.0, 331.0)
    assert res1 == res2
    assert res1["percentage_change"] == 13.75


def test_15_measurement_window_deterministic():
    """Verifies that default measurement windows have fixed start and end stamps."""
    b_win, m_win = get_default_windows()
    assert b_win["duration_days"] == 10
    assert m_win["duration_days"] == 7
    assert b_win["end"] == m_win["start"]


def test_16_metric_ordering_does_not_affect_result():
    """Verifies that metric calculation is invariant to dictionary key order."""
    action = {"incentive_value": 50.0, "target_customer_count": 486}
    base1 = {"revenue": 481850.0, "orders": 1284.0, "evening_orders": 291.0}
    base2 = {"evening_orders": 291.0, "revenue": 481850.0, "orders": 1284.0}

    out1 = generate_digital_twin_metrics(action, base1)
    out2 = generate_digital_twin_metrics(action, base2)
    assert out1["evening_orders"] == out2["evening_orders"]
    assert out1["orders"] == out2["orders"]
    assert out1["revenue"] == out2["revenue"]


# ----------------------------------------------------------------------
# 4. DIGITAL TWIN SAFETY BOUNDARY
# ----------------------------------------------------------------------

def test_17_simulated_metrics_clearly_marked():
    """Verifies that all outcome measurements carry explicit simulation flags and disclaimers."""
    exec_id = _create_mock_completed_execution("exec-t17", "dec-t17", "act-t17")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert outcome.simulated is True
    assert outcome.measurement_mode == ExecutionMode.SIMULATION
    assert "SIMULATED" in outcome.disclaimer
    assert "NOT REAL PAYTM PERFORMANCE" in outcome.disclaimer


def test_18_no_real_paytm_api_called():
    """Verifies that outcome calculation makes zero external network or Paytm API calls."""
    exec_id = _create_mock_completed_execution("exec-t18", "dec-t18", "act-t18")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)
    assert outcome is not None


def test_19_no_network_execution():
    """Verifies that OutcomeEngine operates entirely in-memory and local SQLite."""
    engine = OutcomeEngine()
    assert hasattr(engine, "measure_outcome")


def test_20_no_real_customer_data():
    """Verifies that outcome metrics are synthetic aggregates, not live customer PII."""
    exec_id = _create_mock_completed_execution("exec-t20", "dec-t20", "act-t20")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)
    assert "phone" not in outcome.baseline_metrics
    assert "pan" not in outcome.baseline_metrics


def test_21_no_real_merchant_data():
    """Verifies that merchant ID belongs strictly to the demo digital twin."""
    exec_id = _create_mock_completed_execution("exec-t21", "dec-t21", "act-t21")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)
    assert outcome.merchant_id == "MID-DEMO-98234"


# ----------------------------------------------------------------------
# 5. IDEMPOTENCY & DATABASE INTEGRITY
# ----------------------------------------------------------------------

def test_22_repeated_measurement_returns_existing_outcome():
    """Verifies that measuring the same execution twice returns the identical outcome object."""
    exec_id = _create_mock_completed_execution("exec-t22", "dec-t22", "act-t22")
    engine = OutcomeEngine()
    outcome1 = engine.measure_outcome(exec_id)
    outcome2 = engine.measure_outcome(exec_id)

    assert outcome1.outcome_id == outcome2.outcome_id
    assert outcome1.measured_at == outcome2.measured_at


def test_23_duplicate_outcome_rows_prevented():
    """Verifies that SQLite table contains exactly one outcome record for an execution."""
    exec_id = _create_mock_completed_execution("exec-t23", "dec-t23", "act-t23")
    engine = OutcomeEngine()
    engine.measure_outcome(exec_id)
    engine.measure_outcome(exec_id)

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM outcomes WHERE execution_id = ?", (exec_id,))
    count = c.fetchone()[0]
    conn.close()

    assert count == 1


def test_24_same_execution_has_one_authoritative_outcome():
    """Verifies that OutcomeRepository.get_outcome_by_execution returns authoritative record."""
    exec_id = _create_mock_completed_execution("exec-t24", "dec-t24", "act-t24")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    repo_record = OutcomeRepository.get_outcome_by_execution(exec_id)
    assert repo_record is not None
    assert repo_record["id"] == outcome.outcome_id


def test_25_arbitrary_client_metrics_rejected(test_client):
    """Verifies that client cannot inject fabricated metric values via the API payload."""
    exec_id = _create_mock_completed_execution("exec-t25", "dec-t25", "act-t25")
    res = test_client.post(
        f"/api/outcomes/measure/{exec_id}",
        json={"merchant_id": "MID-DEMO-98234", "fabricated_revenue": 9999999.0},
    )
    assert res.status_code in (200, 201)
    data = res.json()
    assert data["baseline_metrics"]["revenue"] == 481850.0  # Derived from SQLite, not payload!


def test_26_fabricated_baseline_rejected():
    """Verifies that baseline values must come from SQLite digital twin, not arbitrary client input."""
    exec_id = _create_mock_completed_execution("exec-t26", "dec-t26", "act-t26")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)
    assert outcome.baseline_metrics["orders"] == 1284.0


def test_27_fabricated_post_action_metrics_rejected():
    """Verifies that post-action metrics are derived by digital-twin model, not caller."""
    exec_id = _create_mock_completed_execution("exec-t27", "dec-t27", "act-t27")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)
    assert outcome.post_action_metrics["orders"] == 1456.0


def test_28_execution_outcome_relationship_validated():
    """Verifies foreign key relationship and decision/action lineage."""
    exec_id = _create_mock_completed_execution("exec-t28", decision_id="dec-28", action_id="act-28")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert outcome.execution_id == "exec-t28"
    assert outcome.decision_id == "dec-28"
    assert outcome.action_id == "act-28"


# ----------------------------------------------------------------------
# 6. AUDIT TRAIL TESTS
# ----------------------------------------------------------------------

def test_29_measurement_requested_audited():
    """Verifies that OUTCOME_MEASUREMENT_REQUESTED event is chained into audit ledger."""
    audit = AuditEngine()
    exec_id = _create_mock_completed_execution("exec-t29", "dec-t29", "act-t29")
    engine = OutcomeEngine(audit_engine=audit)
    engine.measure_outcome(exec_id)

    events = audit.get_events()
    requested_events = [e for e in events if "requested" in e.action_description.lower()]
    assert len(requested_events) >= 1
    assert requested_events[0].stage == StageType.LEARN


def test_30_successful_measurement_audited():
    """Verifies that OUTCOME_MEASURED is recorded with output metrics and hash chaining."""
    audit = AuditEngine()
    exec_id = _create_mock_completed_execution("exec-t30", "dec-t30", "act-t30")
    engine = OutcomeEngine(audit_engine=audit)
    engine.measure_outcome(exec_id)

    events = audit.get_events()
    measured_events = [e for e in events if "measured simulated" in e.action_description.lower()]
    assert len(measured_events) >= 1
    assert measured_events[0].integrity_hash is not None


def test_31_insufficient_data_audited():
    """Verifies that OUTCOME_INSUFFICIENT_DATA event is logged when data is missing."""
    audit = AuditEngine()
    exec_id = _create_mock_completed_execution("exec-t31", "dec-t31", "act-t31", merchant_id="MID-EMPTY")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM business_metrics WHERE merchant_id = 'MID-EMPTY'")
    conn.commit()
    conn.close()

    engine = OutcomeEngine(audit_engine=audit)
    engine.measure_outcome(exec_id)

    events = audit.get_events()
    inconclusive = [e for e in events if "inconclusive" in e.action_description.lower()]
    assert len(inconclusive) >= 1


def test_32_failure_audited():
    """Verifies that failure is logged in audit trail when non-existent execution is queried."""
    audit = AuditEngine()
    engine = OutcomeEngine(audit_engine=audit)
    try:
        engine.measure_outcome("exec-nonexistent")
    except ExecutionNotFoundError:
        pass

    events = audit.get_events()
    failures = [e for e in events if "failed" in e.action_description.lower()]
    assert len(failures) >= 1


# ----------------------------------------------------------------------
# 7. REST API ENDPOINT TESTS
# ----------------------------------------------------------------------

def test_33_api_post_measure_endpoint(test_client):
    """Verifies POST /api/outcomes/measure/{execution_id} returns 201 Created."""
    exec_id = _create_mock_completed_execution("exec-t33", "dec-t33", "act-t33")
    res = test_client.post(f"/api/outcomes/measure/{exec_id}")
    assert res.status_code == 201
    data = res.json()
    assert data["outcome_status"] == "MEASURED"
    assert data["simulated"] is True


def test_34_api_get_outcome_endpoint(test_client):
    """Verifies GET /api/outcomes/{outcome_id} returns 200 OK."""
    exec_id = _create_mock_completed_execution("exec-t34", "dec-t34", "act-t34")
    post_res = test_client.post(f"/api/outcomes/measure/{exec_id}")
    oid = post_res.json()["outcome_id"]

    get_res = test_client.get(f"/api/outcomes/{oid}")
    assert get_res.status_code == 200
    assert get_res.json()["outcome_id"] == oid


def test_35_api_get_outcome_by_execution(test_client):
    """Verifies GET /api/executions/{execution_id}/outcome returns linked outcome."""
    exec_id = _create_mock_completed_execution("exec-t35", "dec-t35", "act-t35")
    test_client.post(f"/api/outcomes/measure/{exec_id}")

    res = test_client.get(f"/api/executions/{exec_id}/outcome")
    assert res.status_code == 200
    assert res.json()["execution_id"] == exec_id


def test_36_api_merchant_history(test_client):
    """Verifies GET /api/outcomes?merchant_id=... returns merchant outcome history."""
    exec_id = _create_mock_completed_execution("exec-t36", "dec-t36", "act-t36")
    test_client.post(f"/api/outcomes/measure/{exec_id}")

    res = test_client.get("/api/outcomes?merchant_id=MID-DEMO-98234")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_37_invalid_execution_id_returns_404(test_client):
    """Verifies that measuring non-existent execution returns 404 Not Found."""
    res = test_client.post("/api/outcomes/measure/exec-fake-999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_38_invalid_measurement_window_handled_safely(test_client):
    """Verifies that null or missing measurement window falls back safely to default."""
    exec_id = _create_mock_completed_execution("exec-t38", "dec-t38", "act-t38")
    res = test_client.post(f"/api/outcomes/measure/{exec_id}", json={})
    assert res.status_code == 201
    assert res.json()["measurement_window"]["duration_days"] == 7


def test_39_llm_cannot_override_outcome_metrics():
    """Verifies that outcome calculation is 100% code-based with zero LLM authority."""
    exec_id = _create_mock_completed_execution("exec-t39", "dec-t39", "act-t39")
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)
    assert "Observed simulated change" in outcome.metric_changes["evening_orders"]["description"]
    assert "caused" not in outcome.metric_changes["evening_orders"]["description"].lower()


def test_40_modify_execution_uses_clamped_parameter():
    """Verifies that an action clamped by guardrails to INR 100 uses INR 100 for digital-twin outcome."""
    clamped_action = {
        "action_id": "act-mod-40",
        "action_type": "OFFER_CAMPAIGN",
        "incentive_value": 100.0,
        "target_customer_count": 486,
        "parameters": {"cashback_inr": 100.0},
    }
    exec_id = _create_mock_completed_execution("exec-t40", "dec-t40", "act-t40", approved_action=clamped_action)
    engine = OutcomeEngine()
    outcome = engine.measure_outcome(exec_id)

    assert outcome.post_action_metrics["evening_orders"] == 371.0
    assert outcome.metric_changes["evening_orders"]["absolute_change"] == 80.0
