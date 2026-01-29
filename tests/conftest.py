"""Pytest Configuration and Fixtures"""

import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    env_vars = {
        "API_KEY": "test_api_key_123",
        "ALLOWED_ORIGINS": "http://localhost:3000",
        "RATE_LIMIT": "1000/minute",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars

@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass

@pytest.fixture
def mock_page():
    """Create a mock Playwright page object."""
    page = AsyncMock()
    page.goto = AsyncMock(return_value=None)
    page.mouse = AsyncMock()
    page.keyboard = AsyncMock()
    return page

@pytest.fixture
def auth_headers():
    """Return authentication headers."""
    return {"X-API-Key": "test_api_key_123"}
