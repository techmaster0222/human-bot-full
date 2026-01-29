# Development Guide

## Setup

```bash
# Clone and setup
cd /opt/project/ads_project
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium
```

## Project Structure

```
src/
├── api/           # FastAPI server
├── adspower/      # Browser automation
├── behavior/      # Human simulation
├── bot/           # Session management
├── proxy/         # Proxy handling
└── core/          # Orchestration
```

---

## Testing

### Test Suite Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_api.py          # API endpoint tests
├── test_behavior.py     # Behavior module tests
├── test_config.py       # Configuration tests
└── test_proxy.py        # Proxy management tests
```

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run fast tests (skip slow/integration)
pytest tests/ -v -m "not slow and not integration"

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test class
pytest tests/test_proxy.py::TestIPRoyalProxy -v
```

### Using Makefile Commands

```bash
make test           # Run all tests
make test-fast      # Skip slow tests
make test-cov       # Generate coverage report
make test-integration  # Run integration tests only
```

### Writing New Tests

#### Basic Test Structure

```python
# tests/test_my_module.py
import pytest
from src.my_module import MyClass

class TestMyClass:
    """Tests for MyClass."""
    
    @pytest.fixture
    def my_instance(self):
        """Create test instance."""
        return MyClass(config="test")
    
    def test_basic_functionality(self, my_instance):
        """Test basic method works."""
        result = my_instance.do_something()
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_async_method(self, my_instance):
        """Test async method."""
        result = await my_instance.async_operation()
        assert result == "expected"
```

#### Using Fixtures from conftest.py

```python
def test_with_mock_page(mock_page):
    """Test using shared mock_page fixture."""
    # mock_page is a pre-configured AsyncMock
    assert mock_page.goto is not None

def test_with_temp_db(temp_db):
    """Test using temporary database."""
    # temp_db is a path to a temporary SQLite file
    db = DatabaseLogger(db_path=temp_db)
    assert db is not None

def test_api_client(api_client, auth_headers):
    """Test using FastAPI test client."""
    response = api_client.get("/api/health")
    assert response.status_code == 200
```

#### Test Markers

```python
@pytest.mark.slow
def test_long_running():
    """This test takes a while."""
    pass

@pytest.mark.integration
def test_full_flow():
    """Requires external services."""
    pass

@pytest.mark.skipif(not FEATURE_AVAILABLE, reason="Feature not available")
def test_optional_feature():
    """Skip if feature not available."""
    pass
```

### CI Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every push and PR:

1. **Lint & Format**: Ruff + Black checks
2. **Python Tests**: Unit tests with coverage
3. **Integration Tests**: Full system tests
4. **Dashboard Build**: TypeScript compilation
5. **Security Scan**: Bandit + Safety

### Code Coverage

```bash
# Generate HTML coverage report
make test-cov

# View report
open htmlcov/index.html
```

Coverage targets:
- **src/api/**: 85%+
- **src/proxy/**: 90%+
- **src/behavior/**: 75%+

---

## Adding New Behaviors

1. Create file in `src/behavior/`:

```python
# src/behavior/my_behavior.py
class MyBehavior:
    async def execute(self, page):
        # Your logic
        pass
```

2. Export in `src/behavior/__init__.py`
3. Use in `src/bot/actions.py`

---

## Adding Proxy Providers

1. Create `src/proxy/my_provider.py`:

```python
class MyProvider:
    def get_proxy(self, country: str) -> ProxyConfig:
        return ProxyConfig(
            host="proxy.example.com",
            port=8080,
            username=self.username,
            password=self.password
        )
```

2. Export in `src/proxy/__init__.py`

---

## Adding API Endpoints

```python
# In src/api/server.py
@app.get("/api/my-endpoint")
async def my_endpoint(api_key: str = Depends(verify_api_key)):
    return {"data": "value"}
```

---

## Code Quality

```bash
# Lint
make lint

# Format
make format

# All checks
make check
```

---

## Debugging

```python
from loguru import logger

logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

Check logs:
```bash
tail -f logs/api_events.log
```

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API.md](./API.md) - API reference
- [PROJECT_REPORT.md](./PROJECT_REPORT.md) - Full project report

---

*Last updated: January 2026*
