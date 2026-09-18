import pytest
from starlette.testclient import TestClient
from app.database.connection import get_connection, init_db
from app.database.repository import (
    BusinessMetricRepository,
    CampaignRepository,
    CustomerRepository,
    MerchantRepository,
    TransactionRepository,
)
from app.database.seed import seed_digital_twin
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_database_initialization():
    """Validates that all 13 core tables exist in SQLite."""
    init_db()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = {row["name"] for row in cursor.fetchall()}
        required_tables = {
            "merchants",
            "customers",
            "transactions",
            "campaigns",
            "business_metrics",
            "signals",
            "investigations",
            "actions",
            "guardrail_evaluations",
            "decisions",
            "executions",
            "outcomes",
            "audit_events",
        }
        for t in required_tables:
            assert t in tables, f"Missing required table: {t}"
    finally:
        conn.close()


def test_seed_script_repeatability():
    """Verifies that seed_digital_twin can be executed repeatedly with identical counts."""
    res1 = seed_digital_twin()
    res2 = seed_digital_twin()

    assert res1["merchants"] == 1
    assert res1["customers"] == 520
    assert res1["transactions"] == 1284
    assert res1["evening_orders_current"] == 291
    assert res1["evening_orders_baseline"] == 410
    assert res1["target_campaign_customers"] == 486

    # Both runs must produce identical results
    assert res1 == res2


def test_repositories_query_seeded_data():
    """Verifies repository functions correctly retrieve the seeded dataset."""
    seed_digital_twin()

    merchant = MerchantRepository.get_merchant("MID-DEMO-98234")
    assert merchant is not None
    assert merchant["name"] == "Sharma Kirana & General Store"
    assert merchant["minimum_margin"] == 0.10
    assert merchant["daily_budget"] == 12000.0

    cust_summary = CustomerRepository.get_customers_summary("MID-DEMO-98234")
    assert cust_summary["total_customers"] == 520
    assert cust_summary["target_campaign_customers"] == 486
    assert "repeat_customer" in cust_summary["segment_breakdown"]

    stats = TransactionRepository.get_stats("MID-DEMO-98234")
    assert stats["total_orders"] == 1284
    assert stats["evening_orders"] == 291
    assert 480000.0 <= stats["total_revenue"] <= 485000.0

    metrics = BusinessMetricRepository.get_metrics_map("MID-DEMO-98234")
    assert metrics["evening_orders_baseline"] == 410.0
    assert metrics["evening_orders_observed"] == 291.0
    assert metrics["repeat_conversion_observed"] == 0.148

    campaigns = CampaignRepository.get_campaigns("MID-DEMO-98234")
    assert len(campaigns) >= 1
    expired_campaign = next((c for c in campaigns if c["name"].startswith("Evening Rush")), None)
    assert expired_campaign is not None
    assert expired_campaign["status"] == "EXPIRED"


def test_simulation_reset_endpoint(client: TestClient):
    """POST /api/simulation/reset must restore deterministic state."""
    response = client.post("/api/simulation/reset")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["simulated"] is True
    assert data["seed_summary"]["customers"] == 520
    assert data["seed_summary"]["transactions"] == 1284
    assert data["seed_summary"]["target_campaign_customers"] == 486
