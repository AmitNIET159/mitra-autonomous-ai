"""Tests for MITRA Phase 11: Audit & Explainability Engine.

SAFETY, PROVENANCE & CRYPTOGRAPHIC VERIFICATION:
- Verifies SHA-256 hash chaining and tamper detection.
- Verifies facts vs hypotheses strict separation and provenance tracking.
- Verifies non-causal framing and zero secret leakage.
- Verifies read-only API behavior and entity graph resolution.
- Verifies MODIFY clamped parameter invariant and honest negative ROI representation.
"""
import json
import pytest
from starlette.testclient import TestClient

from app.database.connection import get_connection, init_db
from app.database.repository import (
    ActionRepository,
    AuditRepository,
    BusinessImpactRepository,
    DecisionRepository,
    ExecutionRepository,
    GuardrailRepository,
    InvestigationRepository,
    OutcomeRepository,
    SignalRepository,
)
from app.engines.audit_engine.engine import AuditEngine, compute_event_hash, sanitize_payload
from app.engines.explainability_engine.engine import ExplainabilityEngine
from app.engines.explainability_engine.rules import (
    build_action_explanation,
    build_business_impact_explanation,
    build_decision_explanation,
    build_execution_explanation,
    build_guardrail_explanation,
    build_outcome_explanation,
    build_signal_explanation,
    extract_facts_and_hypotheses,
    resolve_workflow_entities,
)
from app.main import app
from app.models.contracts import (
    AuditEvent,
    ExplainabilitySummary,
    FactItem,
    HypothesisItem,
    WorkflowAuditVerification,
)
from app.models.enums import (
    ActionType,
    ApprovalStatus,
    DecisionState,
    ExecutionMode,
    ExecutionState,
    ImpactClassification,
    ImpactStatus,
    OutcomeStatus,
    SignalSeverity,
    StageType,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM audit_events WHERE id != 'AUDIT-INIT-001'")
        cur.execute("DELETE FROM autonomy_evaluations")
        cur.execute("DELETE FROM business_impacts")
        cur.execute("DELETE FROM outcomes")
        cur.execute("DELETE FROM executions")
        cur.execute("DELETE FROM decisions")
        cur.execute("DELETE FROM guardrail_evaluations")
        cur.execute("DELETE FROM actions")
        cur.execute("DELETE FROM investigations")
        cur.execute("DELETE FROM signals")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def client():
    return TestClient(app)


# ==============================================================================
# 1. AUDIT ENGINE & HASH CHAINING TESTS (Tests 1 - 10)
# ==============================================================================

def test_audit_record_event_persists_to_sqlite():
    engine = AuditEngine()
    event = engine.record_event(
        stage=StageType.DETECT,
        actor="SignalEngine",
        action_description="Detected evening anomaly",
        input_payload={"metric": "evening_orders"},
        output_payload={"signal_id": "sig-test-01"},
        correlation_id="wf-test-01",
    )
    assert event.event_id is not None
    assert event.integrity_hash is not None
    assert event.correlation_id == "wf-test-01"

    row = AuditRepository.get_event(event.event_id)
    assert row is not None
    assert row["actor"] == "SignalEngine"
    assert row["stage"] == "DETECT"


def test_audit_hash_chaining_links_previous_hash():
    engine = AuditEngine()
    e1 = engine.record_event(
        stage=StageType.DETECT,
        actor="Actor1",
        action_description="First event",
        input_payload={"step": 1},
        output_payload={"status": "OK"},
        correlation_id="wf-chain-01",
    )
    e2 = engine.record_event(
        stage=StageType.INVESTIGATE,
        actor="Actor2",
        action_description="Second event",
        input_payload={"step": 2},
        output_payload={"status": "OK"},
        correlation_id="wf-chain-01",
    )
    assert e2.previous_hash == e1.integrity_hash
    assert e2.integrity_hash != e1.integrity_hash


def test_audit_chain_verification_succeeds_on_valid_chain():
    engine = AuditEngine()
    for i in range(5):
        engine.record_event(
            stage=StageType.GUARD,
            actor="Planner",
            action_description=f"Action step {i}",
            input_payload={"step": i},
            output_payload={"res": i * 10},
            correlation_id="wf-valid-01",
        )
    verification = engine.verify_audit_chain(correlation_id="wf-valid-01")
    assert verification.valid is True
    assert verification.event_count == 5
    assert verification.verification_mode == "SHA-256"
    assert verification.error is None


def test_audit_tamper_detection_on_modified_payload():
    engine = AuditEngine()
    e1 = engine.record_event(
        stage=StageType.ACT,
        actor="ExecutionEngine",
        action_description="Simulated execution",
        input_payload={"amount": 100},
        output_payload={"status": "COMPLETED"},
        correlation_id="wf-tamper-01",
    )
    # Tamper payload directly in SQLite
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE audit_events SET input_payload = ? WHERE id = ?",
            (json.dumps({"amount": 999999}), e1.event_id),
        )
        conn.commit()
    finally:
        conn.close()

    verification = engine.verify_audit_chain(correlation_id="wf-tamper-01")
    assert verification.valid is False
    assert "Tampered hash detected" in verification.error


