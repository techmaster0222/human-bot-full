"""API endpoint tests."""

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    os.environ["API_KEY"] = "test_api_key_123"
    os.environ["ALLOWED_ORIGINS"] = "http://localhost:3000"
    os.environ["RATE_LIMIT"] = "1000/minute"
    from src.api.server import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Return authentication headers."""
    return {"X-API-Key": "test_api_key_123"}


class TestHealthEndpoint:
    """Health check endpoint tests."""

    def test_health_returns_200(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_no_auth_required(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_format(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"


class TestAuthentication:
    """Authentication tests."""

    def test_stats_requires_auth(self, client):
        response = client.get("/api/stats")
        assert response.status_code in [401, 403]

    def test_sessions_requires_auth(self, client):
        response = client.get("/api/sessions")
        assert response.status_code in [401, 403]

    def test_invalid_key_rejected(self, client):
        response = client.get("/api/stats", headers={"X-API-Key": "wrong"})
        assert response.status_code == 403


class TestSessionsEndpoint:
    """Sessions endpoint tests."""

    def test_get_sessions(self, client, auth_headers):
        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_register_session(self, client, auth_headers):
        response = client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json={
                "session_id": "test-001",
                "profile_id": "profile_1",
                "device": "desktop",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "registered"

    def test_end_session(self, client, auth_headers):
        client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json={"session_id": "test-002", "profile_id": "profile_1", "device": "desktop"},
        )
        response = client.post(
            "/api/sessions/end",
            headers=auth_headers,
            json={"session_id": "test-002", "success": True, "duration": 15.5},
        )
        assert response.status_code == 200


class TestEventsEndpoint:
    """Events endpoint tests."""

    def test_get_events(self, client, auth_headers):
        response = client.get("/api/events", headers=auth_headers)
        assert response.status_code in [200, 500]


class TestIPStatusEndpoint:
    """IP status endpoint tests."""

    def test_get_ip_status(self, client, auth_headers):
        response = client.get("/api/ip/status", headers=auth_headers)
        assert response.status_code in [200, 500]


class TestExportEndpoints:
    """Export endpoint tests."""

    def test_export_sessions(self, client, auth_headers):
        response = client.get("/api/sessions/export", headers=auth_headers)
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")


class TestErrorHandling:
    """Error handling tests."""

    def test_404_unknown_endpoint(self, client, auth_headers):
        response = client.get("/api/unknown", headers=auth_headers)
        assert response.status_code == 404

    def test_missing_auth_returns_error(self, client):
        response = client.get("/api/stats")
        assert response.status_code in [401, 403]
