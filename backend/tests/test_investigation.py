import json
import pytest
from starlette.testclient import TestClient

from app.database.connection import init_db
from app.database.repository import (
    CampaignRepository,
    CustomerRepository,
    InvestigationRepository,
    SignalRepository,
    TransactionRepository,
)
from app.database.seed import seed_digital_twin
from app.engines.audit_engine.engine import AuditEngine
from app.engines.investigation_engine.evidence_builder import EvidenceBuilder
from app.engines.investigation_engine.investigation_engine import InvestigationEngine
from app.engines.investigation_engine.schemas import (
    ConfidenceLevel,
    EvidenceBundle,
    EvidenceCategory,
    InvestigationResult,
)
from app.engines.investigation_engine.validator import InvestigationValidator
from app.llm.client import FallbackClient, LLMClient
from app.main import app
from app.models.contracts import Signal
from app.models.enums import SignalSeverity, SignalStatus


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    seed_digital_twin()


def _get_primary_demo_signal() -> Signal:
    """Helper to fetch or construct primary EVENING_ORDER_DECLINE signal."""
    raw = SignalRepository.get_signals(merchant_id="MID-DEMO-98234")
    evn = next((s for s in raw if "EVENING" in s["signal_type"]), None)
    if not evn:
        # If not present, upsert it
        row = SignalRepository.upsert_active_signal(
            merchant_id="MID-DEMO-98234",
            signal_type="EVENING_ORDER_DECLINE",
            severity="HIGH",
            metric_name="evening_orders",
            baseline_value=410.0,
            observed_value=291.0,
            change_percentage=-29.02,
            decline_percentage=29.02,
            description="Evening orders dropped 29.02%.",
        )
        return Signal(
            signal_id=row["id"],
            merchant_id=row["merchant_id"],
            signal_type=row["signal_type"],
            severity=SignalSeverity(row["severity"]),
            metric_name=row["metric_name"],
            baseline_value=float(row["baseline_value"]),
            observed_value=float(row["observed_value"]),
            change_percentage=float(row["change_percentage"]),
            decline_percentage=float(row["decline_percentage"]),
            variance_percentage=float(row["change_percentage"]),
            description=row["description"],
            status=SignalStatus.ACTIVE,
        )

    return Signal(
        signal_id=evn["id"],
        merchant_id=evn["merchant_id"],
        signal_type=evn["signal_type"],
        severity=SignalSeverity(evn["severity"]),
        metric_name=evn["metric_name"],
        baseline_value=float(evn["baseline_value"]),
        observed_value=float(evn["observed_value"]),
        change_percentage=float(evn.get("change_percentage", -29.02)),
        decline_percentage=float(evn.get("decline_percentage", 29.02)),
        variance_percentage=float(evn.get("change_percentage", -29.02)),
        description=evn["description"],
        status=SignalStatus.ACTIVE,
    )


def test_1_evidence_bundle_construction():
    """Verifies that EvidenceBundle is constructed with all required fields and categories."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    assert isinstance(bundle, EvidenceBundle)
    assert bundle.signal_id == signal.signal_id
    assert bundle.merchant_id == "MID-DEMO-98234"
    assert len(bundle.evidence_items) == 5

    categories = [item.category for item in bundle.evidence_items]
    assert EvidenceCategory.PRIMARY_SIGNAL in categories
    assert EvidenceCategory.CUSTOMER_BEHAVIOR in categories
    assert EvidenceCategory.CAMPAIGN_CONTEXT in categories
    assert EvidenceCategory.TARGET_AUDIENCE in categories
    assert EvidenceCategory.BUSINESS_CONTEXT in categories


def test_2_primary_signal_evidence_traceability():
    """Verifies E1 correctly captures primary evening orders drop."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    e1 = next(item for item in bundle.evidence_items if item.evidence_id == "E1")
    assert e1.category == EvidenceCategory.PRIMARY_SIGNAL
    assert e1.baseline == 410.0
    assert e1.current == 291.0
    assert e1.change_percentage == -29.02
    assert "410" in e1.observation and "291" in e1.observation
    assert e1.source == "transactions"


def test_3_repeat_conversion_evidence():
    """Verifies E2 captures repeat customer conversion change from SQLite."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    e2 = next(item for item in bundle.evidence_items if item.evidence_id == "E2")
    assert e2.category == EvidenceCategory.CUSTOMER_BEHAVIOR
    assert e2.baseline == 0.182
    assert e2.current == 0.148
    assert e2.change_percentage == -18.68
    assert "18.2%" in e2.observation and "14.8%" in e2.observation
    assert e2.source == "business_metrics"


def test_4_expired_campaign_contextual_evidence():
    """Verifies E3 captures expired campaign timing without claiming causality."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    e3 = next(item for item in bundle.evidence_items if item.evidence_id == "E3")
    assert e3.category == EvidenceCategory.CAMPAIGN_CONTEXT
    assert "Evening Rush" in e3.observation
    assert "expired" in e3.observation.lower()
    assert e3.source == "campaigns"