def test_audit_tamper_detection_on_broken_chain_link():
    engine = AuditEngine()
    e1 = engine.record_event(
        stage=StageType.DETECT, actor="A", action_description="E1",
        input_payload={}, output_payload={}, correlation_id="wf-broken-01",
    )
    e2 = engine.record_event(
        stage=StageType.GUARD, actor="B", action_description="E2",
        input_payload={}, output_payload={}, correlation_id="wf-broken-01",
    )
    # Corrupt previous_hash of e2 in SQLite
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE audit_events SET previous_hash = 'INVALID_HASH' WHERE id = ?", (e2.event_id,))
        conn.commit()
    finally:
        conn.close()

    verification = engine.verify_audit_chain(correlation_id="wf-broken-01")
    assert verification.valid is False
    assert "Broken chain link" in verification.error


def test_audit_verify_empty_chain_returns_valid():
    engine = AuditEngine()
    verification = engine.verify_audit_chain(correlation_id="wf-nonexistent-999")
    assert verification.valid is True
    assert verification.event_count == 0
    assert verification.error is None


def test_sanitize_payload_masks_sensitive_keys():
    raw_payload = {
        "user": "merchant_admin",
        "password": "secret_password_123",
        "api_key": "paytm_live_key_xyz",
        "nested": {
            "auth_token": "jwt.header.payload.sig",
            "safe_metric": 42.5,
        },
    }
    clean = sanitize_payload(raw_payload)
    assert clean["user"] == "merchant_admin"
    assert clean["password"] == "[REDACTED]"
    assert clean["api_key"] == "[REDACTED]"
    assert clean["nested"]["auth_token"] == "[REDACTED]"
    assert clean["nested"]["safe_metric"] == 42.5


def test_audit_auto_derives_correlation_id_from_signal_id():
    engine = AuditEngine()
    event = engine.record_event(
        stage=StageType.DETECT,
        actor="SignalEngine",
        action_description="Anomaly found",
        input_payload={"signal_id": "sig-abc12345"},
        output_payload={},
    )
    assert event.correlation_id == "wf-abc12345"


def test_audit_query_events_by_correlation_id():
    engine = AuditEngine()
    engine.record_event(StageType.DETECT, "A", "Act A", {}, {}, correlation_id="wf-target")
    engine.record_event(StageType.GUARD, "B", "Act B", {}, {}, correlation_id="wf-target")
    engine.record_event(StageType.DETECT, "C", "Act C", {}, {}, correlation_id="wf-other")

    events = AuditRepository.get_events_by_correlation_id("wf-target")
    assert len(events) == 2
    assert [e["action_description"] for e in events] == ["Act A", "Act B"]


def test_compute_event_hash_deterministic():
    h1 = compute_event_hash("GENESIS", StageType.GUARD, "Actor", "Desc", {"k": 1}, {"res": "PASS"})
    h2 = compute_event_hash("GENESIS", StageType.GUARD, "Actor", "Desc", {"k": 1}, {"res": "PASS"})
    assert h1 == h2
    assert len(h1) == 64


# ==============================================================================
# 2. FACTS VS HYPOTHESES & PROVENANCE TESTS (Tests 11 - 18)
# ==============================================================================

def test_extract_facts_from_signal():
    signal_row = {
        "id": "sig-01",
        "metric_name": "evening_orders",
        "baseline_value": 410.0,
        "observed_value": 291.0,
        "change_percentage": -29.02,
        "detected_at": "2026-09-18T12:00:00Z",
    }
    facts, hypotheses, provenance = extract_facts_and_hypotheses(None, signal_row)
    assert len(facts) == 1
    assert facts[0].id == "F1"
    assert facts[0].fact_type == "METRIC_ANOMALY"
    assert "29.02%" in facts[0].statement
    assert facts[0].source == "business_metrics"
    assert len(provenance) == 1
    assert len(hypotheses) == 0


