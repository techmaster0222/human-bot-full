# AdsPower Bot Engine

A human-like browser automation framework with AdsPower fingerprint browsers and IPRoyal residential proxies.

## Features

- **Human-like Behavior**: Bezier mouse movements, Weibull timing distributions, natural scrolling
- **Anti-Detection**: AdsPower browser fingerprinting + residential proxies
- **Real-time Dashboard**: Monitor sessions, events, and proxy health
- **API Server**: RESTful API with WebSocket for live updates

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 3. Start Services

```bash
# Option A: Start everything
./scripts/start_all.sh

# Option B: Start individually
./scripts/start_api.sh      # API server (port 8000)
./scripts/start_dashboard.sh # Dashboard (port 5173)
```

### 4. Run Bot

```bash
python main.py
```

## Project Structure

```
ads_project/
├── src/                 # Python source code
│   ├── api/            # FastAPI server
│   ├── adspower/       # AdsPower integration
│   ├── behavior/       # Human-like behaviors
│   ├── bot/            # Bot session management
│   ├── proxy/          # IPRoyal proxy management
│   └── core/           # Orchestration
├── dashboard/          # React frontend
├── scripts/            # Shell scripts
├── tests/              # Test suite
├── docs/               # Documentation
└── config/             # Configuration files
```

## Configuration

Edit `.env` file:

| Variable | Description |
|----------|-------------|
| `ADSPOWER_API_URL` | AdsPower local API |
| `ADSPOWER_API_KEY` | AdsPower API key |
| `IPROYAL_USERNAME` | IPRoyal username |
| `IPROYAL_PASSWORD` | IPRoyal password |
| `API_KEY` | Dashboard API key |

## Testing

```bash
# Run unit tests
make test

# Run with coverage
make test-cov

# Test dashboard (10 sessions)
python run_10_sessions.py
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Development guide |
| [docs/API.md](docs/API.md) | API reference |
| [docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md) | Project report |

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/sessions` - List sessions
- `GET /api/events` - List events
- `GET /api/stats` - Statistics
- `WS /ws` - WebSocket for live updates

Interactive docs: http://localhost:8000/docs

## License

Private - All rights reserved.
