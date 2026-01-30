# Human Bot Engine

A production-ready bot automation framework with AdsPower browser fingerprinting, IPRoyal proxy rotation, and human-like behavior simulation.

## Features

- **Browser Automation**: AdsPower integration with unique fingerprints per session
- **Proxy Management**: IPRoyal residential proxies with intelligent rotation
- **Human Behavior**: Natural mouse movements, typing, scrolling, and timing
- **Real-time Dashboard**: React + TypeScript dashboard with WebSocket updates
- **Session Tracking**: SQLite-based event logging and statistics
- **IP Health Monitoring**: Automatic proxy scoring and blacklisting

## Project Structure

```
ads_project/
├── src/
│   ├── adspower/       # AdsPower browser management
│   ├── api/            # FastAPI backend + WebSocket
│   ├── bot/            # Bot actions and human behavior
│   ├── proxy/          # IPRoyal proxy management
│   └── core/           # Configuration and orchestration
├── dashboard/          # React + TypeScript frontend
├── scripts/            # Startup scripts
├── config/             # YAML configuration
├── data/               # SQLite databases
└── logs/               # Application logs
```

## Quick Start

### Prerequisites

1. **Python 3.10+**
2. **Node.js 18+** (for dashboard)
3. **AdsPower** browser running locally
4. **IPRoyal** account with residential proxies

### Installation

```bash
# Clone and enter project
cd ads_project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
playwright install chromium

# Install dashboard dependencies
cd dashboard && npm install && cd ..
```

### Configuration

1. Copy environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:
```env
ADSPOWER_API_URL=http://localhost:50325
ADSPOWER_API_KEY=your_api_key

IPROYAL_USERNAME=your_username
IPROYAL_PASSWORD=your_password
```

3. Review `config/settings.yaml` for additional options.

### Running

**Start API Server** (required):
```bash
./scripts/start_api.sh
# API available at http://localhost:8000
```

**Start Dashboard** (optional):
```bash
./scripts/start_dashboard.sh
# Dashboard at http://localhost:3000
```

**Start AdsPower** (VPS):
```bash
./start_adspower.sh
```

## Usage

### Basic Bot Session

```python
import asyncio
from src.api import get_tracker

tracker = get_tracker(use_local=True)

# Start a tracked session
session_id = tracker.start_session(
    profile_id="my_profile",
    proxy="geo.iproyal.com:12321",
    country="US"
)

# Your bot logic here...

# End session (automatically tracks proxy stats)
tracker.end_session(session_id, success=True)
```

### Running Bot Detection Test

```bash
python my_test.py
```

### Using the Orchestrator

```python
from src.core import load_config, BotOrchestrator
from src.bot import BotSession

config = load_config()

async def my_task(session: BotSession):
    await session.visit_page("https://example.com")
    await session.simulate_reading(2000)
    await session.scroll("down")

# Run with orchestrator (see main.py for full examples)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/sessions` | GET | List sessions |
| `/api/stats` | GET | Statistics |
| `/api/events` | GET | Event log |
| `/api/ip/status` | GET | Proxy health |
| `/ws` | WS | Real-time updates |

## Dashboard Features

- **Stats Cards**: Total/Active/Success/Failed sessions
- **Activity Chart**: Session timeline with Recharts
- **Session List**: Real-time session monitoring
- **IP Status**: Proxy health tracking (Healthy/Flagged/Blacklisted)
- **WebSocket**: Live updates without polling

## Proxy Health Logic

| Status | Condition |
|--------|-----------|
| Healthy | Success rate ≥ 80% |
| Flagged | Success rate 50-80% |
| Blacklisted | Success rate < 50% OR disabled |

Proxies are auto-disabled after 3 consecutive failures with a 30-minute cooldown.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADSPOWER_API_URL` | AdsPower local API | `http://localhost:50325` |
| `ADSPOWER_API_KEY` | AdsPower API key | - |
| `IPROYAL_USERNAME` | IPRoyal username | - |
| `IPROYAL_PASSWORD` | IPRoyal password | - |
| `IPROYAL_HOST` | Proxy host | `geo.iproyal.com` |
| `IPROYAL_PORT` | Proxy port | `12321` |

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
make test

# Run fast tests (skip slow/integration)
make test-fast

# Run with coverage report
make test-cov

# Bot detection test (requires AdsPower)
python my_test.py

# Dashboard monitoring test (10 sessions)
python run_10_sessions.py
```

### Code Quality

```bash
# Run linter
make lint

# Format code
make format

# Run all checks (lint + format)
make check
```

### Building Dashboard

```bash
cd dashboard
npm run build
```

### Checking Logs

```bash
tail -f logs/api_events.log
```

### CI/CD

GitHub Actions runs automatically on push/PR:
- Linting (Ruff + Black)
- Unit tests (pytest)
- Integration tests
- Dashboard build
- Security scans

## Extending the Project

### Adding New Behaviors

1. Create a new file in `src/behavior/`:

```python
# src/behavior/my_behavior.py
class MyBehavior:
    async def do_something(self, page):
        # Your behavior logic
        pass
```

2. Export from `src/behavior/__init__.py`
3. Use in `src/bot/actions.py`

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for detailed examples.

### Adding New Proxy Providers

1. Create `src/proxy/my_provider.py`
2. Implement `get_proxy()` and `get_sticky_proxy()` methods
3. Export from `src/proxy/__init__.py`

### Adding API Endpoints

1. Define Pydantic models in `src/api/server.py`
2. Add endpoint with `@app.get()` or `@app.post()`
3. Add authentication with `Depends(verify_api_key)`

## Documentation

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Quick start guide (this file) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture with diagrams |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development guide & extending |
| [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) | Full project report |

## API Documentation

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## License

Private - All rights reserved.