def test_5_missing_evidence_safe_handling(monkeypatch):
    """Verifies that missing or unqueried tables safely produce 'data unavailable'."""
    from app.database.repository import BusinessMetricRepository, CampaignRepository
    monkeypatch.setattr(BusinessMetricRepository, "get_metrics_map", lambda mid: {})
    monkeypatch.setattr(CampaignRepository, "get_campaigns", lambda mid: [])

    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    e2 = next(item for item in bundle.evidence_items if item.evidence_id == "E2")
    assert e2.observation == "data unavailable"
    assert e2.baseline == "data unavailable"

    e3 = next(item for item in bundle.evidence_items if item.evidence_id == "E3")
    assert e3.observation == "data unavailable"


def test_6_structured_gemini_response_validation():
    """Verifies that a valid LLM response passes validation and parses correctly."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    valid_llm_json = json.dumps({
        "summary": "Evening orders declined by 29.02%. Repeat conversion also dropped, coinciding with campaign expiry.",
        "findings": [
            "Evening transactions dropped from 410 to 291 orders (E1).",
            "Repeat customer conversion dropped by 18.68% (E2)."
        ],
        "hypotheses": [
            {
                "hypothesis": "Weakened repeat conversion may be associated with the evening volume decline.",
                "rationale": "Repeat customers form a major portion of evening transactions.",
                "supporting_evidence_ids": ["E1", "E2"],
                "confidence": "HIGH"
            },
            {
                "hypothesis": "The absence of the previous cashback offer may correlate with lower evening velocity.",
                "rationale": "The decline followed campaign expiration 3 days ago.",
                "supporting_evidence_ids": ["E1", "E3"],
                "confidence": "MEDIUM"
            }
        ],
        "confidence": "HIGH",
        "limitations": [
            "External local merchant competition is unobserved."
        ]
    })

    is_valid, res, err = InvestigationValidator.validate_and_parse(valid_llm_json, bundle, "inv-test-01")
    assert is_valid is True
    assert res is not None
    assert res.confidence == ConfidenceLevel.HIGH
    assert len(res.hypotheses) == 2
    assert "E1" in res.evidence_ids
    assert "E2" in res.evidence_ids


def test_7_hallucination_validator_rejects_unsupported_evidence():
    """Verifies that cited invalid evidence IDs or fabricated metrics trigger rejection."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    # Scenario A: Hallucinated evidence ID "E99"
    hallucinated_id_json = json.dumps({
        "summary": "Fabricated summary",
        "findings": ["Fabricated finding citing E99"],
        "hypotheses": [
            {
                "hypothesis": "Fabricated hypothesis",
                "rationale": "Reasoning",
                "supporting_evidence_ids": ["E1", "E99"],
                "confidence": "MEDIUM"
            }
        ],
        "confidence": "MEDIUM",
        "limitations": []
    })

    is_valid, res, err = InvestigationValidator.validate_and_parse(hallucinated_id_json, bundle, "inv-test-02")
    assert is_valid is False
    assert "Unknown evidence ID 'E99'" in err

    # Scenario B: Fabricated percentage "88.5%" not in evidence
    hallucinated_metric_json = json.dumps({
        "summary": "Orders collapsed by 88.5% due to competitor entrance.",
        "findings": ["Orders fell 88.5%"],
        "hypotheses": [
            {
                "hypothesis": "Competitor discounts may be associated with loss.",
                "rationale": "Reasoning",
                "supporting_evidence_ids": ["E1"],
                "confidence": "MEDIUM"
            }
        ],
        "confidence": "MEDIUM",
        "limitations": []
    })

    is_valid2, res2, err2 = InvestigationValidator.validate_and_parse(hallucinated_metric_json, bundle, "inv-test-03")
    assert is_valid2 is False
    assert "Fabricated metric '88.5%'" in err2


