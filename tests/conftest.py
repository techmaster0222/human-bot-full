"""
Pytest Configuration and Fixtures
================================
Shared fixtures for all test modules.
"""

import asyncio
import os
import sqlite3
import tempfile
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ============== Event Loop ==============


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============== Environment ==============


@pytest.fixture(scope="session")
def test_env() -> Generator[dict[str, str], None, None]:
    """Set up test environment variables."""
    env_vars = {
        "ADSPOWER_API_URL": "http://localhost:50325",
        "ADSPOWER_API_KEY": "test_api_key_12345",
        "IPROYAL_USERNAME": "test_proxy_user",
        "IPROYAL_PASSWORD": "test_proxy_pass",
        "IPROYAL_HOST": "geo.iproyal.com",
        "IPROYAL_PORT": "12321",
        "API_KEY": "test_dashboard_api_key",
        "ALLOWED_ORIGINS": "http://localhost:3000,http://localhost:5173",
        "RATE_LIMIT": "1000/minute",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


# ============== Database ==============


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except (FileNotFoundError, PermissionError):
        pass


@pytest.fixture
def db_connection(temp_db: str) -> Generator[sqlite3.Connection, None, None]:
    """Create database connection with test schema."""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row

    # Create test tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            profile_id TEXT,
            device TEXT,
            target_url TEXT,
            proxy TEXT,
            country TEXT,
            start_time TEXT,
            end_time TEXT,
            duration REAL,
            success INTEGER,
            error TEXT,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_type TEXT,
            timestamp TEXT,
            details TEXT
        );

        CREATE TABLE IF NOT EXISTS proxy_stats (
            proxy_id TEXT PRIMARY KEY,
            country TEXT,
            success_count INTEGER DEFAULT 0,
            failure_count INTEGER DEFAULT 0,
            total_latency_ms REAL DEFAULT 0,
            last_used TEXT,
            is_disabled INTEGER DEFAULT 0,
            cooldown_until TEXT
        );
    """)
    conn.commit()

    yield conn
    conn.close()


# ============== Mock Page (Playwright) ==============


@pytest.fixture
def mock_page() -> AsyncMock:
    """Create comprehensive mock Playwright page."""
    page = AsyncMock()

    # Navigation
    page.goto = AsyncMock(return_value=None)
    page.reload = AsyncMock(return_value=None)
    page.go_back = AsyncMock(return_value=None)
    page.go_forward = AsyncMock(return_value=None)
    page.wait_for_load_state = AsyncMock(return_value=None)
    page.wait_for_selector = AsyncMock(return_value=AsyncMock())
    page.wait_for_timeout = AsyncMock(return_value=None)

    # Properties
    page.url = "https://example.com/test"
    page.title = AsyncMock(return_value="Test Page Title")
    page.content = AsyncMock(return_value="<html><body><h1>Test</h1></body></html>")

    # Selectors
    mock_element = AsyncMock()
    mock_element.click = AsyncMock()
    mock_element.fill = AsyncMock()
    mock_element.type = AsyncMock()
    mock_element.press = AsyncMock()
    mock_element.scroll_into_view_if_needed = AsyncMock()
    mock_element.bounding_box = AsyncMock(
        return_value={"x": 100, "y": 200, "width": 150, "height": 40}
    )
    mock_element.is_visible = AsyncMock(return_value=True)
    mock_element.is_enabled = AsyncMock(return_value=True)
    mock_element.text_content = AsyncMock(return_value="Button Text")
    mock_element.get_attribute = AsyncMock(return_value="attribute_value")
    mock_element.inner_text = AsyncMock(return_value="Inner Text")

    page.query_selector = AsyncMock(return_value=mock_element)
    page.query_selector_all = AsyncMock(return_value=[mock_element, mock_element])
    page.locator = MagicMock(
        return_value=AsyncMock(
            first=mock_element,
            click=AsyncMock(),
            fill=AsyncMock(),
            is_visible=AsyncMock(return_value=True),
            is_enabled=AsyncMock(return_value=True),
        )
    )

    # Input
    page.keyboard = AsyncMock()
    page.keyboard.type = AsyncMock()
    page.keyboard.press = AsyncMock()
    page.keyboard.down = AsyncMock()
    page.keyboard.up = AsyncMock()

    page.mouse = AsyncMock()
    page.mouse.move = AsyncMock()
    page.mouse.click = AsyncMock()
    page.mouse.down = AsyncMock()
    page.mouse.up = AsyncMock()
    page.mouse.wheel = AsyncMock()

    # Evaluation
    page.evaluate = AsyncMock(return_value={"result": "success"})
    page.evaluate_handle = AsyncMock()

    # Screenshots
    page.screenshot = AsyncMock(return_value=b"fake_screenshot_data")
    page.pdf = AsyncMock(return_value=b"fake_pdf_data")

    # Viewport
    page.viewport_size = {"width": 1920, "height": 1080}
    page.set_viewport_size = AsyncMock()

    # Close
    page.close = AsyncMock()
    page.is_closed = MagicMock(return_value=False)

    return page


@pytest.fixture
def mock_element() -> AsyncMock:
    """Create mock Playwright element."""
    element = AsyncMock()
    element.click = AsyncMock()
    element.fill = AsyncMock()
    element.type = AsyncMock()
    element.press = AsyncMock()
    element.scroll_into_view_if_needed = AsyncMock()
    element.bounding_box = AsyncMock(return_value={"x": 100, "y": 200, "width": 150, "height": 40})
    element.is_visible = AsyncMock(return_value=True)
    element.is_enabled = AsyncMock(return_value=True)
    element.text_content = AsyncMock(return_value="Element Text")
    element.get_attribute = AsyncMock(return_value="href_value")
    return element


# ============== Mock Browser ==============


@pytest.fixture
def mock_browser() -> AsyncMock:
    """Create mock Playwright browser."""
    browser = AsyncMock()

    context = AsyncMock()
    page = AsyncMock()

    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()
    browser.is_connected = MagicMock(return_value=True)

    return browser


# ============== API Test Fixtures ==============


@pytest.fixture
def auth_headers(test_env: dict[str, str]) -> dict[str, str]:
    """Return authentication headers for API tests."""
    return {"X-API-Key": test_env["API_KEY"]}


@pytest.fixture
def sample_session() -> dict[str, Any]:
    """Return sample session data."""
    return {
        "session_id": f"test-session-{datetime.now().timestamp()}",
        "profile_id": "profile_test_001",
        "device": "desktop",
        "target_url": "https://example.com",
        "proxy": "192.168.1.100:8080",
        "country": "US",
    }


@pytest.fixture
def sample_event() -> dict[str, Any]:
    """Return sample event data."""
    return {
        "session_id": "test-session-123",
        "event_type": "navigation",
        "details": {"url": "https://example.com/page", "status": 200, "load_time_ms": 1250},
    }


@pytest.fixture
def sample_sessions_batch() -> list[dict[str, Any]]:
    """Return batch of sample sessions for testing."""
    countries = ["US", "UK", "DE", "FR", "JP"]
    devices = ["desktop", "mobile"]

    sessions = []
    for i in range(10):
        sessions.append(
            {
                "session_id": f"batch-session-{i}",
                "profile_id": f"profile_{i}",
                "device": devices[i % 2],
                "target_url": f"https://site{i}.com",
                "proxy": f"192.168.1.{100 + i}:8080",
                "country": countries[i % len(countries)],
            }
        )
    return sessions


# ============== Proxy Fixtures ==============


@pytest.fixture
def proxy_config() -> dict[str, Any]:
    """Return sample proxy configuration."""
    return {
        "host": "geo.iproyal.com",
        "port": 12321,
        "username": "test_user",
        "password": "test_pass",
        "country": "US",
    }


@pytest.fixture
def proxy_stats_data() -> list[dict[str, Any]]:
    """Return sample proxy statistics."""
    return [
        {"proxy_id": "proxy_1", "country": "US", "success_count": 95, "failure_count": 5},
        {"proxy_id": "proxy_2", "country": "UK", "success_count": 88, "failure_count": 12},
        {"proxy_id": "proxy_3", "country": "DE", "success_count": 100, "failure_count": 0},
        {"proxy_id": "proxy_4", "country": "US", "success_count": 50, "failure_count": 50},
        {"proxy_id": "proxy_5", "country": "JP", "success_count": 10, "failure_count": 90},
    ]


# ============== Time Fixtures ==============


@pytest.fixture
def frozen_time():
    """Fixture for time-based tests."""
    return datetime(2026, 1, 30, 12, 0, 0)


@pytest.fixture
def time_range():
    """Return time range for filtering tests."""
    now = datetime.now()
    return {
        "start": now - timedelta(hours=24),
        "end": now,
    }


# ============== Markers ==============


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, dependencies)")
    config.addinivalue_line("markers", "slow: Slow tests (skip with -m 'not slow')")
    config.addinivalue_line("markers", "api: API endpoint tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "proxy: Proxy-related tests")
    config.addinivalue_line("markers", "bot: Bot behavior tests")
    config.addinivalue_line("markers", "async_test: Async tests")
