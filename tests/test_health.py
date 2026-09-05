from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    """
    Test GET /health returns 200 OK with expected JSON structure.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ClaimLens AI"
    assert "timestamp" in data

def test_api_v1_health_endpoint():
    """
    Test GET /api/v1/health returns 200 OK.
    """
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ClaimLens AI"

def test_root_endpoint():
    """
    Test GET / returns 200 OK with welcome message and docs links.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["service"] == "ClaimLens AI"
    assert data["health_url"] == "/health"