def test_8_causal_language_sanitization_and_detection():
    """Verifies that absolute causal claims (caused by, led to, etc.) are caught."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    causal_llm_json = json.dumps({
        "summary": "Evening orders fell 29.02%.",
        "findings": ["Orders dropped from 410 to 291 (E1)."],
        "hypotheses": [
            {
                "hypothesis": "The drop was directly caused by the expired campaign.",
                "rationale": "Reasoning",
                "supporting_evidence_ids": ["E1", "E3"],
                "confidence": "MEDIUM"
            }
        ],
        "confidence": "MEDIUM",
        "limitations": []
    })

    is_valid, res, err = InvestigationValidator.validate_and_parse(causal_llm_json, bundle, "inv-test-04")
    assert is_valid is True
    # The phrase "directly caused by" must have been sanitized to associative language
    assert "directly caused by" not in res.hypotheses[0].hypothesis.lower()
    assert "may be associated with" in res.hypotheses[0].hypothesis.lower()


def test_9_confidence_rule_clamping():
    """Verifies that HIGH confidence with < 2 supporting evidence items is clamped to MEDIUM."""
    signal = _get_primary_demo_signal()
    bundle = EvidenceBuilder.build_evidence(signal)

    single_evidence_high_conf_json = json.dumps({
        "summary": "Evening orders fell 29.02%.",
        "findings": ["Orders dropped from 410 to 291 (E1)."],
        "hypotheses": [
            {
                "hypothesis": "Volume drop may correlate with customer lull.",
                "rationale": "Reasoning",
                "supporting_evidence_ids": ["E1"],  # Only 1 evidence item!
                "confidence": "HIGH"  # Invalid per confidence rules!
            }
        ],
        "confidence": "HIGH",
        "limitations": []
    })

    is_valid, res, err = InvestigationValidator.validate_and_parse(single_evidence_high_conf_json, bundle, "inv-test-05")
    assert is_valid is True
    # Confidence must be clamped to MEDIUM
    assert res.hypotheses[0].confidence == ConfidenceLevel.MEDIUM
    assert res.confidence == ConfidenceLevel.MEDIUM


@pytest.mark.asyncio
async def test_10_fallback_investigation_deterministic():
    """Verifies that FallbackClient produces a conservative, structured investigation."""
    signal = _get_primary_demo_signal()
    engine = InvestigationEngine(llm_client=FallbackClient())

    result = await engine.investigate(signal=signal, force_fallback=True)
    assert isinstance(result, InvestigationResult)
    assert result.is_fallback is True
    assert result.signal_id == signal.signal_id
    assert len(result.hypotheses) >= 2
    assert any("repeat" in h.hypothesis.lower() for h in result.hypotheses)
    assert any("campaign" in h.hypothesis.lower() for h in result.hypotheses)
    assert all(h.confidence == ConfidenceLevel.MEDIUM for h in result.hypotheses)


@pytest.mark.asyncio
async def test_11_investigation_persistence_and_idempotency():
    """Verifies investigations persist in SQLite and repeated calls do not duplicate rows."""
    signal = _get_primary_demo_signal()
    engine = InvestigationEngine(llm_client=FallbackClient())

    res1 = await engine.investigate(signal=signal, force_fallback=True)
    id1 = res1.investigation_id

    # Verify saved in SQLite
    saved1 = InvestigationRepository.get_investigation(id1)
    assert saved1 is not None
    assert saved1["signal_id"] == signal.signal_id

    # Verify query by signal ID
    saved_by_sig = InvestigationRepository.get_investigation_by_signal(signal.signal_id)
    assert saved_by_sig is not None
    assert saved_by_sig["id"] == id1

    # Run investigation again (idempotency test)
    res2 = await engine.investigate(signal=signal, force_fallback=True)
    id2 = res2.investigation_id

    # Must reuse the same investigation record ID
    assert id1 == id2


def test_12_api_post_and_get_investigation(client: TestClient):
    """Verifies POST /api/investigations/{signal_id} and GET endpoints."""
    signal = _get_primary_demo_signal()

    # 1. POST /api/investigations/{signal_id}
    post_res = client.post(f"/api/investigations/{signal.signal_id}?force_fallback=true")
    assert post_res.status_code == 200
    inv_data = post_res.json()

    assert inv_data["signal_id"] == signal.signal_id
    assert inv_data["status"] == "COMPLETED"
    assert len(inv_data["hypotheses"]) >= 1
    assert "E1" in inv_data["evidence_ids"]

    inv_id = inv_data["investigation_id"]

    # 2. GET /api/investigations/{investigation_id}
    get_res = client.get(f"/api/investigations/{inv_id}")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["investigation_id"] == inv_id

    # 3. GET /api/signals/{signal_id}/investigation
    sig_inv_res = client.get(f"/api/signals/{signal.signal_id}/investigation")
    assert sig_inv_res.status_code == 200
    sig_data = sig_inv_res.json()
    assert sig_data["investigation_id"] == inv_id


@pytest.mark.asyncio
async def test_13_audit_trail_logging():
    """Verifies INVESTIGATION_STARTED and INVESTIGATION_COMPLETED events in audit_events."""
    audit_engine = AuditEngine()
    signal = _get_primary_demo_signal()
    engine = InvestigationEngine(llm_client=FallbackClient(), audit_engine=audit_engine)

    await engine.investigate(signal=signal, force_fallback=True)

    events = audit_engine.get_events()
    assert any("Initiated investigation" in e.action_description for e in events)
    assert any("Completed investigation" in e.action_description for e in events)


@pytest.mark.asyncio
async def test_14_unconfigured_gemini_falls_back_gracefully():
    """Verifies that an unconfigured or failing LLM client safely produces a fallback investigation."""
    class FailingLLMClient(LLMClient):
        @property
        def provider_name(self) -> str:
            return "FailingClient"

        @property
        def is_available(self) -> bool:
            return True

        async def generate(self, prompt: str, system_instruction=None, temperature=0.2) -> str:
            raise ConnectionError("Simulated LLM API network failure")

    signal = _get_primary_demo_signal()
    engine = InvestigationEngine(llm_client=FailingLLMClient())

    # Must complete without crashing and mark is_fallback = True
    result = await engine.investigate(signal=signal)
    assert result.is_fallback is True
    assert result.status == "COMPLETED"
    assert len(result.hypotheses) >= 2

