import pytest
from starlette.testclient import TestClient
from app.database.seed import seed_digital_twin
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_merchant_digital_twin_scenario_details(client: TestClient):
    """Verifies that the primary demo merchant meets all Hackathon requirements."""
    seed_digital_twin()

    response = client.get("/api/merchant")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == "MID-DEMO-98234"
    assert data["name"] == "Sharma Kirana & General Store"
    assert data["category"] == "Retail / Grocery"
    assert data["location"] == "Delhi NCR"
    assert data["minimum_margin"] == 0.10
    assert data["daily_budget"] == 12000.0
    assert data["max_discount"] == 100.0
    assert data["autonomy_level"] == "APPROVAL_REQUIRED"
    assert data["simulated"] is True


def test_evening_order_decline_scenario(client: TestClient):
    """Verifies that the evening order decline of ~29% is derived from seeded data."""
    seed_digital_twin()

    response = client.get("/api/merchant/metrics")
    assert response.status_code == 200
    metrics = response.json()

    # Scenario numbers check
    baseline = metrics["evening_orders_baseline"]
    observed = metrics["evening_orders_current"]
    variance_pct = metrics["evening_orders_variance_pct"]

    assert baseline == 410
    assert observed == 291
    # Variance should be approximately -29%
    assert -30.0 <= variance_pct <= -28.0
    assert metrics["simulated"] is True
    assert metrics["total_orders"] == 1284
    assert 480000.0 <= metrics["total_revenue_inr"] <= 485000.0


def test_repeat_customer_conversion_root_cause(client: TestClient):
    """Verifies that repeat-customer conversion deterioration is present in metrics."""
    seed_digital_twin()

    response = client.get("/api/merchant/metrics")
    metrics = response.json()

    assert metrics["repeat_conversion_baseline"] == 0.182
    assert metrics["repeat_conversion_current"] == 0.148
    # Conversion dropped by approx 3.4 percentage points
    assert metrics["repeat_conversion_current"] < metrics["repeat_conversion_baseline"]


def test_campaign_history_shows_expired_evening_campaign(client: TestClient):
    """Verifies that previous campaign exists, targeted evening rush, and is expired."""
    seed_digital_twin()

    response = client.get("/api/merchant/campaigns")
    assert response.status_code == 200
    campaigns = response.json()

    assert len(campaigns) >= 1
    expired_evening = next((c for c in campaigns if "Evening Rush" in c["name"]), None)
    assert expired_evening is not None
    assert expired_evening["status"] == "EXPIRED"
    assert expired_evening["target_customer_count"] == 486
    assert expired_evening["simulated"] is True


def test_customer_summary_and_target_segment(client: TestClient):
    """Verifies total customer count >= 500 and target campaign segment is derived as 486."""
    seed_digital_twin()

    response = client.get("/api/merchant/customers/summary")
    assert response.status_code == 200
    summary = response.json()

    assert summary["total_customers"] >= 500
    assert summary["total_customers"] == 520
    assert summary["target_campaign_customers"] == 486

    segments = summary["segment_breakdown"]
    assert "repeat_customer" in segments
    assert "regular" in segments
    assert "inactive" in segments
    assert "new_customer" in segments


def test_simulation_status_api(client: TestClient):
    """Verifies simulation status endpoint exposes digital twin flags correctly."""
    seed_digital_twin()

    response = client.get("/api/simulation/status")
    assert response.status_code == 200
    data = response.json()

    assert data["simulation_mode"] is True
    assert data["database_seeded"] is True
    assert data["active_merchant_id"] == "MID-DEMO-98234"
    assert "PROTOTYPE SIMULATION NOTICE" in data["simulation_disclaimer"]