def test_extract_facts_and_hypotheses_from_investigation():
    investigation_row = {
        "id": "inv-01",
        "evidence_bundle": json.dumps({
            "evidence_items": [
                {
                    "description": "Repeat conversion dropped to 14.8%",
                    "metric_name": "repeat_conversion",
                    "baseline_value": 0.182,
                    "observed_value": 0.148,
                    "source": "pos_transactions",
                },
                {
                    "description": "Previous campaign expired 3 days ago",
                    "metric_name": "campaign_active",
                    "source": "campaigns",
                },
            ]
        }),
        "hypotheses": json.dumps([
            {
                "hypothesis": "Promotional gap reduced evening visit likelihood.",
                "confidence": 0.85,
            }
        ]),
    }
    facts, hypotheses, provenance = extract_facts_and_hypotheses(investigation_row, None)
    assert len(facts) == 2
    assert facts[0].id == "F2"
    assert facts[1].id == "F3"
    assert len(hypotheses) == 1
    assert hypotheses[0].id == "H1"
    assert hypotheses[0].is_causal_claim is False
    assert "Causality is not established" in hypotheses[0].caveat


def test_provenance_contains_valid_source_tables():
    signal_row = {"id": "sig-01", "metric_name": "evening_orders", "baseline_value": 100, "observed_value": 50, "change_percentage": -50.0}
    inv_row = {
        "id": "inv-01",
        "evidence_bundle": json.dumps({"evidence_items": [{"description": "test", "metric_name": "m1", "source": "daily_metrics"}]}),
        "hypotheses": "[]",
    }
    facts, hypotheses, provenance = extract_facts_and_hypotheses(inv_row, signal_row)
    assert any(p["source_table"] == "daily_metrics" for p in provenance)


def test_hypothesis_never_asserts_causality():
    h = HypothesisItem(id="H1", hypothesis="Weather reduced foot traffic")
    assert h.is_causal_claim is False
    assert "AI interpretation" in h.caveat


def test_fact_item_serialization():
    fact = FactItem(
        id="F1",
        fact_type="EVIDENCE",
        statement="Orders dropped",
        source="pos_transactions",
        metric="orders",
        baseline_value=100.0,
        observed_value=80.0,
        provenance="table: pos_transactions",
    )
    d = fact.model_dump()
    assert d["id"] == "F1"
    assert d["observed_value"] == 80.0


def test_build_signal_explanation():
    sig = {
        "id": "sig-01",
        "metric_name": "revenue",
        "baseline_value": 5000.0,
        "observed_value": 4000.0,
        "change_percentage": -20.0,
        "severity": "HIGH",
    }
    exp = build_signal_explanation(sig)
    assert exp["signal_id"] == "sig-01"
    assert "-20.00%" in exp["explanation"]


def test_build_action_explanation():
    act = {
        "id": "act-01",
        "action_type": "OFFER_CAMPAIGN",
        "objective": "Re-engage evening customers",
        "target_customer_count": 486,
        "incentive_value": 50.0,
        "incentive_type": "CASHBACK",
        "duration": "7 days",
        "reason": "Addresses evening decline",
        "supporting_evidence_ids": json.dumps(["E1", "E2"]),
    }
    exp = build_action_explanation(act)
    assert exp["action_id"] == "act-01"
    assert exp["target_customer_count"] == 486
    assert exp["incentive_value"] == 50.0


def test_build_action_explanation_none():
    assert build_action_explanation(None) is None


# ==============================================================================
# 3. GUARDRAILS, DECISION & EXECUTION EXPLANATION TESTS (Tests 19 - 26)
# ==============================================================================

def test_guardrail_explanation_pass():
    grd = {
        "id": "grd-01",
        "overall_status": "PASS",
        "passed": 1,
        "notes": "All guardrails passed.",
        "checks": json.dumps([{"rule": "G1", "status": "PASS"}, {"rule": "G2", "status": "PASS"}]),
        "modifications": json.dumps({}),
        "original_values": json.dumps({}),
    }
    exp = build_guardrail_explanation(grd)
    assert exp["overall_status"] == "PASS"
    assert exp["passed"] is True
    assert "Verdict: PASS" in exp["explanation"]


