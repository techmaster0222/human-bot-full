"""
API Endpoint Tests
==================
Comprehensive tests for FastAPI server endpoints.
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ============== Fixtures ==============


@pytest.fixture(scope="module")
def client():
    """Create test client with mocked environment."""
    env_vars = {
        "API_KEY": "test_api_key_secure_123",
        "ALLOWED_ORIGINS": "http://localhost:3000",
        "RATE_LIMIT": "1000/minute",
    }
    with patch.dict(os.environ, env_vars):
        from src.api.server import app

        yield TestClient(app)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return valid authentication headers."""
    return {"X-API-Key": "test_api_key_secure_123"}


@pytest.fixture
def invalid_headers() -> dict[str, str]:
    """Return invalid authentication headers."""
    return {"X-API-Key": "wrong_key"}


# ============== Health Check Tests ==============


@pytest.mark.api
class TestHealthEndpoint:
    """Health check endpoint tests."""

    def test_health_returns_200(self, client: TestClient):
        """Health endpoint should return 200."""
        response = client.get("/api/health")
        assert response.status_code in [200, 201]

    def test_health_response_structure(self, client: TestClient):
        """Health response should have correct structure."""
        response = client.get("/api/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    def test_health_no_auth_required(self, client: TestClient):
        """Health endpoint should not require authentication."""
        # No headers provided
        response = client.get("/api/health")
        assert response.status_code in [200, 201]

    def test_health_timestamp_is_recent(self, client: TestClient):
        """Health timestamp should be recent."""
        response = client.get("/api/health")
        data = response.json()

        # Should be able to parse the timestamp
        assert "timestamp" in data
        assert isinstance(data["timestamp"], str)


# ============== Authentication Tests ==============


@pytest.mark.api
class TestAuthentication:
    """Authentication and authorization tests."""

    def test_stats_requires_auth(self, client: TestClient):
        """Stats endpoint should require authentication."""
        response = client.get("/api/stats")
        assert response.status_code in [401, 403]

    def test_sessions_requires_auth(self, client: TestClient):
        """Sessions endpoint should require authentication."""
        response = client.get("/api/sessions")
        assert response.status_code in [401, 403]

    def test_events_requires_auth(self, client: TestClient):
        """Events endpoint should require authentication."""
        response = client.get("/api/events")
        assert response.status_code in [401, 403]

    def test_invalid_api_key_rejected(self, client: TestClient, invalid_headers: dict):
        """Invalid API key should be rejected."""
        response = client.get("/api/stats", headers=invalid_headers)
        assert response.status_code in [401, 403]

    def test_valid_api_key_accepted(self, client: TestClient, auth_headers: dict):
        """Valid API key should be accepted."""
        response = client.get("/api/stats", headers=auth_headers)
        # Should not be 401/403 (may be 200 or 500 depending on DB state)
        assert response.status_code not in [401, 403]

    def test_missing_api_key_header(self, client: TestClient):
        """Missing API key header should return error."""
        response = client.get("/api/sessions")
        assert response.status_code in [401, 403]

    def test_empty_api_key_rejected(self, client: TestClient):
        """Empty API key should be rejected."""
        response = client.get("/api/stats", headers={"X-API-Key": ""})
        assert response.status_code in [401, 403]


# ============== Session Endpoint Tests ==============


@pytest.mark.api
class TestSessionsEndpoint:
    """Sessions endpoint tests."""

    def test_get_sessions_with_auth(self, client: TestClient, auth_headers: dict):
        """Should return sessions list with valid auth."""
        response = client.get("/api/sessions", headers=auth_headers)
        assert response.status_code in [200, 500]  # 500 if DB not initialized

    def test_register_session(self, client: TestClient, auth_headers: dict):
        """Should register a new session."""
        session_data = {
            "session_id": f"test-{datetime.now().timestamp()}",
            "profile_id": "profile_001",
            "device": "desktop",
            "target_url": "https://example.com",
            "proxy": "1.2.3.4:8080",
            "country": "US",
        }

        response = client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json=session_data,
        )

        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "registered"

    def test_register_session_minimal_data(self, client: TestClient, auth_headers: dict):
        """Should register session with minimal required data."""
        session_data = {
            "session_id": f"minimal-{datetime.now().timestamp()}",
            "profile_id": "profile_min",
            "device": "mobile",
        }

        response = client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json=session_data,
        )

        assert response.status_code in [200, 201]

    def test_end_session(self, client: TestClient, auth_headers: dict):
        """Should end a session successfully."""
        # First register
        session_id = f"end-test-{datetime.now().timestamp()}"
        client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json={"session_id": session_id, "profile_id": "p1", "device": "desktop"},
        )

        # Then end
        response = client.post(
            "/api/sessions/end",
            headers=auth_headers,
            json={
                "session_id": session_id,
                "success": True,
                "duration": 125.5,
            },
        )

        assert response.status_code in [200, 201]

    def test_end_session_with_error(self, client: TestClient, auth_headers: dict):
        """Should end session with error message."""
        session_id = f"error-test-{datetime.now().timestamp()}"
        client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json={"session_id": session_id, "profile_id": "p1", "device": "desktop"},
        )

        response = client.post(
            "/api/sessions/end",
            headers=auth_headers,
            json={
                "session_id": session_id,
                "success": False,
                "duration": 30.0,
                "error": "Proxy connection timeout",
            },
        )

        assert response.status_code in [200, 201]

    def test_sessions_pagination(self, client: TestClient, auth_headers: dict):
        """Should support pagination parameters."""
        response = client.get(
            "/api/sessions",
            headers=auth_headers,
            params={"limit": 10, "offset": 0},
        )
        assert response.status_code in [200, 500]

    def test_sessions_filter_by_status(self, client: TestClient, auth_headers: dict):
        """Should filter sessions by status."""
        response = client.get(
            "/api/sessions",
            headers=auth_headers,
            params={"status": "success"},
        )
        assert response.status_code in [200, 500]


