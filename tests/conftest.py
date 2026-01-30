"""Pytest fixtures for all test modules."""

import asyncio
import os
import tempfile
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    env_vars = {
        "ADSPOWER_API_URL": "http://localhost:50325",
        "ADSPOWER_API_KEY": "test_api_key",
        "IPROYAL_USERNAME": "test_user",
        "IPROYAL_PASSWORD": "test_pass",
        "IPROYAL_HOST": "geo.iproyal.com",
        "IPROYAL_PORT": "12321",
        "API_KEY": "test_api_key_for_testing",
        "ALLOWED_ORIGINS": "http://localhost:3000",
        "RATE_LIMIT": "1000/minute",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_page():
    """Create mock Playwright page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.query_selector = AsyncMock(return_value=AsyncMock())
    page.evaluate = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_data")
    page.content = AsyncMock(return_value="<html><body>Test</body></html>")
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Test Page")
    page.keyboard = AsyncMock()
    page.keyboard.type = AsyncMock()
    page.keyboard.press = AsyncMock()
    page.mouse = AsyncMock()
    page.mouse.move = AsyncMock()
    page.mouse.click = AsyncMock()
    page.mouse.wheel = AsyncMock()
    return page


@pytest.fixture
def mock_element():
    """Create mock Playwright element."""
    element = AsyncMock()
    element.click = AsyncMock()
    element.fill = AsyncMock()
    element.scroll_into_view_if_needed = AsyncMock()
    element.bounding_box = AsyncMock(return_value={"x": 100, "y": 100, "width": 50, "height": 20})
    element.is_visible = AsyncMock(return_value=True)
    return element


@pytest.fixture
def auth_headers(test_env):
    """Return authentication headers."""
    return {"X-API-Key": test_env["API_KEY"]}


@pytest.fixture
def sample_session():
    """Return sample session data."""
    return {
        "session_id": "test-session-123",
        "profile_id": "profile_1",
        "device": "desktop",
        "target_url": "https://example.com",
        "proxy": "1.2.3.4:12321",
        "country": "US",
    }


@pytest.fixture
def sample_event():
    """Return sample event data."""
    return {
        "session_id": "test-session-123",
        "event_type": "navigation",
        "details": {"url": "https://example.com"},
    }
