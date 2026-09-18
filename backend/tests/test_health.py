import pytest
from starlette.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Provides a synchronous test client for FastAPI."""
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client: TestClient):
    """Health endpoint must return 200 with status ok and service MITRA."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "MITRA"


def test_system_status_endpoint(client: TestClient):
    """System status endpoint must expose merchant context and simulation status."""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "MITRA"
    assert data["simulation_mode"] is True
    assert "merchant_profile" in data
    assert data["merchant_profile"]["merchant_id"] == "MID-DELHI-98234"
    assert data["guardrails_enforced"] is True