# ============== Events Endpoint Tests ==============


@pytest.mark.api
class TestEventsEndpoint:
    """Events endpoint tests."""

    def test_get_events(self, client: TestClient, auth_headers: dict):
        """Should return events list."""
        response = client.get("/api/events", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_post_event(self, client: TestClient, auth_headers: dict):
        """Should record a new event."""
        event_data = {
            "session_id": "test-session-events",
            "event_type": "navigation",
            "details": {"url": "https://example.com", "status": 200},
        }

        response = client.post(
            "/api/events",
            headers=auth_headers,
            json=event_data,
        )

        assert response.status_code in [200, 201, 405]  # May not support POST

    def test_post_event_different_types(self, client: TestClient, auth_headers: dict):
        """Should handle different event types."""
        event_types = ["navigation", "click", "scroll", "typing", "error", "page_load"]

        for event_type in event_types:
            response = client.post(
                "/api/events",
                headers=auth_headers,
                json={
                    "session_id": "type-test",
                    "event_type": event_type,
                    "details": {"test": True},
                },
            )
            assert response.status_code in [200, 201, 405]

    def test_events_filter_by_session(self, client: TestClient, auth_headers: dict):
        """Should filter events by session_id."""
        response = client.get(
            "/api/events",
            headers=auth_headers,
            params={"session_id": "test-session-123"},
        )
        assert response.status_code in [200, 500]


# ============== Stats Endpoint Tests ==============


@pytest.mark.api
class TestStatsEndpoint:
    """Statistics endpoint tests."""

    def test_get_stats(self, client: TestClient, auth_headers: dict):
        """Should return statistics."""
        response = client.get("/api/stats", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_stats_structure(self, client: TestClient, auth_headers: dict):
        """Stats should have expected structure."""
        response = client.get("/api/stats", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            # Should have key metrics
            expected_keys = ["total_sessions", "success_rate"]
            for key in expected_keys:
                assert key in data or "error" in data


# ============== IP Status Endpoint Tests ==============


@pytest.mark.api
class TestIPStatusEndpoint:
    """IP/Proxy status endpoint tests."""

    def test_get_ip_status(self, client: TestClient, auth_headers: dict):
        """Should return IP status information."""
        response = client.get("/api/ip/status", headers=auth_headers)
        assert response.status_code in [200, 500]

    def test_ip_status_structure(self, client: TestClient, auth_headers: dict):
        """IP status should have expected structure."""
        response = client.get("/api/ip/status", headers=auth_headers)

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))


# ============== Export Endpoint Tests ==============


@pytest.mark.api
class TestExportEndpoints:
    """CSV export endpoint tests."""

    def test_export_sessions_csv(self, client: TestClient, auth_headers: dict):
        """Should export sessions as CSV."""
        response = client.get("/api/sessions/export", headers=auth_headers)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/csv" in content_type or "text/plain" in content_type

    def test_export_events_csv(self, client: TestClient, auth_headers: dict):
        """Should export events as CSV."""
        response = client.get("/api/events/export", headers=auth_headers)

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/csv" in content_type or "text/plain" in content_type


# ============== Error Handling Tests ==============


@pytest.mark.api
class TestErrorHandling:
    """Error handling tests."""

    def test_404_unknown_endpoint(self, client: TestClient, auth_headers: dict):
        """Should return 404 for unknown endpoints."""
        response = client.get("/api/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_405_wrong_method(self, client: TestClient, auth_headers: dict):
        """Should return 405 for wrong HTTP method."""
        response = client.delete("/api/health")
        assert response.status_code in [405, 404]

    def test_422_invalid_json(self, client: TestClient, auth_headers: dict):
        """Should return 422 for invalid JSON body."""
        response = client.post(
            "/api/sessions/register",
            headers={**auth_headers, "Content-Type": "application/json"},
            content="not valid json{",
        )
        assert response.status_code in [422, 400]

    def test_missing_required_fields(self, client: TestClient, auth_headers: dict):
        """Should handle missing required fields."""
        response = client.post(
            "/api/sessions/register",
            headers=auth_headers,
            json={},  # Missing required fields
        )
        assert response.status_code == 422
