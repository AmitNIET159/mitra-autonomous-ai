"""Comprehensive Automated Pytest Suite for MITRA Phase 10: ROI & Business Impact Analysis.

Covers:
- Preconditions (missing outcome, unmeasured outcome, measured outcome, insufficient data)
- Deterministic formulas (incremental revenue, orders, evening orders, campaign cost, ROI, ROI %)
- Efficiency indicators (cost per incremental order, revenue per campaign rupee)
- Safety & zero division (zero cost, negative cost, zero incremental orders, no NaN/Infinity)
- Anti-fabrication (gross profit impact is None, no fabricated COGS)
- Impact classification (POSITIVE, NEUTRAL, NEGATIVE, INSUFFICIENT_DATA)
- Single authoritative DB row & idempotency
- CRITICAL MODIFY INVARIANT: Clamped approved value (e.g. INR 100) strictly used, proposal (INR 150) ignored
- Sandbox & prototype indicators (simulated=True, SIMULATION mode, disclaimer)
- Anti-injection (client payload cannot manipulate metrics)
- Audit ledger (SHA-256 hash chaining)
- REST API endpoints (POST analyze, GET by ID, GET by outcome, GET merchant list)
"""
import json
import pytest
from starlette.testclient import TestClient

from app.database.connection import get_connection, init_db
from app.database.repository import (
    ActionRepository,
    BusinessImpactRepository,
    DecisionRepository,
    ExecutionRepository,
    OutcomeRepository,
)
from app.engines.audit_engine.engine import AuditEngine
from app.engines.business_impact.engine import BusinessImpactEngine
from app.engines.business_impact.rules import (
    calculate_business_impact_metrics,
    calculate_campaign_cost,
    classify_impact,
    verify_outcome_preconditions,
    BusinessImpactError,
    InsufficientImpactDataError,
    OutcomeNotFoundError,
    OutcomeNotMeasuredError,
)
from app.main import app
from app.models.contracts import BusinessImpact
from app.models.enums import (
    DecisionState,
    ExecutionMode,
    ExecutionState,
    ImpactClassification,
    ImpactStatus,
    MeasurementMode,
    OutcomeStatus,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_database():
    """Ensures database schema and clean test environment."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM business_impacts;")
        cursor.execute("DELETE FROM outcomes;")
        cursor.execute("DELETE FROM executions;")
        conn.commit()
    finally:
        conn.close()



def _create_test_execution_and_outcome(
    execution_id: str = "exec-test-1",
    outcome_id: str = "out-test-1",
    outcome_status: str = "MEASURED",
    incentive_value: float = 10.0,
    target_count: int = 486,
    baseline_rev: float = 481850.0,
    post_rev: float = 500000.0,
    baseline_orders: float = 1284.0,
    post_orders: float = 1456.0,
    baseline_evening: float = 291.0,
    post_evening: float = 331.0,
):
    """Helper to create matching execution and outcome records."""
    approved_action = {
        "action_type": "EVENING_REENGAGEMENT_CAMPAIGN",
        "incentive_value": incentive_value,
        "target_customer_count": target_count,
        "parameters": {
            "cashback_inr": incentive_value,
            "target_customer_count": target_count,
        },
    }
    ActionRepository.create_or_update_action_proposal(
        signal_id=f"sig-{execution_id}",
        investigation_id=f"inv-{execution_id}",
        merchant_id="MID-DEMO-98234",
        action_type="OFFER_CAMPAIGN",
        action_id=f"act-{execution_id}",
        parameters={"cashback_inr": incentive_value, "target_customer_count": target_count},
        incentive_value=incentive_value,
        target_customer_count=target_count,
    )
    DecisionRepository.create_or_update_decision(
        decision_id=f"dec-{execution_id}",
        action_id=f"act-{execution_id}",
        evaluation_id=f"grd-{execution_id}",
        merchant_id="MID-DEMO-98234",
        decision_state="PASS",
        reason="Approved",
        triggered_rules=[],
        modifications={},
        approval_required=True,
        approval_status="APPROVED",
        is_execution_eligible=True,
        approved_action=approved_action,
    )

    ExecutionRepository.create_execution(
        decision_id=f"dec-{execution_id}",
        execution_id=execution_id,
        action_id=f"act-{execution_id}",
        merchant_id="MID-DEMO-98234",
        execution_state="COMPLETED",
        execution_mode="SIMULATION",
        approved_action=approved_action,
        result={"simulated_success": True},
    )

    base_metrics = {
        "revenue": baseline_rev,
        "gmv": baseline_rev,
        "orders": baseline_orders,
        "evening_orders": baseline_evening,
    }
    post_metrics = {
        "revenue": post_rev,
        "gmv": post_rev,
        "orders": post_orders,
        "evening_orders": post_evening,
    }
    metric_changes = {
        "revenue": {"absolute_change": round(post_rev - baseline_rev, 2)},
        "orders": {"absolute_change": round(post_orders - baseline_orders, 2)},
        "evening_orders": {"absolute_change": round(post_evening - baseline_evening, 2)},
    }

    return OutcomeRepository.create_outcome(
        execution_id=execution_id,
        outcome_id=outcome_id,
        decision_id=f"dec-{execution_id}",
        action_id=f"act-{execution_id}",
        merchant_id="MID-DEMO-98234",
        baseline_metrics=base_metrics if outcome_status != "INSUFFICIENT_DATA" else {},
        post_action_metrics=post_metrics if outcome_status != "INSUFFICIENT_DATA" else {},
        metric_changes=metric_changes if outcome_status != "INSUFFICIENT_DATA" else {},
        outcome_status=outcome_status,
        measurement_mode="SIMULATION",
        simulated=True,
    )


# ==============================================================================
# 1. PRECONDITION TESTS
# ==============================================================================

def test_precondition_missing_outcome():
    """Verify missing outcome raises OutcomeNotFoundError."""
    with pytest.raises(OutcomeNotFoundError):
        verify_outcome_preconditions(None)


def test_precondition_pending_outcome_raises_conflict():
    """Verify unmeasured PENDING outcome raises OutcomeNotMeasuredError."""
    outcome_dict = {"id": "out-p", "outcome_status": "PENDING"}
    with pytest.raises(OutcomeNotMeasuredError) as exc_info:
        verify_outcome_preconditions(outcome_dict)
    assert "outcome measurement is required first" in str(exc_info.value)


def test_precondition_failed_outcome_raises_conflict():
    """Verify unmeasured FAILED outcome raises OutcomeNotMeasuredError."""
    outcome_dict = {"id": "out-f", "outcome_status": "FAILED"}
    with pytest.raises(OutcomeNotMeasuredError):
        verify_outcome_preconditions(outcome_dict)


def test_precondition_measured_outcome_passes():
    """Verify MEASURED outcome passes preconditions without error."""
    outcome_dict = {"id": "out-m", "outcome_status": "MEASURED"}
    verify_outcome_preconditions(outcome_dict)  # Should not raise


def test_precondition_insufficient_data_outcome_passes():
    """Verify INSUFFICIENT_DATA outcome passes preconditions without error."""
    outcome_dict = {"id": "out-i", "outcome_status": "INSUFFICIENT_DATA"}
    verify_outcome_preconditions(outcome_dict)  # Should not raise


# ==============================================================================
# 2. DETERMINISTIC CALCULATION TESTS
# ==============================================================================

def test_calculate_campaign_cost_from_incentive_and_count():
    """Campaign cost should equal incentive * target_customer_count."""
    action = {
        "incentive_value": 50.0,
        "target_customer_count": 486,
    }
    cost = calculate_campaign_cost(action)
    assert cost == 24300.0


def test_calculate_campaign_cost_from_parameters():
    """Campaign cost should extract from parameters dictionary."""
    action = {
        "parameters": {
            "cashback_inr": 10.0,
            "target_customer_count": 486,
        }
    }
    cost = calculate_campaign_cost(action)
    assert cost == 4860.0


def test_calculate_campaign_cost_from_estimated_cost_fallback():
    """Campaign cost falls back to estimated_cost_inr if explicit values missing."""
    action = {"estimated_cost_inr": 4860.0}
    cost = calculate_campaign_cost(action)
    assert cost == 4860.0


def test_calculate_campaign_cost_empty_action_is_zero():
    """Empty action yields 0 cost safely."""
    assert calculate_campaign_cost({}) == 0.0


def test_calculate_incremental_revenue_and_orders():
    """Verify incremental revenue, incremental orders, and evening orders diff."""
    res = calculate_business_impact_metrics(
        baseline_revenue=481850.0,
        post_action_revenue=500000.0,
        baseline_orders=1284.0,
        post_action_orders=1456.0,
        baseline_evening_orders=291.0,
        post_action_evening_orders=331.0,
        campaign_cost=4860.0,
    )
    assert res["incremental_revenue"] == 18150.0
    assert res["orders_change"] == 172.0
    assert res["incremental_orders"] == 172.0
    assert res["evening_orders_change"] == 40.0


def test_calculate_roi_and_percentage():
    """Verify ROI = (inc_rev - cost) / cost and roi_percentage = roi * 100."""
    # inc_rev = 18150, cost = 4860 -> net = 13290 -> roi = 13290 / 4860 ≈ 2.7346 -> 273.46%
    res = calculate_business_impact_metrics(
        baseline_revenue=481850.0,
        post_action_revenue=500000.0,
        baseline_orders=1000.0,
        post_action_orders=1100.0,
        baseline_evening_orders=200.0,
        post_action_evening_orders=250.0,
        campaign_cost=4860.0,
    )
    assert res["roi"] == 2.7346
    assert res["roi_percentage"] == 273.46


def test_calculate_cost_per_incremental_order():
    """cost_per_incremental_order = campaign_cost / incremental_orders."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=110000.0,
        baseline_orders=100.0,
        post_action_orders=200.0,  # inc_orders = 100
        baseline_evening_orders=50.0,
        post_action_evening_orders=80.0,
        campaign_cost=2000.0,
    )
    assert res["cost_per_incremental_order"] == 20.0  # 2000 / 100


