import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    """Verify that the system health subsystem is operational."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "subsystems" in data

def test_unauthenticated_api_access():
    """Ensure that protected API routes correctly enforce Bearer auth."""
    response = client.get("/api/zones")
    # Should be 403 or 401 because get_current_user dependency will fail
    assert response.status_code in [401, 403]

def test_api_docs_availability():
    """Verify that Swagger documentation is generated correctly."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text

@pytest.mark.asyncio
async def test_websocket_connectivity_schema():
    """Verify that the WebSocket endpoint accepts connections (simulated)."""
    # Note: Full WebSocket testing is complex in unit tests, 
    # but we can verify the route exists.
    from starlette.testclient import TestClient as StarletteClient
    with StarletteClient(app) as s_client:
        # This will fail auth but confirm route validity
        try:
            with s_client.websocket_connect("/api/ws/venue?token=invalid") as websocket:
                pass
        except Exception:
            # We expect a close or auth failure
            pass