def test_guardrail_explanation_modify_clamped_parameter():
    grd = {
        "id": "grd-mod",
        "overall_status": "MODIFY",
        "passed": 1,
        "notes": "Clamped cashback to ₹100.",
        "checks": json.dumps([{"rule": "G3", "status": "MODIFY"}]),
        "modifications": json.dumps({"cashback_inr": 100.0}),
        "original_values": json.dumps({"cashback_inr": 150.0}),
    }
    exp = build_guardrail_explanation(grd)
    assert exp["overall_status"] == "MODIFY"
    assert len(exp["clamp_details"]) == 1
    assert "requested 150.0 -> clamped to safety maximum 100.0" in exp["clamp_details"][0]


def test_decision_explanation_pass():
    dec = {
        "id": "dec-01",
        "decision_state": "PASS",
        "approval_required": 1,
        "approval_status": "APPROVED",
        "is_execution_eligible": 1,
        "reason": "Approved by merchant.",
    }
    exp = build_decision_explanation(dec)
    assert exp["decision_state"] == "PASS"
    assert exp["approval_status"] == "APPROVED"
    assert exp["is_execution_eligible"] is True


def test_decision_explanation_block_safety_note():
    dec = {
        "id": "dec-blk",
        "decision_state": "BLOCK",
        "approval_required": 1,
        "approval_status": "REJECTED",
        "is_execution_eligible": 0,
        "reason": "Safety margin violation.",
    }
    exp = build_decision_explanation(dec)
    assert exp["decision_state"] == "BLOCK"
    assert "permanently prohibited" in exp["safety_block_note"]
    assert exp["is_execution_eligible"] is False


def test_execution_explanation_normal():
    exe = {
        "id": "exec-01",
        "execution_state": "COMPLETED",
        "execution_mode": "SIMULATION",
        "approved_action": json.dumps({"parameters": {"cashback_inr": 50.0}}),
        "executed_at": "2026-09-18T13:00:00Z",
    }
    exp = build_execution_explanation(exe, None, None)
    assert exp["execution_state"] == "COMPLETED"
    assert exp["execution_mode"] == "SIMULATION"
    assert exp["simulated"] is True


def test_execution_explanation_modify_invariant_proof():
    action_row = {"incentive_value": 150.0}
    exe = {
        "id": "exec-mod",
        "execution_state": "COMPLETED",
        "execution_mode": "SIMULATION",
        "approved_action": json.dumps({"incentive_value": 100.0}),
    }
    exp = build_execution_explanation(exe, action_row, None)
    assert "MODIFY INVARIANT VERIFIED" in exp["invariant_note"]
    assert "NEVER executed" in exp["invariant_note"]


def test_outcome_explanation_descriptive_non_causal():
    out = {
        "id": "out-01",
        "outcome_status": "MEASURED",
        "baseline_metrics": json.dumps({"revenue": 481850.0, "evening_orders": 291.0}),
        "post_action_metrics": json.dumps({"revenue": 500000.0, "evening_orders": 331.0}),
        "metric_changes": json.dumps({
            "evening_orders": {"percentage_change": 13.75, "description": "Observed simulated change: +13.75%"},
            "revenue": {"percentage_change": 3.77},
        }),
    }
    exp = build_outcome_explanation(out)
    assert exp["framing"] == "DESCRIPTIVE_NON_CAUSAL"
    assert "+13.75%" in exp["explanation"]
    assert "causality is not asserted" in exp["explanation"]


def test_business_impact_explanation_honest_negative_roi():
    imp = {
        "id": "imp-01",
        "impact_status": "CALCULATED",
        "impact_classification": "NEGATIVE",
        "incremental_revenue": 18150.0,
        "campaign_cost": 24300.0,
        "roi_percentage": -25.31,
        "cost_per_incremental_order": 141.28,
        "revenue_per_campaign_rupee": 0.75,
    }
    exp = build_business_impact_explanation(imp)
    assert exp["impact_classification"] == "NEGATIVE"
    assert "-25.31%" in exp["explanation"]
    assert exp["gross_profit_impact"] is None
    assert "zero COGS fabrication guarantee" in exp["explanation"]


# ==============================================================================
# 4. EXPLAINABILITY ENGINE & ENTITY RESOLUTION TESTS (Tests 27 - 35)
# ==============================================================================

def test_resolve_workflow_entities_from_signal():
    SignalRepository.create_signal(
        signal_id="sig-res-01",
        signal_type="EVENING_ORDER_DECLINE",
        metric_name="evening_orders",
        baseline_value=410.0,
        observed_value=291.0,
        change_percentage=-29.02,
    )
    InvestigationRepository.create_or_update_investigation(
        signal_id="sig-res-01",
        investigation_id="inv-res-01",
        finding="Orders dropped",
        confidence=0.9,
    )
    entities = resolve_workflow_entities("sig-res-01")
    assert entities["signal"]["id"] == "sig-res-01"
    assert entities["investigation"]["id"] == "inv-res-01"
    assert entities["correlation_id"] == "wf-res-01"


