import pytest
from starlette.testclient import TestClient
from app.database.repository import SignalRepository
from app.database.seed import seed_digital_twin
from app.engines.audit_engine.engine import AuditEngine
from app.engines.signal_engine.detectors import (
    CampaignUnderperformanceDetector,
    CustomerEngagementDeclineDetector,
    EveningOrderDeclineDetector,
    RepeatCustomerConversionDetector,
    RevenueDeclineDetector,
)
from app.engines.signal_engine.engine import SignalDetectionEngine
from app.engines.signal_engine.thresholds import DEFAULT_THRESHOLDS, ThresholdConfig
from app.main import app
from app.models.enums import SignalSeverity, SignalStatus


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_threshold_classification():
    """Verifies deterministic classification into NONE, LOW, MEDIUM, HIGH, CRITICAL."""
    thresholds = ThresholdConfig()

    assert thresholds.classify_decline(2.5) is None
    assert thresholds.classify_decline(4.99) is None
    assert thresholds.classify_decline(5.0) == SignalSeverity.LOW
    assert thresholds.classify_decline(9.9) == SignalSeverity.LOW
    assert thresholds.classify_decline(10.0) == SignalSeverity.MEDIUM
    assert thresholds.classify_decline(19.99) == SignalSeverity.MEDIUM
    assert thresholds.classify_decline(20.0) == SignalSeverity.HIGH
    assert thresholds.classify_decline(29.02) == SignalSeverity.HIGH
    assert thresholds.classify_decline(30.0) == SignalSeverity.CRITICAL
    assert thresholds.classify_decline(45.0) == SignalSeverity.CRITICAL


def test_evening_decline_calculation_formula():
    """Verifies that the evening orders calculation yields exactly ~29.02% from seeded digital twin."""
    seed_digital_twin()
    detector = EveningOrderDeclineDetector()
    result = detector.detect("MID-DEMO-98234")

    assert result is not None
    assert result.signal_type == "EVENING_ORDER_DECLINE"
    assert result.baseline_value == 410.0
    assert result.current_value == 291.0
    assert result.change_percentage == -29.02
    assert result.decline_percentage == 29.02
    assert result.severity == SignalSeverity.HIGH
    assert "29.02%" in result.description
    assert result.evidence["baseline_evening_orders"] == 410
    assert result.evidence["current_evening_orders"] == 291


def test_all_five_detectors_execute():
    """Verifies that all 5 deterministic detectors execute according to Phase 3 rules."""
    seed_digital_twin()
    merchant_id = "MID-DEMO-98234"

    d1 = EveningOrderDeclineDetector().detect(merchant_id)
    assert d1 is not None
    assert d1.signal_type == "EVENING_ORDER_DECLINE"
    assert d1.severity == SignalSeverity.HIGH

    d2 = RepeatCustomerConversionDetector().detect(merchant_id)
    assert d2 is not None
    assert d2.signal_type == "REPEAT_CUSTOMER_CONVERSION_DECLINE"
    assert d2.severity == SignalSeverity.MEDIUM
    assert d2.baseline_value == 0.182
    assert d2.current_value == 0.148

    d3 = RevenueDeclineDetector().detect(merchant_id)
    assert d3 is not None
    assert d3.signal_type == "REVENUE_DECLINE"
    assert d3.severity == SignalSeverity.HIGH

    # Correction 1: Seeded merchant only has EXPIRED campaign; must return NO SIGNAL (None)
    d4 = CampaignUnderperformanceDetector().detect(merchant_id)
    assert d4 is None

    # Correction 2: Inactive ratio uses relative deterioration formula ((7.69 - 5.0) / 5.0) * 100 = 53.8%
    d5 = CustomerEngagementDeclineDetector().detect(merchant_id)
    assert d5 is not None
    assert d5.signal_type == "CUSTOMER_ENGAGEMENT_DECLINE"
    assert d5.severity == SignalSeverity.CRITICAL
    assert d5.evidence["current_ratio"] == 7.69
    assert d5.evidence["baseline_ratio"] == 5.0
    assert d5.evidence["change_percentage"] == 53.8
    assert d5.baseline_value == 5.0
    assert d5.current_value == 7.69