def test_calculate_revenue_per_campaign_rupee():
    """revenue_per_campaign_rupee = incremental_revenue / campaign_cost."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=115000.0,  # inc_rev = 15000
        baseline_orders=100.0,
        post_action_orders=150.0,
        baseline_evening_orders=50.0,
        post_action_evening_orders=80.0,
        campaign_cost=5000.0,
    )
    assert res["revenue_per_campaign_rupee"] == 3.0  # 15000 / 5000


# ==============================================================================
# 3. SAFETY & ZERO DIVISION TESTS
# ==============================================================================

def test_zero_campaign_cost_does_not_divide_by_zero():
    """When campaign_cost == 0, ROI and efficiency metrics are None safely."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=120000.0,
        baseline_orders=100.0,
        post_action_orders=120.0,
        baseline_evening_orders=20.0,
        post_action_evening_orders=30.0,
        campaign_cost=0.0,
    )
    assert res["roi"] is None
    assert res["roi_percentage"] is None
    assert res["revenue_per_campaign_rupee"] is None
    assert res["cost_per_incremental_order"] is None


def test_negative_campaign_cost_handled_safely():
    """When campaign_cost < 0, ROI and efficiency metrics are None safely."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=120000.0,
        baseline_orders=100.0,
        post_action_orders=120.0,
        baseline_evening_orders=20.0,
        post_action_evening_orders=30.0,
        campaign_cost=-500.0,
    )
    assert res["roi"] is None
    assert res["roi_percentage"] is None


def test_zero_incremental_orders_does_not_divide_by_zero():
    """When incremental_orders == 0, cost_per_incremental_order is None."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=105000.0,
        baseline_orders=100.0,
        post_action_orders=100.0,  # inc_orders = 0
        baseline_evening_orders=20.0,
        post_action_evening_orders=20.0,
        campaign_cost=1000.0,
    )
    assert res["cost_per_incremental_order"] is None


