# Development Guide

> How to extend, customize, and contribute to the AdsPower Bot Engine

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Adding New Behaviors](#adding-new-behaviors)
4. [Adding New Proxy Providers](#adding-new-proxy-providers)
5. [Creating Custom Bot Actions](#creating-custom-bot-actions)
6. [Extending the API](#extending-the-api)
7. [Adding Dashboard Components](#adding-dashboard-components)
8. [Testing](#testing)
9. [Code Style](#code-style)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Development Setup

```bash
# Clone the repository
cd /opt/project/ads_project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (including dev)
pip install -r requirements.txt
pip install pytest pytest-asyncio black flake8

# Install Playwright browsers
playwright install chromium

# Install dashboard dependencies
cd dashboard && npm install && cd ..
```

### Running in Development Mode

```bash
# Terminal 1: API Server (with auto-reload)
cd /opt/project/ads_project
source venv/bin/activate
uvicorn src.api.server:app --reload --port 8000

# Terminal 2: Dashboard (with hot reload)
cd /opt/project/ads_project/dashboard
npm run dev
```

---

## Project Structure

```
src/
├── adspower/      # Browser management (AdsPower API)
├── api/           # FastAPI backend
├── behavior/      # Human behavior algorithms ← ADD NEW BEHAVIORS HERE
├── bot/           # High-level bot actions
├── core/          # Configuration & orchestration
├── proxy/         # Proxy management ← ADD NEW PROVIDERS HERE
├── reputation/    # Proxy scoring system
├── events/        # Event system
└── session/       # Session management
```

---

## Adding New Behaviors

### Step 1: Create the Behavior Module

Create a new file in `src/behavior/`:

```python
# src/behavior/typing_advanced.py
"""
Advanced Typing Behavior
========================
Simulates more realistic typing patterns with:
- Variable speed based on character type
- Fatigue simulation
- Language-specific patterns
"""

import random
import asyncio
from typing import Optional
from loguru import logger


class AdvancedTyping:
    """Advanced human-like typing simulation."""
    
    def __init__(
        self,
        base_wpm: int = 60,
        error_rate: float = 0.02,
        fatigue_enabled: bool = True
    ):
        self.base_wpm = base_wpm
        self.error_rate = error_rate
        self.fatigue_enabled = fatigue_enabled
        self.chars_typed = 0
    
    def _get_char_delay(self, char: str, prev_char: Optional[str] = None) -> float:
        """Calculate delay for a character based on typing patterns."""
        # Base delay from WPM (assuming 5 chars per word)
        base_delay = 60 / (self.base_wpm * 5)
        
        # Adjustments based on character type
        if char in '.,!?':
            # Punctuation is slower
            base_delay *= random.uniform(1.2, 1.5)
        elif char == ' ':
            # Space after word, slight pause
            base_delay *= random.uniform(0.8, 1.0)
        elif char.isupper():
            # Shift key adds delay
            base_delay *= random.uniform(1.1, 1.3)
        elif char.isdigit():
            # Numbers require looking at keyboard
            base_delay *= random.uniform(1.2, 1.4)
        
        # Fatigue: typing slows down over time
        if self.fatigue_enabled and self.chars_typed > 100:
            fatigue_factor = 1 + (self.chars_typed - 100) * 0.001
            base_delay *= min(fatigue_factor, 1.5)
        
        # Add random variance
        return base_delay * random.uniform(0.8, 1.2)
    
    def _should_make_typo(self) -> bool:
        """Determine if a typo should be made."""
        return random.random() < self.error_rate
    
    def _get_typo_char(self, intended_char: str) -> str:
        """Get a realistic typo for a character."""
        # QWERTY keyboard neighbors
        neighbors = {
            'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs',
            'e': 'wsdr', 'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yujnbg',
            'i': 'ujko', 'j': 'uikmnh', 'k': 'iolmj', 'l': 'opk',
            'm': 'njk', 'n': 'bhjm', 'o': 'iklp', 'p': 'ol',
            'q': 'wa', 'r': 'edft', 's': 'weadzx', 't': 'rfgy',
            'u': 'yhji', 'v': 'cfgb', 'w': 'qase', 'x': 'zsdc',
            'y': 'tghu', 'z': 'asx'
        }
        
        char_lower = intended_char.lower()
        if char_lower in neighbors:
            typo = random.choice(neighbors[char_lower])
            return typo.upper() if intended_char.isupper() else typo
        return intended_char
    
    async def type_text(self, page, selector: str, text: str):
        """Type text with human-like behavior."""
        element = await page.query_selector(selector)
        if not element:
            logger.warning(f"Element not found: {selector}")
            return
        
        await element.click()
        self.chars_typed = 0
        
        prev_char = None
        i = 0
        while i < len(text):
            char = text[i]
            
            # Maybe make a typo
            if self._should_make_typo() and char.isalpha():
                typo_char = self._get_typo_char(char)
                
                # Type the wrong character
                await page.keyboard.type(typo_char)
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # "Notice" the mistake
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                # Backspace and correct
                await page.keyboard.press('Backspace')
                await asyncio.sleep(random.uniform(0.1, 0.2))
            
            # Type the correct character
            delay = self._get_char_delay(char, prev_char)
            await page.keyboard.type(char)
            await asyncio.sleep(delay)
            
            self.chars_typed += 1
            prev_char = char
            i += 1
        
        logger.debug(f"Typed {self.chars_typed} characters")
```

### Step 2: Export from Package

Update `src/behavior/__init__.py`:

```python
# src/behavior/__init__.py
from .mouse import MouseBehavior, BezierCurve
from .timing import TimingBehavior, gaussian_delay
from .scroll import ScrollBehavior
from .interaction import InteractionBehavior
from .focus import FocusBehavior
from .typing_advanced import AdvancedTyping  # ← Add this

__all__ = [
    'MouseBehavior',
    'BezierCurve',
    'TimingBehavior',
    'gaussian_delay',
    'ScrollBehavior',
    'InteractionBehavior',
    'FocusBehavior',
    'AdvancedTyping',  # ← Add this
]
```

### Step 3: Integrate into Bot Actions

Update `src/bot/actions.py` to use the new behavior:

```python
# In src/bot/actions.py

from src.behavior import AdvancedTyping

class BotActions:
    def __init__(self, page, behavior=None):
        self.page = page
        self.behavior = behavior or HumanBehavior()
        self.advanced_typing = AdvancedTyping()  # ← Add this
    
    async def type_realistic(self, selector: str, text: str):
        """Type text with advanced human-like patterns."""
        await self.advanced_typing.type_text(self.page, selector, text)
```

### Step 4: Use in Your Bot

```python
# In your bot script
from src.bot import BotActions

actions = BotActions(page)
await actions.type_realistic("#search-input", "example search query")
```

---

## Adding New Proxy Providers

### Step 1: Create Provider Module

```python
# src/proxy/brightdata.py
"""
Bright Data Proxy Provider
==========================
Integration with Bright Data (formerly Luminati) proxy service.
"""

from dataclasses import dataclass
from typing import Optional
import random
import string


@dataclass
class BrightDataConfig:
    """Bright Data proxy configuration."""
    host: str
    port: int
    username: str
    password: str
    zone: str = "residential"


class BrightDataProxy:
    """Bright Data proxy provider."""
    
    def __init__(
        self,
        username: str,
        password: str,
        zone: str = "residential",
        host: str = "brd.superproxy.io",
        port: int = 22225
    ):
        self.username = username
        self.password = password
        self.zone = zone
        self.host = host
        self.port = port
    
    def _generate_session_id(self, length: int = 8) -> str:
        """Generate random session ID for sticky sessions."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    def get_proxy(
        self,
        country: Optional[str] = None,
        city: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> tuple[BrightDataConfig, str]:
        """
        Get a proxy configuration.
        
        Args:
            country: Two-letter country code (e.g., "US", "GB")
            city: City name (e.g., "new_york")
            session_id: Session ID for sticky sessions
        
        Returns:
            Tuple of (config, session_id)
        """
        session_id = session_id or self._generate_session_id()
        
        # Build username with options
        user_parts = [f"brd-customer-{self.username}", f"zone-{self.zone}"]
        
        if country:
            user_parts.append(f"country-{country.lower()}")
        if city:
            user_parts.append(f"city-{city.lower()}")
        
        user_parts.append(f"session-{session_id}")
        
        username = "-".join(user_parts)
        
        config = BrightDataConfig(
            host=self.host,
            port=self.port,
            username=username,
            password=self.password,
            zone=self.zone
        )
        
        return config, session_id
    
    def get_proxy_url(self, country: Optional[str] = None) -> str:
        """Get proxy URL string for direct use."""
        config, _ = self.get_proxy(country=country)
        return f"http://{config.username}:{config.password}@{config.host}:{config.port}"
```

### Step 2: Export from Package

```python
# src/proxy/__init__.py
from .iproyal import IPRoyalProxy, ProxyConfig
from .brightdata import BrightDataProxy, BrightDataConfig  # ← Add
from .rotation import ProxyRotator, RotationStrategy
from .stats import ProxyStatsManager
from .session_manager import ProxySessionManager

__all__ = [
    'IPRoyalProxy',
    'ProxyConfig',
    'BrightDataProxy',      # ← Add
    'BrightDataConfig',     # ← Add
    'ProxyRotator',
    'RotationStrategy',
    'ProxyStatsManager',
    'ProxySessionManager',
]
```

### Step 3: Add Configuration

Update `config/settings.yaml`:

```yaml
proxy:
  provider: "iproyal"  # or "brightdata"
  
  iproyal:
    username: ${IPROYAL_USERNAME}
    password: ${IPROYAL_PASSWORD}
    host: geo.iproyal.com
    port: 12321
  
  brightdata:
    username: ${BRIGHTDATA_USERNAME}
    password: ${BRIGHTDATA_PASSWORD}
    zone: residential
    host: brd.superproxy.io
    port: 22225
```

---

## Creating Custom Bot Actions

### Example: Form Filling Action

```python
# src/bot/actions.py (add to existing class)

async def fill_form(self, form_data: dict, submit: bool = True):
    """
    Fill a form with human-like behavior.
    
    Args:
        form_data: Dict mapping selector to value
        submit: Whether to submit the form
    
    Example:
        await actions.fill_form({
            "#name": "John Doe",
            "#email": "john@example.com",
            "#message": "Hello world"
        })
    """
    for selector, value in form_data.items():
        # Random delay between fields
        await self.random_wait(500, 1500)
        
        # Click the field
        await self.click_element(selector)
        await self.random_wait(100, 300)
        
        # Type the value
        await self.type_text(selector, value)
    
    if submit:
        await self.random_wait(500, 1000)
        # Try common submit button selectors
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            '.submit-btn',
            '#submit'
        ]
        for sel in submit_selectors:
            try:
                await self.click_element(sel)
                break
            except:
                continue
```

### Example: CAPTCHA Detection Action

```python
async def check_for_captcha(self) -> bool:
    """
    Check if page contains a CAPTCHA.
    
    Returns:
        True if CAPTCHA detected
    """
    captcha_indicators = [
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
        '.g-recaptcha',
        '.h-captcha',
        '#captcha',
        '[data-captcha]'
    ]
    
    for selector in captcha_indicators:
        element = await self.page.query_selector(selector)
        if element:
            logger.warning(f"CAPTCHA detected: {selector}")
            return True
    
    return False
```

---

## Extending the API

### Adding a New Endpoint

```python
# In src/api/server.py

from pydantic import BaseModel

# 1. Define request/response models
class ProxyTestRequest(BaseModel):
    proxy_url: str
    test_url: str = "https://api.ipify.org?format=json"

class ProxyTestResponse(BaseModel):
    success: bool
    ip: Optional[str] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

# 2. Add the endpoint
@app.post("/api/proxy/test", response_model=ProxyTestResponse)
async def test_proxy(
    request: ProxyTestRequest,
    _: bool = Depends(verify_api_key)
):
    """Test a proxy connection and return the result."""
    import httpx
    import time
    
    try:
        start = time.time()
        async with httpx.AsyncClient(proxy=request.proxy_url, timeout=30) as client:
            response = await client.get(request.test_url)
            latency = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                return ProxyTestResponse(
                    success=True,
                    ip=data.get("ip"),
                    latency_ms=latency
                )
            else:
                return ProxyTestResponse(
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
    except Exception as e:
        return ProxyTestResponse(success=False, error=str(e))
```

### Adding WebSocket Event Types

```python
# In src/api/server.py

# Add new event type
async def broadcast_proxy_alert(proxy_url: str, reason: str):
    """Broadcast proxy alert to all WebSocket clients."""
    await broadcast_event({
        "type": "proxy_alert",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "proxy_url": proxy_url,
            "reason": reason
        }
    })
```

---

## Adding Dashboard Components

### Step 1: Create Component

```tsx
// dashboard/src/components/ProxyTester.tsx
import { useState } from 'react'
import { apiClient } from '../services/api'
import './ProxyTester.css'

interface TestResult {
  success: boolean
  ip?: string
  latency_ms?: number
  error?: string
}

export default function ProxyTester() {
  const [proxyUrl, setProxyUrl] = useState('')
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState<TestResult | null>(null)

  const handleTest = async () => {
    setTesting(true)
    setResult(null)
    
    try {
      const response = await apiClient.testProxy(proxyUrl)
      setResult(response)
    } catch (error) {
      setResult({ success: false, error: 'Request failed' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="proxy-tester">
      <h3>Proxy Tester</h3>
      <div className="tester-form">
        <input
          type="text"
          value={proxyUrl}
          onChange={(e) => setProxyUrl(e.target.value)}
          placeholder="http://user:pass@host:port"
        />
        <button onClick={handleTest} disabled={testing || !proxyUrl}>
          {testing ? 'Testing...' : 'Test Proxy'}
        </button>
      </div>
      
      {result && (
        <div className={`result ${result.success ? 'success' : 'error'}`}>
          {result.success ? (
            <>
              <p>✓ Connected successfully</p>
              <p>IP: {result.ip}</p>
              <p>Latency: {result.latency_ms?.toFixed(0)}ms</p>
            </>
          ) : (
            <p>✗ Failed: {result.error}</p>
          )}
        </div>
      )}
    </div>
  )
}
```

### Step 2: Add API Method

```typescript
// dashboard/src/services/api.ts

async testProxy(proxyUrl: string): Promise<{
  success: boolean
  ip?: string
  latency_ms?: number
  error?: string
}> {
  const response = await this.client.post('/api/proxy/test', {
    proxy_url: proxyUrl
  })
  return response.data
}
```

### Step 3: Add to Dashboard

```tsx
// dashboard/src/components/Dashboard.tsx
import ProxyTester from './ProxyTester'

// In the render:
<div className="dashboard-grid">
  {/* ... existing components ... */}
  <ProxyTester />
</div>
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_proxy.py -v

# Run async tests
pytest tests/test_bot.py -v --asyncio-mode=auto
```

### Writing Tests

```python
# tests/test_behavior.py
import pytest
from src.behavior import AdvancedTyping

class TestAdvancedTyping:
    def test_char_delay_punctuation(self):
        typing = AdvancedTyping(base_wpm=60)
        
        # Punctuation should be slower than letters
        letter_delay = typing._get_char_delay('a')
        punct_delay = typing._get_char_delay('.')
        
        assert punct_delay > letter_delay
    
    def test_typo_generation(self):
        typing = AdvancedTyping(error_rate=1.0)  # Always typo
        
        # Should generate a neighboring key
        typo = typing._get_typo_char('a')
        assert typo in 'sqwz'
    
    @pytest.mark.asyncio
    async def test_type_text(self, mock_page):
        typing = AdvancedTyping()
        await typing.type_text(mock_page, "#input", "test")
        
        # Verify keyboard.type was called
        assert mock_page.keyboard.type.called
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

## Code Style

### Python

- Use **Black** for formatting: `black src/`
- Use **Ruff** for linting: `ruff check src/`
- Use **type hints** for all function signatures
- Use **docstrings** (Google style) for all public functions

```python
def calculate_delay(base: float, variance: float = 0.2) -> float:
    """
    Calculate a delay with random variance.
    
    Args:
        base: Base delay in seconds
        variance: Variance factor (0.0 to 1.0)
    
    Returns:
        Delay in seconds with applied variance
    
    Example:
        >>> delay = calculate_delay(1.0, 0.2)
        >>> 0.8 <= delay <= 1.2
        True
    """
    return base * random.uniform(1 - variance, 1 + variance)
```

### TypeScript

- Use **ESLint** and **Prettier**
- Use **strict TypeScript** mode
- Define interfaces for all data structures

```typescript
interface SessionData {
  id: string
  profileId: string
  status: 'active' | 'completed' | 'failed'
  startTime: string
  endTime?: string
}
```

---

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'src'"

```bash
# Make sure you're in the project root and venv is activated
cd /opt/project/ads_project
source venv/bin/activate

# Or set PYTHONPATH
export PYTHONPATH=/opt/project/ads_project:$PYTHONPATH
```

#### "AdsPower is not running"

```bash
# Start AdsPower (VPS)
./start_adspower.sh

# Check if it's running
curl http://localhost:50325/status
```

#### "API key invalid"

```bash
# Make sure .env files match
cat .env | grep API_KEY
cat dashboard/.env | grep VITE_API_KEY

# They should have the same value
```

#### Dashboard shows "API Disconnected"

1. Check if API is running: `curl http://localhost:8000/api/health`
2. Check browser console for errors
3. Verify CORS settings in `.env`
4. Restart both API and dashboard

### Debug Mode

```python
# Enable debug logging
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="DEBUG")
```

---

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [README.md](../README.md) - Quick start guide

---

*Last updated: January 2026*
