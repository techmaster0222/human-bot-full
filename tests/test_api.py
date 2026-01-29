"""API Endpoint Tests"""

import os
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client():
    os.environ["API_KEY"] = "test_api_key_123"
    os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
    from src.api.server import app
    return TestClient(app)

class TestHealthEndpoint:
    def test_health_check_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_check_response_format(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

class TestAuthentication:
    def test_stats_requires_auth(self, client):
        response = client.get("/api/stats")
        assert response.status_code in [401, 403]

    def test_invalid_api_key_rejected(self, client):
        headers = {"X-API-Key": "wrong_key"}
        response = client.get("/api/stats", headers=headers)
        assert response.status_code == 403