def test_campaign_underperformance_requires_active_campaign(monkeypatch):
    """Verifies that CAMPAIGN_UNDERPERFORMANCE triggers ONLY when an active campaign underperforms."""
    detector = CampaignUnderperformanceDetector()

    # Scenario A: No active campaigns (e.g. only expired) -> returns None (NO SIGNAL)
    from app.database.repository import CampaignRepository
    monkeypatch.setattr(
        CampaignRepository,
        "get_campaigns",
        lambda mid: [
            {"id": "CAMP-01", "name": "Expired Promo", "status": "EXPIRED", "target_customer_count": 486}
        ],
    )
    assert detector.detect("TEST-MID") is None

    # Scenario B: Active campaign with performance below 15% benchmark
    # 486 target customers * 0.15 = 72.9 expected conversions. Actual = 10 (86.28% decline -> CRITICAL)
    monkeypatch.setattr(
        CampaignRepository,
        "get_campaigns",
        lambda mid: [
            {
                "id": "CAMP-02",
                "name": "Live Weekend Flash",
                "campaign_type": "CASHBACK_OFFER",
                "status": "ACTIVE",
                "target_customer_count": 486,
                "actual_conversions": 10.0,
            }
        ],
    )
    res = detector.detect("TEST-MID")
    assert res is not None
    assert res.signal_type == "CAMPAIGN_UNDERPERFORMANCE"
    assert res.baseline_value == 72.9
    assert res.current_value == 10.0
    assert res.decline_percentage == 86.28
    assert res.severity == SignalSeverity.CRITICAL

    # Scenario C: Active campaign meeting benchmark (actual 80 >= expected 72.9) -> returns None
    monkeypatch.setattr(
        CampaignRepository,
        "get_campaigns",
        lambda mid: [
            {
                "id": "CAMP-03",
                "name": "High Performing Offer",
                "campaign_type": "CASHBACK_OFFER",
                "status": "ACTIVE",
                "target_customer_count": 486,
                "actual_conversions": 80.0,
            }
        ],
    )
    assert detector.detect("TEST-MID") is None


def test_customer_engagement_relative_deterioration_formula(monkeypatch):
    """Verifies the ((current - baseline) / baseline) * 100 relative deterioration formula."""
    from app.database.repository import CustomerRepository
    detector = CustomerEngagementDeclineDetector()

    # 40 inactive out of 520 = 7.692% -> rounded to 7.69%
    # Baseline = 5.0%
    # Relative deterioration = ((7.69 - 5.0) / 5.0) * 100 = 53.8%
    # 53.8% > 30% -> CRITICAL
    monkeypatch.setattr(
        CustomerRepository,
        "get_customers_summary",
        lambda mid: {
            "total_customers": 520,
            "segment_breakdown": {"inactive": 40, "repeat_customer": 216, "regular": 240, "new_customer": 24},
        },
    )
    result = detector.detect("TEST-MID")
    assert result is not None
    assert result.signal_type == "CUSTOMER_ENGAGEMENT_DECLINE"
    assert result.severity == SignalSeverity.CRITICAL
    assert result.baseline_value == 5.0
    assert result.current_value == 7.69
    assert result.change_percentage == 53.8
    assert result.evidence["current_ratio"] == 7.69
    assert result.evidence["baseline_ratio"] == 5.0
    assert result.evidence["change_percentage"] == 53.8
    assert result.evidence["formula"] == "((current_ratio - baseline_ratio) / baseline_ratio) * 100"

    # Edge case: Inactive ratio is within baseline (e.g., 20 / 520 = 3.85% <= 5.0%) -> returns None
    monkeypatch.setattr(
        CustomerRepository,
        "get_customers_summary",
        lambda mid: {
            "total_customers": 520,
            "segment_breakdown": {"inactive": 20, "repeat_customer": 236, "regular": 240, "new_customer": 24},
        },
    )
    assert detector.detect("TEST-MID") is None


