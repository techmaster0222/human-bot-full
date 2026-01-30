# Project Report: AdsPower Bot Engine

> Comprehensive documentation of the project development from scratch

**Project Duration**: January 2026  
**Status**: Production Ready  
**Version**: 1.0.0

---

## Executive Summary

The AdsPower Bot Engine is a fully-featured browser automation framework designed for anti-detection web automation. The system integrates AdsPower browser fingerprinting, IPRoyal residential proxies, and sophisticated human behavior simulation with a real-time monitoring dashboard.

### Key Deliverables

| Component | Status | Description |
|-----------|--------|-------------|
| Core Bot Engine | ✅ Complete | Modular automation framework |
| AdsPower Integration | ✅ Complete | Browser fingerprinting & profile management |
| Proxy Management | ✅ Complete | IPRoyal integration with intelligent rotation |
| Human Behavior | ✅ Complete | Natural mouse, typing, scrolling simulation |
| FastAPI Backend | ✅ Complete | REST API with WebSocket support |
| React Dashboard | ✅ Complete | Real-time monitoring UI |
| Security Layer | ✅ Complete | API authentication, CORS, rate limiting |
| Documentation | ✅ Complete | Architecture, development guides |

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Components Built](#3-components-built)
4. [Features Implemented](#4-features-implemented)
5. [Technology Stack](#5-technology-stack)
6. [File Structure](#6-file-structure)
7. [API Reference](#7-api-reference)
8. [Dashboard Features](#8-dashboard-features)
9. [Security Implementation](#9-security-implementation)
10. [Testing & Validation](#10-testing--validation)
11. [Deployment Guide](#11-deployment-guide)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Project Overview

### Purpose

Build a production-grade bot automation system that:
- Avoids detection through browser fingerprinting (AdsPower)
- Routes traffic through residential proxies (IPRoyal)
- Simulates human-like behavior to bypass bot detection
- Provides real-time monitoring and analytics

### Goals Achieved

1. **Anti-Detection**: Unique browser fingerprints per session
2. **Proxy Management**: Intelligent rotation with health scoring
3. **Human Simulation**: Natural movements, typing, and timing
4. **Observability**: Real-time dashboard with WebSocket updates
5. **Scalability**: Modular architecture for easy extension
6. **Security**: API authentication and rate limiting

---

## 2. Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Services                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   AdsPower      │    IPRoyal      │      Target Websites        │
│   Browser API   │    Proxies      │                             │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Python Backend                              │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│   Core      │  AdsPower   │   Proxy     │    Bot      │  API    │
│ Orchestrator│   Client    │  Manager    │   Engine    │ Server  │
├─────────────┴─────────────┴─────────────┴─────────────┴─────────┤
│                    Behavior Simulation Layer                     │
│         (Mouse | Timing | Scroll | Typing | Focus)              │
├─────────────────────────────────────────────────────────────────┤
│                     Data Persistence Layer                       │
│              (SQLite | File Logs | Statistics)                  │
└─────────────────────────────────────────────────────────────────┘
         │
         │ REST API + WebSocket
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     React Dashboard                              │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│ Stats Cards │  Session    │  IP Status  │   Activity Chart      │
│             │    List     │             │                       │
└─────────────┴─────────────┴─────────────┴───────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Each module handles one responsibility
2. **Dependency Injection**: Components are loosely coupled
3. **Event-Driven**: Real-time updates via WebSocket
4. **Fail-Safe**: Graceful degradation on errors
5. **Configurable**: YAML + environment variable configuration

---

## 3. Components Built

### 3.1 Core Module (`src/core/`)

| File | Lines | Purpose |
|------|-------|---------|
| `config.py` | ~200 | Configuration management (YAML + env) |
| `orchestrator.py` | ~150 | Session orchestration |

**Key Features:**
- Loads configuration from `settings.yaml`
- Environment variable substitution
- Pydantic models for validation
- Session lifecycle management

### 3.2 AdsPower Integration (`src/adspower/`)

| File | Lines | Purpose |
|------|-------|---------|
| `client.py` | ~150 | HTTP client for AdsPower API |
| `profile.py` | ~80 | Profile data models |
| `profile_factory.py` | ~100 | Profile creation helpers |
| `controller.py` | ~200 | Browser lifecycle management |
| `browser.py` | ~120 | Playwright connection |

**Key Features:**
- Profile creation with proxy configuration
- Browser start/stop management
- Playwright WebSocket connection
- Automatic cleanup on failure

### 3.3 Proxy Management (`src/proxy/`)

| File | Lines | Purpose |
|------|-------|---------|
| `iproyal.py` | ~100 | IPRoyal proxy configuration |
| `rotation.py` | ~150 | Rotation strategies |
| `stats.py` | ~250 | Health tracking & scoring |
| `session_manager.py` | ~100 | Sticky session management |

**Key Features:**
- Sticky sessions with configurable duration
- Country/city targeting
- Round-robin, weighted, and random rotation
- Automatic health scoring and blacklisting

### 3.4 Bot Engine (`src/bot/`)

| File | Lines | Purpose |
|------|-------|---------|
| `actions.py` | ~300 | High-level bot actions |
| `human_behavior.py` | ~200 | Behavior orchestration |
| `session.py` | ~150 | Session management |

**Key Features:**
- Navigate, click, type, scroll actions
- Screenshot capture
- Form filling
- Element waiting and interaction

### 3.5 Behavior Simulation (`src/behavior/`)

| File | Lines | Purpose |
|------|-------|---------|
| `mouse.py` | ~150 | Bezier curve mouse movements |
| `timing.py` | ~80 | Gaussian-distributed delays |
| `scroll.py` | ~100 | Natural scrolling patterns |
| `interaction.py` | ~120 | Click/hover behaviors |
| `focus.py` | ~80 | Tab focus simulation |

**Key Features:**
- Bezier curve mouse trajectories
- Variable speed based on distance
- Random noise injection
- Fatigue simulation

### 3.6 API Server (`src/api/`)

| File | Lines | Purpose |
|------|-------|---------|
| `server.py` | ~800 | FastAPI application |
| `session_tracker.py` | ~200 | Session tracking |
| `database_logger.py` | ~300 | SQLite persistence |
| `event_logger.py` | ~100 | File logging |

**Key Features:**
- RESTful API endpoints
- WebSocket real-time updates
- API key authentication
- CORS configuration
- Rate limiting (slowapi)
- CSV export

### 3.7 React Dashboard (`dashboard/`)

| File | Lines | Purpose |
|------|-------|---------|
| `Dashboard.tsx` | ~200 | Main layout |
| `StatsCards.tsx` | ~100 | Statistics display |
| `SessionList.tsx` | ~200 | Session list with filters |
| `IPStatus.tsx` | ~150 | Proxy health display |
| `ActivityChart.tsx` | ~100 | Timeline chart |
| `api.ts` | ~150 | API client |
| `websocket.ts` | ~100 | WebSocket client |

**Key Features:**
- Real-time updates via WebSocket
- Filtering and pagination
- CSV export
- Dark/Light theme toggle
- Responsive design

---

## 4. Features Implemented

### 4.1 Session Management

```python
# Start a tracked session
tracker = get_tracker(use_local=True)
session_id = tracker.start_session(
    profile_id="my_profile",
    proxy="1.2.3.4:12321",
    country="US"
)

# Log events during session
tracker.log_navigation(session_id, "https://example.com")
tracker.log_event(session_id, "click", {"element": "#button"})

# End session with result
tracker.end_session(session_id, success=True)
```

### 4.2 Proxy Rotation

```python
# Create proxy manager
proxy = IPRoyalProxy(username="user", password="pass")

# Get sticky session
config, session_id = proxy.get_sticky_proxy(
    country="US",
    duration=600  # 10 minutes
)

# Rotation strategies
rotator = ProxyRotator(proxies, strategy="weighted")
next_proxy = rotator.get_next()
```

### 4.3 Human Behavior

```python
# Mouse movement with Bezier curves
mouse = MouseBehavior()
await mouse.move_to(page, x=500, y=300)

# Natural typing with typos
await actions.type_text("#input", "Hello world")

# Scroll with pauses
await actions.scroll_down(pixels=500)
await actions.random_wait(1000, 2000)
```

### 4.4 Dashboard Monitoring

| Feature | Description |
|---------|-------------|
| Stats Cards | Total, Active, Success, Failed, Rate, Duration |
| Session List | Filterable, searchable, paginated |
| IP Status | Health indicators (Healthy/Flagged/Blacklisted) |
| Real-time | WebSocket updates without polling |
| Export | CSV download with filters |
| Theme | Dark/Light mode toggle |

---

## 5. Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Core language |
| FastAPI | 0.100+ | REST API framework |
| Uvicorn | 0.23+ | ASGI server |
| Playwright | 1.40+ | Browser automation |
| SQLite | 3 | Data persistence |
| Pydantic | 2.0+ | Data validation |
| Loguru | 0.7+ | Structured logging |
| httpx | 0.25+ | Async HTTP client |
| slowapi | 0.1+ | Rate limiting |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2+ | UI framework |
| TypeScript | 5.0+ | Type safety |
| Vite | 5.0+ | Build tool |
| Axios | 1.6+ | HTTP client |
| Recharts | 2.10+ | Charts |
| date-fns | 3.0+ | Date formatting |

### External Services

| Service | Purpose |
|---------|---------|
| AdsPower | Browser fingerprinting |
| IPRoyal | Residential proxies |

---

## 6. File Structure

```
ads_project/
├── src/                          # Python source code
│   ├── __init__.py
│   ├── adspower/                 # AdsPower integration (5 files)
│   ├── api/                      # FastAPI backend (4 files)
│   ├── behavior/                 # Human behavior (5 files)
│   ├── bot/                      # Bot engine (3 files)
│   ├── core/                     # Configuration (2 files)
│   ├── proxy/                    # Proxy management (4 files)
│   ├── reputation/               # Proxy scoring (4 files)
│   ├── events/                   # Event system (4 files)
│   └── session/                  # Session management (4 files)
│
├── dashboard/                    # React frontend
│   ├── src/
│   │   ├── components/           # UI components (5 files)
│   │   ├── services/             # API client (2 files)
│   │   ├── context/              # Theme context
│   │   ├── types/                # TypeScript types
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
│
├── config/
│   └── settings.yaml             # Main configuration
│
├── scripts/
│   ├── start_all.sh              # Start all services
│   ├── start_api.sh              # Start API only
│   └── start_dashboard.sh        # Start dashboard only
│
├── docs/
│   ├── ARCHITECTURE.md           # System architecture
│   ├── DEVELOPMENT.md            # Development guide
│   └── PROJECT_REPORT.md         # This document
│
├── data/                         # SQLite databases
├── logs/                         # Application logs
├── .env                          # Environment variables
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
└── README.md                     # Quick start guide
```

**Total Files**: ~50+ source files  
**Total Lines**: ~5,000+ lines of code

---

## 7. API Reference

### Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | No | Health check |
| GET | `/api/sessions` | Yes | List sessions (paginated) |
| GET | `/api/sessions/{id}` | Yes | Session details |
| POST | `/api/sessions/register` | Yes | Register session |
| POST | `/api/sessions/end` | Yes | End session |
| GET | `/api/sessions/export` | Yes | Export CSV |
| GET | `/api/stats` | Yes | Statistics |
| GET | `/api/events` | Yes | List events (paginated) |
| POST | `/api/events` | Yes | Log event |
| GET | `/api/events/export` | Yes | Export CSV |
| GET | `/api/ip/status` | Yes | Proxy health |
| WS | `/ws` | No | Real-time updates |

### Authentication

```bash
# Header-based authentication
curl -H "X-API-Key: your_key_here" http://localhost:8000/api/stats
```

### Response Examples

```json
// GET /api/stats
{
  "total_sessions": 100,
  "active_sessions": 5,
  "successful_sessions": 85,
  "failed_sessions": 10,
  "success_rate": 85.0,
  "average_duration": 12.5,
  "proxy_stats": [...],
  "ip_health": {
    "healthy": 8,
    "flagged": 2,
    "blacklisted": 1
  }
}

// GET /api/sessions
{
  "sessions": [...],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "total_pages": 5
}
```

---

## 8. Dashboard Features

### Stats Overview

| Card | Metric | Description |
|------|--------|-------------|
| Total Sessions | Count | All-time session count |
| Active Sessions | Count | Currently running |
| Successful | Count | Completed successfully |
| Failed | Count | Ended with error |
| Success Rate | Percentage | Success / Total |
| Avg Duration | Seconds | Average session length |

### Session List

- **Search**: Filter by session ID, profile, proxy
- **Status Filter**: All / Active / Completed / Failed
- **Country Filter**: Dynamic based on data
- **Pagination**: 20 per page, prev/next navigation
- **Export**: Download as CSV with current filters

### IP Status

| Status | Color | Condition |
|--------|-------|-----------|
| Healthy | 🟢 Green | Success rate ≥ 80% |
| Flagged | 🟡 Yellow | Success rate 50-80% |
| Blacklisted | 🔴 Red | Success rate < 50% |

### Real-time Updates

- WebSocket connection at `/ws`
- Events: `session_start`, `session_end`, `event`, `stats_update`
- Auto-reconnect on disconnect
- Status indicator in header

---

## 9. Security Implementation

### API Security

| Layer | Implementation |
|-------|----------------|
| Authentication | `X-API-Key` header |
| CORS | Whitelist in `ALLOWED_ORIGINS` |
| Rate Limiting | `slowapi` (100/minute default) |
| Input Validation | Pydantic models |

### Configuration Security

```env
# .env (not committed to version control)
API_KEY=your_secret_key_here
ALLOWED_ORIGINS=http://localhost:3000
RATE_LIMIT=100/minute
```

### Credential Handling

- Proxy credentials in environment variables
- AdsPower API key in environment variables
- No secrets in code or config files
- `.env.example` as template

---

## 10. Testing & Validation

### Test Script

```bash
# Run 10 bot sessions with real proxies
python run_10_sessions.py
```

### Test Results (Example Run)

```
Session 1: KR → 88.21.190.4 → ✓ Success (8.2s)
Session 2: DE → 187.189.29.135 → ✓ Success (12.4s)
Session 3: SG → 204.175.44.251 → ✓ Success (7.0s)
Session 4: SG → 103.234.203.188 → ✓ Success (10.2s)
Session 5: FR → 2.201.36.112 → ✓ Success (7.3s)
Session 6: CA → 24.201.32.74 → ✗ Failed (CAPTCHA)
Session 7: JP → 96.191.102.162 → ✓ Success (12.8s)
Session 8: JP → 86.127.226.20 → ✓ Success (5.4s)
Session 9: FR → 136.106.67.193 → ✗ Failed (Timeout)
Session 10: US → 165.238.165.14 → ✓ Success (10.5s)

SUMMARY:
- Total: 10
- Successful: 8
- Failed: 2
- Success Rate: 80%
```

### Bot Detection Tests

- `bot.sannysoft.com`: ✓ Passed (webdriver=false)
- `pixelscan.net`: ✓ Passed (no detection)
- `creepjs`: ✓ Passed (fingerprint consistent)

---

## 11. Deployment Guide

### Prerequisites

1. Python 3.10+
2. Node.js 18+
3. AdsPower Browser (running locally)
4. IPRoyal Account

### Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 2. Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd dashboard && npm install && cd ..

# 3. Start all services
./scripts/start_all.sh

# Dashboard: http://localhost:3000
# API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### VPS Deployment

```bash
# Start AdsPower (headless)
./start_adspower.sh

# Start services
./scripts/start_all.sh
```

---

## 12. Future Enhancements

### Potential Additions

| Feature | Priority | Effort |
|---------|----------|--------|
| Multi-provider proxy support | High | Medium |
| CAPTCHA solving integration | High | High |
| Session replay/debugging | Medium | Medium |
| Scheduled task execution | Medium | Medium |
| Distributed execution | Low | High |
| Mobile device emulation | Low | Medium |

### Recommended Next Steps

1. Add more proxy providers (Bright Data, Oxylabs)
2. Integrate CAPTCHA solving (2Captcha, Anti-Captcha)
3. Add session recording for debugging
4. Implement scheduled task runner
5. Add more dashboard visualizations

---

## Phase 4: Tests & CI

### Test Suite Overview

A comprehensive test suite using **pytest** and **pytest-asyncio** was implemented to ensure code quality and prevent regressions.

#### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configuration
├── test_api.py          # API endpoint tests (17 tests)
├── test_behavior.py     # Behavior module tests (9 tests)
├── test_config.py       # Configuration & database tests (10 tests)
└── test_proxy.py        # Proxy management tests (12 tests)
```

#### Test Categories

| Category | Tests | Coverage |
|----------|-------|----------|
| API Endpoints | 17 | Health, Auth, Sessions, Events, Export |
| Proxy Management | 12 | Config, Sessions, IPRoyal integration |
| Configuration | 10 | YAML loading, Database operations |
| Behavior | 9 | Math utilities, Timing, Bezier curves |
| **Total** | **48** | Core functionality |

#### Test Markers

```python
@pytest.mark.slow          # Long-running tests
@pytest.mark.integration   # Integration tests
@pytest.mark.playwright    # Playwright-dependent tests
```

### GitHub Actions CI Pipeline

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

#### Pipeline Triggers

- Push to `main`, `master`, `develop`
- Pull requests to these branches

#### Quality Gates

| Check | Tool | Threshold |
|-------|------|-----------|
| Linting | Ruff | No errors |
| Formatting | Black | Consistent style |
| Tests | Pytest | All pass |
| Coverage | pytest-cov | Reported |
| Security | Bandit | No high severity |

### Development Commands (Makefile)

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

### Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Pytest, Black, Ruff, MyPy config |
| `Makefile` | Development commands |
| `requirements-dev.txt` | Test/dev dependencies |
| `.github/workflows/ci.yml` | GitHub Actions |

### Test Results

```
============ 48 passed, 5 skipped in 1.66s ============

Coverage:
- src/api/        85%
- src/proxy/      90%
- src/behavior/   75%
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
| `start_adspower.sh` | Start AdsPower (VPS) |
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

*Document generated: January 2026*  
*Project version: 1.0.0*