def test_negative_order_change_clamps_incremental_orders_to_zero():
    """When orders drop, incremental_orders is clamped to 0, not negative."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=90000.0,
        baseline_orders=100.0,
        post_action_orders=80.0,  # drop by 20
        baseline_evening_orders=20.0,
        post_action_evening_orders=15.0,
        campaign_cost=1000.0,
    )
    assert res["orders_change"] == -20.0
    assert res["incremental_orders"] == 0.0
    assert res["cost_per_incremental_order"] is None


def test_zero_cogs_fabrication():
    """Gross profit impact remains None unless explicit COGS inputs are known."""
    res = calculate_business_impact_metrics(
        baseline_revenue=100000.0,
        post_action_revenue=110000.0,
        baseline_orders=100.0,
        post_action_orders=120.0,
        baseline_evening_orders=20.0,
        post_action_evening_orders=30.0,
        campaign_cost=1000.0,
    )
    assert res["gross_profit_impact"] is None


# ==============================================================================
# 4. IMPACT CLASSIFICATION TESTS
# ==============================================================================

def test_classify_impact_positive():
    """Positive ROI is classified as POSITIVE."""
    assert classify_impact(roi=0.25, status="CALCULATED") == ImpactClassification.POSITIVE


def test_classify_impact_neutral():
    """Zero ROI is classified as NEUTRAL."""
    assert classify_impact(roi=0.0, status="CALCULATED") == ImpactClassification.NEUTRAL


def test_classify_impact_negative():
    """Negative ROI is classified as NEGATIVE."""
    assert classify_impact(roi=-0.15, status="CALCULATED") == ImpactClassification.NEGATIVE


def test_classify_impact_insufficient_data():
    """None ROI or INSUFFICIENT_DATA status is classified as INSUFFICIENT_DATA."""
    assert classify_impact(roi=None, status="CALCULATED") == ImpactClassification.INSUFFICIENT_DATA
    assert classify_impact(roi=0.5, status="INSUFFICIENT_DATA") == ImpactClassification.INSUFFICIENT_DATA


# ==============================================================================
# 5. ENGINE & IDEMPOTENCY TESTS
# ==============================================================================

def test_engine_analyze_impact_success():
    """Engine calculates and persists business impact correctly."""
    _create_test_execution_and_outcome("exec-eng-1", "out-eng-1")
    engine = BusinessImpactEngine()
    impact = engine.analyze_impact("out-eng-1")

    assert impact.impact_id.startswith("imp-")
    assert impact.outcome_id == "out-eng-1"
    assert impact.impact_status == ImpactStatus.CALCULATED
    assert impact.impact_classification == ImpactClassification.POSITIVE
    assert impact.incremental_revenue == 18150.0
    assert impact.incremental_orders == 172.0
    assert impact.evening_orders_change == 40.0
    assert impact.simulated is True
    assert impact.measurement_mode == MeasurementMode.SIMULATION


def test_engine_idempotency_returns_same_record():
    """Multiple analyze calls on same outcome return identical record with 1 DB row."""
    _create_test_execution_and_outcome("exec-idem-1", "out-idem-1")
    engine = BusinessImpactEngine()
    impact1 = engine.analyze_impact("out-idem-1")
    impact2 = engine.analyze_impact("out-idem-1")

    assert impact1.impact_id == impact2.impact_id
    assert impact1.roi == impact2.roi

    # Verify SQLite row count
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM business_impacts WHERE outcome_id = 'out-idem-1'")
        assert cursor.fetchone()["cnt"] == 1
    finally:
        conn.close()


def test_engine_handles_insufficient_data_outcome():
    """Engine creates INSUFFICIENT_DATA impact record without fabricating numbers."""
    _create_test_execution_and_outcome(
        "exec-insuf-1", "out-insuf-1", outcome_status="INSUFFICIENT_DATA"
    )
    engine = BusinessImpactEngine()
    impact = engine.analyze_impact("out-insuf-1")

    assert impact.impact_status == ImpactStatus.INSUFFICIENT_DATA
    assert impact.impact_classification == ImpactClassification.INSUFFICIENT_DATA
    assert impact.roi is None
    assert impact.roi_percentage is None
    assert impact.incremental_revenue == 0.0


def test_engine_missing_outcome_raises_404_error():
    """Engine raises OutcomeNotFoundError if outcome ID is invalid."""
    engine = BusinessImpactEngine()
    with pytest.raises(OutcomeNotFoundError):
        engine.analyze_impact("out-nonexistent-999")


def test_engine_unmeasured_outcome_raises_409_error():
    """Engine raises OutcomeNotMeasuredError if outcome status is PENDING."""
    _create_test_execution_and_outcome(
        "exec-pending-1", "out-pending-1", outcome_status="PENDING"
    )
    engine = BusinessImpactEngine()
    with pytest.raises(OutcomeNotMeasuredError):
        engine.analyze_impact("out-pending-1")


# ==============================================================================
# 6. CRITICAL MODIFY INVARIANT TEST
# ==============================================================================

def test_modify_clamped_parameter_used_for_cost_calculation():
    """CRITICAL TEST: In MODIFY flow, campaign cost MUST consume approved clamped value (INR 100), NEVER proposed (INR 150)."""
    # 1. Simulate proposal where original proposal had cashback = 150
    # 2. Guardrails clamped cashback to 100
    # 3. Execution recorded approved_action with cashback = 100
    target_count = 50
    approved_action = {
        "action_type": "OFFER_CAMPAIGN",
        "incentive_value": 100.0,  # Clamped by Guardrails!
        "target_customer_count": target_count,
        "parameters": {
            "cashback_inr": 100.0,
            "target_customer_count": target_count,
            "original_proposed_cashback": 150.0,  # Ignored!
        },
    }
    ActionRepository.create_or_update_action_proposal(
        signal_id="sig-modify-test",
        investigation_id="inv-modify-test",
        merchant_id="MID-DEMO-98234",
        action_type="OFFER_CAMPAIGN",
        action_id="act-modify-test",
        parameters={"cashback_inr": 150.0, "target_customer_count": target_count},
        incentive_value=150.0,
        target_customer_count=target_count,
    )
    DecisionRepository.create_or_update_decision(
        decision_id="dec-modify-test",
        action_id="act-modify-test",
        evaluation_id="grd-modify-test",
        merchant_id="MID-DEMO-98234",
        decision_state="MODIFY",
        reason="Clamped",
        triggered_rules=["MAX_DISCOUNT_RULE"],
        modifications={"cashback_inr": 100.0},
        approval_required=True,
        approval_status="APPROVED",
        is_execution_eligible=True,
        approved_action=approved_action,
    )

    ExecutionRepository.create_execution(
        decision_id="dec-modify-test",
        execution_id="exec-modify-test",
        action_id="act-modify-test",
        merchant_id="MID-DEMO-98234",
        execution_state="COMPLETED",
        execution_mode="SIMULATION",
        approved_action=approved_action,
        result={"simulated_success": True},
    )
    OutcomeRepository.create_outcome(
        execution_id="exec-modify-test",
        outcome_id="out-modify-test",
        decision_id="dec-modify-test",
        action_id="act-modify-test",
        merchant_id="MID-DEMO-98234",
        baseline_metrics={"revenue": 100000.0, "orders": 500.0, "evening_orders": 100.0},
        post_action_metrics={"revenue": 120000.0, "orders": 600.0, "evening_orders": 150.0},
        outcome_status="MEASURED",
        measurement_mode="SIMULATION",
        simulated=True,
    )

    engine = BusinessImpactEngine()
    impact = engine.analyze_impact("out-modify-test")

    # Expected cost: 100.0 * 50 = 5000.0
    # Unsafe cost would have been: 150.0 * 50 = 7500.0
    assert impact.campaign_cost == 5000.0, "Cost must strictly use clamped INR 100!"
    assert impact.campaign_cost != 7500.0, "Cost must NEVER use unapproved INR 150!"

    # Incremental revenue: 120000 - 100000 = 20000
    # Expected ROI: (20000 - 5000) / 5000 = 3.0 -> 300%
    assert impact.roi == 3.0
    assert impact.roi_percentage == 300.0


# ==============================================================================
# 7. ANTI-INJECTION & SANDBOX TESTS
# ==============================================================================

def test_anti_injection_server_ignores_client_supplied_metrics():
    """Client cannot inject fake revenue or ROI via request body."""
    _create_test_execution_and_outcome("exec-sec-1", "out-sec-1")

    # Attempt to inject custom fake metrics
    malicious_payload = {
        "merchant_id": "MID-DEMO-98234",
        "revenue": 999999999.0,
        "roi": 999999.0,
        "campaign_cost": 0.01,
    }
    response = client.post("/api/business-impact/analyze/out-sec-1", json=malicious_payload)
    assert response.status_code == 201
    data = response.json()

    # The server must have calculated authoritative values from DB, not client payload
    assert data["incremental_revenue"] == 18150.0
    assert data["campaign_cost"] == 4860.0
    assert data["campaign_cost"] != 0.01
    assert data["roi"] != 999999.0


def test_sandbox_and_prototype_indicators_present():
    """Verify all results carry SIMULATION and prototype indicators."""
    _create_test_execution_and_outcome("exec-sand-1", "out-sand-1")
    res = client.post("/api/business-impact/analyze/out-sand-1")
    assert res.status_code == 201
    data = res.json()
    assert data["simulated"] is True
    assert data["measurement_mode"] == "SIMULATION"
    assert "SIMULATED - PROTOTYPE" in data["disclaimer"]


# ==============================================================================
# 8. AUDIT TRAIL TESTS
# ==============================================================================

def test_audit_events_recorded_with_hash_chain():
    """Audit events are chained and hash-verified during analysis."""
    _create_test_execution_and_outcome("exec-aud-1", "out-aud-1")
    audit_eng = AuditEngine()
    engine = BusinessImpactEngine(audit_engine=audit_eng)
    engine.analyze_impact("out-aud-1")

    events = audit_eng.get_events(limit=10)
    event_actions = [e.action_description for e in events]
    assert any("Business impact analysis requested" in a for a in event_actions)
    assert any("Calculated deterministic business impact" in a for a in event_actions)

    for ev in events:
        assert ev.integrity_hash is not None
        assert len(ev.integrity_hash) == 64  # SHA-256 hex string


# ==============================================================================
# 9. REST API ENDPOINTS TESTS
# ==============================================================================

def test_api_post_analyze_success():
    """POST /api/business-impact/analyze/{outcome_id} returns 201 for new analysis."""
    _create_test_execution_and_outcome("exec-api-1", "out-api-1")
    response = client.post("/api/business-impact/analyze/out-api-1")
    assert response.status_code == 201
    data = response.json()
    assert data["outcome_id"] == "out-api-1"
    assert data["impact_status"] == "CALCULATED"


def test_api_post_analyze_idempotent_returns_200():
    """POST /api/business-impact/analyze/{outcome_id} returns 200 for subsequent calls."""
    _create_test_execution_and_outcome("exec-api-2", "out-api-2")
    res1 = client.post("/api/business-impact/analyze/out-api-2")
    assert res1.status_code == 201

    res2 = client.post("/api/business-impact/analyze/out-api-2")
    assert res2.status_code == 200
    assert res1.json()["impact_id"] == res2.json()["impact_id"]


def test_api_post_analyze_missing_outcome_returns_404():
    """POST /api/business-impact/analyze/unknown returns 404 Not Found."""
    response = client.post("/api/business-impact/analyze/out-nonexistent-404")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_api_post_analyze_unmeasured_outcome_returns_409():
    """POST /api/business-impact/analyze/unmeasured returns 409 Conflict."""
    _create_test_execution_and_outcome("exec-unmeas", "out-unmeas", outcome_status="PENDING")
    response = client.post("/api/business-impact/analyze/out-unmeas")
    assert response.status_code == 409
    assert "outcome measurement is required first" in response.json()["detail"].lower()


def test_api_get_business_impact_by_id():
    """GET /api/business-impact/{impact_id} returns the record."""
    _create_test_execution_and_outcome("exec-get-1", "out-get-1")
    post_res = client.post("/api/business-impact/analyze/out-get-1")
    impact_id = post_res.json()["impact_id"]

    get_res = client.get(f"/api/business-impact/{impact_id}")
    assert get_res.status_code == 200
    assert get_res.json()["impact_id"] == impact_id


def test_api_get_business_impact_by_id_404():
    """GET /api/business-impact/unknown returns 404."""
    get_res = client.get("/api/business-impact/imp-nonexistent-404")
    assert get_res.status_code == 404


def test_api_get_business_impact_for_outcome():
    """GET /api/outcomes/{outcome_id}/business-impact returns the record."""
    _create_test_execution_and_outcome("exec-out-get", "out-out-get")
    client.post("/api/business-impact/analyze/out-out-get")

    get_res = client.get("/api/outcomes/out-out-get/business-impact")
    assert get_res.status_code == 200
    assert get_res.json()["outcome_id"] == "out-out-get"


def test_api_get_business_impact_for_outcome_404():
    """GET /api/outcomes/{outcome_id}/business-impact returns 404 if not analyzed."""
    _create_test_execution_and_outcome("exec-notyet", "out-notyet")
    get_res = client.get("/api/outcomes/out-notyet/business-impact")
    assert get_res.status_code == 404


def test_api_list_merchant_business_impacts():
    """GET /api/business-impact?merchant_id=... returns history."""
    _create_test_execution_and_outcome("exec-hist-1", "out-hist-1")
    client.post("/api/business-impact/analyze/out-hist-1")

    res = client.get("/api/business-impact?merchant_id=MID-DEMO-98234")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["outcome_id"] == "out-hist-1"