def test_signal_detection_engine_persistence_and_audit():
    """Verifies engine execution persists signals to SQLite and logs audit events."""
    seed_digital_twin()
    audit_engine = AuditEngine()
    engine = SignalDetectionEngine(audit_engine=audit_engine)

    signals = engine.detect_signals("MID-DEMO-98234")
    assert len(signals) >= 1

    evn_signal = next((s for s in signals if s.signal_type == "EVENING_ORDER_DECLINE"), None)
    assert evn_signal is not None
    assert evn_signal.severity == SignalSeverity.HIGH
    assert evn_signal.change_percentage == -29.02
    assert evn_signal.decline_percentage == 29.02
    assert evn_signal.status == SignalStatus.ACTIVE

    # Check persistence in database
    db_signals = SignalRepository.get_signals("MID-DEMO-98234")
    assert len(db_signals) >= 1
    persisted_evn = next((s for s in db_signals if s["signal_type"] == "EVENING_ORDER_DECLINE"), None)
    assert persisted_evn is not None
    assert persisted_evn["change_percentage"] == -29.02

    # Check audit events recorded
    events = audit_engine.get_events()
    assert len(events) >= 2
    assert any(e.action_description.startswith("Initiated deterministic") for e in events)
    assert any("EVENING_ORDER_DECLINE" in e.action_description for e in events)


def test_signal_deduplication_and_idempotency():
    """Calling detection multiple times must NOT duplicate active signals."""
    seed_digital_twin()
    engine = SignalDetectionEngine()

    run1 = engine.detect_signals("MID-DEMO-98234")
    count1 = len(run1)

    # Run detection again immediately
    run2 = engine.detect_signals("MID-DEMO-98234")
    count2 = len(run2)

    assert count1 == count2

    # Verify database has exactly count1 ACTIVE signals, not double
    active_in_db = SignalRepository.get_signals("MID-DEMO-98234", status="ACTIVE")
    assert len(active_in_db) == count1

    # Verify IDs are preserved
    run1_ids = {s.signal_id for s in run1}
    run2_ids = {s.signal_id for s in run2}
    assert run1_ids == run2_ids


def test_zero_baseline_safe_division():
    """Verifies that a 0 or negative baseline safely returns None without ZeroDivisionError."""
    detector = EveningOrderDeclineDetector()
    # Query with non-existent merchant has 0 baseline
    res = detector.detect("MID-NONEXISTENT-99999")
    assert res is None


def test_api_detection_and_retrieval(client: TestClient):
    """Verifies POST /api/signals/detect and GET /api/signals endpoints."""
    seed_digital_twin()

    # 1. Trigger detection via API
    detect_res = client.post("/api/signals/detect", json={"merchant_id": "MID-DEMO-98234"})
    assert detect_res.status_code == 200
    detect_data = detect_res.json()

    assert detect_data["merchant_id"] == "MID-DEMO-98234"
    assert detect_data["count"] >= 1
    assert detect_data["simulated"] is True

    signals = detect_data["signals_detected"]
    evn = next((s for s in signals if s["signal_type"] == "EVENING_ORDER_DECLINE"), None)
    assert evn is not None
    assert evn["severity"] == "HIGH"
    assert evn["change_percentage"] == -29.02
    assert evn["decline_percentage"] == 29.02
    assert evn["baseline_value"] == 410.0
    assert evn["observed_value"] == 291.0

    # 2. Query signals via GET with filters
    list_res = client.get("/api/signals", params={"merchant_id": "MID-DEMO-98234", "status": "ACTIVE"})
    assert list_res.status_code == 200
    listed_signals = list_res.json()
    assert len(listed_signals) >= 1

    # Filter by severity
    high_res = client.get("/api/signals", params={"merchant_id": "MID-DEMO-98234", "severity": "HIGH"})
    assert high_res.status_code == 200
    high_signals = high_res.json()
    assert all(s["severity"] == "HIGH" for s in high_signals)

    # 3. Retrieve single signal by ID
    single_res = client.get(f"/api/signals/{evn['signal_id']}")
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["signal_id"] == evn["signal_id"]
    assert single_data["signal_type"] == "EVENING_ORDER_DECLINE"
