import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.auth import get_current_user

# Mocking the authenticated user
def mock_get_current_user():
    return "test-user-123"

# Override the dependency globally for tests
app.dependency_overrides[get_current_user] = mock_get_current_user

# Global client with lifespan support
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check_endpoint(client):
    """Verify that the system health subsystem is operational."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "subsystems" in data

def test_authenticated_api_zones(client):
    """Verify that the /api/zones route works with mocked auth."""
    # Since we overrode get_current_user, this should work without a real token
    response = client.get("/api/zones")
    assert response.status_code == 200
    data = response.json()
    assert "zones" in data
    assert "match_phase" in data

def test_simulation_override(client):
    """Verify that the simulator can be updated via the API."""
    payload = {
        "theme": "marathon",
        "situation": "busy_peak",
        "severity": "high"
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["theme"] == "marathon"

def test_prediction_endpoint(client):
    """Verify that wait-time predictions are accessible."""
    # Fixed: Use correct GET endpoint from routers/predict.py
    # Route is /api/predict/{zone_id}
    response = client.get("/api/predict/hall_1")
    assert response.status_code == 200
    data = response.json()
    assert "predicted_wait_minutes" in data
    assert "zone_id" in data

def test_graph_endpoint(client):
    """Verify that the venue knowledge graph can be retrieved."""
    response = client.get("/api/graph")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

def test_api_docs_availability(client):
    """Verify that Swagger documentation is generated correctly."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text
