# Project Report

## Executive Summary

**Project**: AdsPower Bot Engine  
**Version**: 1.0.0  
**Date**: January 2026

A browser automation framework combining AdsPower fingerprint browsers with IPRoyal residential proxies for human-like web browsing simulation.

## Architecture

### Components Built

| Layer | Files | Purpose |
|-------|-------|---------|
| Core | 3 | Orchestration, configuration |
| AdsPower | 5 | Browser automation |
| Proxy | 4 | IPRoyal integration |
| Behavior | 5 | Human simulation |
| Bot | 4 | Session management |
| API | 4 | REST API + WebSocket |
| Dashboard | 12 | React monitoring UI |
| Tests | 5 | pytest suite |

### Technology Stack

**Backend**:
- Python 3.10+
- FastAPI + Uvicorn
- SQLite
- Playwright
- WebSockets

**Frontend**:
- React 18 + TypeScript
- Vite
- Recharts
- Axios

**External Services**:
- AdsPower (browser fingerprinting)
- IPRoyal (residential proxies)

## Features Implemented

### Phase 1: Core Infrastructure
- AdsPower API client
- IPRoyal proxy integration
- Configuration management
- Session tracking

### Phase 2: Human Behavior
- Bezier curve mouse movements
- Weibull timing distributions
- Natural scrolling patterns
- Focus/tab simulation

### Phase 3: Monitoring
- REST API with authentication
- Real-time WebSocket updates
- React dashboard
- Session/event logging

### Phase 4: Tests & CI

#### Test Suite Overview

A comprehensive test suite using **pytest** and **pytest-asyncio** was implemented to ensure code quality and prevent regressions.

##### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configuration
├── test_api.py          # API endpoint tests (17 tests)
├── test_behavior.py     # Behavior module tests (9 tests)
├── test_config.py       # Configuration & database tests (10 tests)
└── test_proxy.py        # Proxy management tests (12 tests)
```

##### Test Categories

| Category | Tests | Coverage |
|----------|-------|----------|
| API Endpoints | 17 | Health, Auth, Sessions, Events, Export |
| Proxy Management | 12 | Config, Sessions, IPRoyal integration |
| Configuration | 10 | YAML loading, Database operations |
| Behavior | 9 | Math utilities, Timing, Bezier curves |
| **Total** | **48** | Core functionality |

##### Test Markers

```python
@pytest.mark.slow          # Long-running tests
@pytest.mark.integration   # Integration tests
@pytest.mark.playwright    # Playwright-dependent tests
```

#### GitHub Actions CI Pipeline

Automated CI/CD workflow configured in `.github/workflows/ci.yml`:

```yaml
Jobs:
  1. lint          # Ruff + Black code quality
  2. test-python   # Unit tests with coverage
  3. test-integration  # Integration tests
  4. build-dashboard   # TypeScript/React build
  5. security      # Bandit + Safety scans
  6. all-checks    # Gate for merge
```

##### Pipeline Triggers

- Push to `main`, `master`, `develop`
- Pull requests to these branches

##### Quality Gates

| Check | Tool | Threshold |
|-------|------|-----------|
| Linting | Ruff | No errors |
| Formatting | Black | Consistent style |
| Tests | Pytest | All pass |
| Coverage | pytest-cov | Reported |
| Security | Bandit | No high severity |

#### Development Commands (Makefile)

```bash
# Install dependencies
make install          # Production deps
make install-dev      # Development deps

# Testing
make test             # Run all tests
make test-fast        # Skip slow/integration
make test-cov         # With coverage report

# Code Quality
make lint             # Run linter
make format           # Format code
make check            # All checks
```

#### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Pytest, Black, Ruff, MyPy config |
| `Makefile` | Development commands |
| `requirements-dev.txt` | Test/dev dependencies |
| `.github/workflows/ci.yml` | GitHub Actions |

#### Test Results

```
============ 48 passed, 5 skipped in 1.66s ============

Coverage:
- src/api/        85%
- src/proxy/      90%
- src/behavior/   75%
```

## File Structure

```
ads_project/
├── src/                 # Python source (10 modules)
├── dashboard/           # React frontend
├── tests/               # Test suite
├── scripts/             # Shell scripts
├── docs/                # Documentation
├── config/              # Configuration
├── main.py              # Entry point
├── run_10_sessions.py   # Dashboard test
├── my_test.py           # Bot detection test
├── Makefile             # Dev commands
├── pyproject.toml       # Project config
└── requirements.txt     # Dependencies
```

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/health` | GET | No | Health check |
| `/api/sessions` | GET | Yes | List sessions |
| `/api/sessions/register` | POST | Yes | Register session |
| `/api/sessions/end` | POST | Yes | End session |
| `/api/events` | GET | Yes | List events |
| `/api/events` | POST | Yes | Log event |
| `/api/stats` | GET | Yes | Statistics |
| `/api/ip/status` | GET | Yes | Proxy status |
| `/ws` | WS | No | Real-time updates |

## Security

- API key authentication
- CORS configuration
- Rate limiting (100/min default)
- Environment variable secrets
- .gitignore for sensitive files

## Deployment

### Requirements
- Python 3.10+
- Node.js 18+
- AdsPower installed
- IPRoyal account

### Quick Start
```bash
./scripts/start_all.sh
```

---

## Appendix A: Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ADSPOWER_API_URL` | No | `http://localhost:50325` | AdsPower API URL |
| `ADSPOWER_API_KEY` | Yes | - | AdsPower API key |
| `IPROYAL_USERNAME` | Yes | - | IPRoyal username |
| `IPROYAL_PASSWORD` | Yes | - | IPRoyal password |
| `IPROYAL_HOST` | No | `geo.iproyal.com` | Proxy host |
| `IPROYAL_PORT` | No | `12321` | Proxy port |
| `API_KEY` | No | - | API authentication key |
| `ALLOWED_ORIGINS` | No | `*` | CORS origins |
| `RATE_LIMIT` | No | `100/minute` | Rate limit |

## Appendix B: Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/start_all.sh` | Start API + Dashboard |
| `scripts/start_api.sh` | Start API server only |
| `scripts/start_dashboard.sh` | Start dashboard only |
| `scripts/start_adspower.sh` | Start AdsPower (VPS) |
| `scripts/vps_setup.sh` | VPS initial setup |
| `run_10_sessions.py` | Test 10 bot sessions |
| `my_test.py` | Bot detection test |

## Appendix C: Test Files Reference

| File | Tests | Description |
|------|-------|-------------|
| `tests/conftest.py` | - | Shared fixtures (mock_page, temp_db, api_client) |
| `tests/test_api.py` | 17 | API endpoints (health, auth, sessions, events) |
| `tests/test_behavior.py` | 9 | Behavior algorithms (bezier, timing, math) |
| `tests/test_config.py` | 10 | Configuration and database operations |
| `tests/test_proxy.py` | 12 | Proxy management (IPRoyal, sessions, config) |

## Appendix D: CI/CD Configuration

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | GitHub Actions workflow |
| `pyproject.toml` | Pytest, Black, Ruff, MyPy configuration |
| `Makefile` | Development commands |
| `requirements-dev.txt` | Test/dev dependencies |

---

*Generated: January 2026*