def test_resolve_workflow_entities_from_correlation_id():
    AuditRepository.record_event(
        stage="DETECT",
        actor="SignalEngine",
        action_description="Detected",
        input_payload={},
        output_payload={},
        integrity_hash="hash1",
        correlation_id="wf-corr-test",
        signal_id="sig-corr-01",
    )
    SignalRepository.create_signal(signal_id="sig-corr-01", metric_name="evening_orders", baseline_value=100.0, observed_value=80.0, change_percentage=-20.0)
    entities = resolve_workflow_entities("wf-corr-test")
    assert entities["correlation_id"] == "wf-corr-test"
    assert entities["signal"]["id"] == "sig-corr-01"


def test_generate_explanation_full_summary():
    SignalRepository.create_signal(signal_id="sig-full", metric_name="evening_orders", baseline_value=410.0, observed_value=291.0, change_percentage=-29.02)
    InvestigationRepository.create_or_update_investigation(signal_id="sig-full", investigation_id="inv-full", finding="Drop found")
    ActionRepository.create_or_update_action_proposal(signal_id="sig-full", investigation_id="inv-full", merchant_id="MID-DEMO-98234", action_type="OFFER_CAMPAIGN", action_id="act-full")
    AuditRepository.record_event("DETECT", "SignalEngine", "Signal detected", {}, {}, "h1", correlation_id="wf-full", signal_id="sig-full")

    engine = ExplainabilityEngine()
    summary = engine.generate_explanation("wf-full")
    assert isinstance(summary, ExplainabilitySummary)
    assert summary.correlation_id == "wf-full"
    assert summary.signal_summary["signal_id"] == "sig-full"
    assert summary.action_summary["action_id"] == "act-full"
    assert len(summary.facts) >= 1
    assert "PROTOTYPE" in summary.disclaimer


def test_generate_explanation_missing_stages_handled():
    # Only signal exists, no action, decision, etc.
    SignalRepository.create_signal(signal_id="sig-only", metric_name="revenue", baseline_value=100.0, observed_value=80.0, change_percentage=-20.0)
    engine = ExplainabilityEngine()
    summary = engine.generate_explanation("sig-only")
    assert summary.signal_summary["signal_id"] == "sig-only"
    assert summary.action_summary is None
    assert summary.decision_summary is None
    assert summary.execution_summary is None
    assert summary.outcome_summary is None
    assert summary.business_impact_summary is None


def test_generate_explanation_blocked_execution_state():
    SignalRepository.create_signal(signal_id="sig-blk-exp", metric_name="revenue", baseline_value=100.0, observed_value=50.0, change_percentage=-50.0)
    InvestigationRepository.create_or_update_investigation(signal_id="sig-blk-exp", investigation_id="inv-blk-exp")
    ActionRepository.create_or_update_action_proposal(signal_id="sig-blk-exp", investigation_id="inv-blk-exp", merchant_id="MID-DEMO-98234", action_type="OFFER_CAMPAIGN", action_id="act-blk-exp")
    DecisionRepository.create_or_update_decision(action_id="act-blk-exp", evaluation_id="eval-blk-exp", decision_state="BLOCK", decision_id="dec-blk-exp")
    ExecutionRepository.create_execution(decision_id="dec-blk-exp", execution_id="exec-blk-exp", action_id="act-blk-exp", merchant_id="MID-DEMO-98234", execution_state="BLOCKED")

    engine = ExplainabilityEngine()
    summary = engine.generate_explanation("sig-blk-exp")
    assert summary.decision_summary["decision_state"] == "BLOCK"
    assert summary.execution_summary["execution_state"] == "BLOCKED"
    assert summary.outcome_summary is None
    assert summary.business_impact_summary is None


def test_generate_explanation_simulation_labels_present():
    engine = ExplainabilityEngine()
    summary = engine.generate_explanation("wf-dummy")
    assert "SIMULATED" in summary.disclaimer
    assert "PROTOTYPE" in summary.disclaimer
    assert "DIGITAL TWIN" in summary.disclaimer


def test_generate_explanation_determinism():
    SignalRepository.create_signal(signal_id="sig-det-test", metric_name="orders", baseline_value=500.0, observed_value=400.0, change_percentage=-20.0)
    engine = ExplainabilityEngine()
    s1 = engine.generate_explanation("sig-det-test")
    s2 = engine.generate_explanation("sig-det-test")
    assert s1.signal_summary == s2.signal_summary
    assert len(s1.facts) == len(s2.facts)


def test_explainability_zero_secrets():
    AuditRepository.record_event(
        "ACT", "Actor", "Executed",
        input_payload={"token": "secret_abc", "password": "pass"},
        output_payload={"status": "OK"},
        integrity_hash="h1",
        correlation_id="wf-sec-test",
    )
    engine = ExplainabilityEngine()
    summary = engine.generate_explanation("wf-sec-test")
    raw_json = summary.model_dump_json()
    assert "secret_abc" not in raw_json
    assert "[REDACTED]" in raw_json


# ==============================================================================
# 5. REST API ENDPOINT TESTS (Tests 36 - 45)
# ==============================================================================

def test_api_list_audit_events(client):
    AuditRepository.record_event("DETECT", "A", "Act A", {}, {}, "h1", correlation_id="wf-api-01")
    resp = client.get("/api/audit/events?correlation_id=wf-api-01")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["correlation_id"] == "wf-api-01"


def test_api_get_audit_event_by_id(client):
    row = AuditRepository.record_event("DETECT", "A", "Act A", {}, {}, "h1", event_id="aud-api-test")
    resp = client.get("/api/audit/events/aud-api-test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == "aud-api-test"


def test_api_get_audit_event_404(client):
    resp = client.get("/api/audit/events/aud-fake-999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_get_workflow_audit_chain(client):
    engine = AuditEngine()
    engine.record_event(StageType.DETECT, "A", "Act 1", {}, {}, correlation_id="wf-chain-api")
    engine.record_event(StageType.GUARD, "B", "Act 2", {}, {}, correlation_id="wf-chain-api")
    resp = client.get("/api/audit/workflow/wf-chain-api")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_api_verify_workflow_audit_valid(client):
    engine = AuditEngine()
    engine.record_event(StageType.DETECT, "A", "Step 1", {}, {}, correlation_id="wf-verify-api")
    engine.record_event(StageType.GUARD, "B", "Step 2", {}, {}, correlation_id="wf-verify-api")
    resp = client.get("/api/audit/workflow/wf-verify-api/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["event_count"] == 2
    assert data["verification_mode"] == "SHA-256"


def test_api_verify_workflow_audit_tampered(client):
    engine = AuditEngine()
    e = engine.record_event(StageType.ACT, "A", "Step 1", {"val": 10}, {}, correlation_id="wf-tamper-api")
    # Mutate in DB
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE audit_events SET input_payload = ? WHERE id = ?", (json.dumps({"val": 9999}), e.event_id))
        conn.commit()
    finally:
        conn.close()

    resp = client.get("/api/audit/workflow/wf-tamper-api/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert "Tampered hash detected" in data["error"]


def test_api_get_workflow_explanation(client):
    SignalRepository.create_signal(signal_id="sig-api-exp", metric_name="evening_orders", baseline_value=410.0, observed_value=291.0, change_percentage=-29.02)
    resp = client.get("/api/explainability/workflow/wf-api-exp")
    assert resp.status_code == 200
    data = resp.json()
    assert data["correlation_id"] == "wf-api-exp"
    assert "signal_summary" in data
    assert "facts" in data
    assert "disclaimer" in data


def test_api_get_entity_explanation_valid_types(client):
    SignalRepository.create_signal(signal_id="sig-ent-test", metric_name="evening_orders", baseline_value=410.0, observed_value=291.0, change_percentage=-29.02)
    resp = client.get("/api/explainability/entity/signal/sig-ent-test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["signal_summary"]["signal_id"] == "sig-ent-test"


def test_api_get_entity_explanation_invalid_type_returns_400(client):
    resp = client.get("/api/explainability/entity/invalid_type/12345")
    assert resp.status_code == 400
    assert "Invalid entity_type" in resp.json()["detail"]


def test_audit_api_is_strictly_read_only(client):
    # Prohibit POST, PUT, DELETE to audit endpoints
    r1 = client.post("/api/audit/events", json={"data": "fake"})
    assert r1.status_code == 405
    r2 = client.delete("/api/audit/events/aud-123")
    assert r2.status_code == 405
    r3 = client.put("/api/audit/workflow/wf-123", json={})
    assert r3.status_code == 405
