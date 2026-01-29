# System Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User / Scheduler                        │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    BotOrchestrator                           │
│  - Manages multiple bot sessions                             │
│  - Coordinates AdsPower profiles                             │
│  - Handles proxy rotation                                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
         ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  AdsPower   │  │   IPRoyal   │  │    API      │
│  Browser    │  │   Proxy     │  │   Server    │
└─────────────┘  └─────────────┘  └─────────────┘
```

## Components

### 1. Core Layer (`src/core/`)
- **Orchestrator**: Manages bot lifecycle
- **Config**: Environment and settings

### 2. AdsPower Layer (`src/adspower/`)
- **Client**: API communication
- **Browser**: Browser control via CDP
- **Profile**: Profile management

### 3. Proxy Layer (`src/proxy/`)
- **IPRoyal**: Residential proxy provider
- **Stats**: Proxy health tracking
- **Rotation**: Smart proxy selection

### 4. Behavior Layer (`src/behavior/`)
- **Mouse**: Bezier curve movements
- **Timing**: Weibull distributions
- **Scroll**: Human-like scrolling

### 5. API Layer (`src/api/`)
- **Server**: FastAPI application
- **Database**: SQLite storage
- **WebSocket**: Real-time updates

## Data Flow

```
1. User starts session
2. Orchestrator requests AdsPower profile
3. IPRoyal provides sticky proxy
4. Browser launches with fingerprint
5. Behavior modules simulate human
6. Events logged to database
7. Dashboard receives WebSocket updates
```

## Database Schema

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    profile_id TEXT,
    proxy TEXT,
    country TEXT,
    start_time TEXT,
    end_time TEXT,
    success INTEGER
);

-- Events table
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    event_type TEXT,
    timestamp TEXT,
    data TEXT
);

-- Proxy stats table
CREATE TABLE proxy_stats (
    proxy_id TEXT PRIMARY KEY,
    success_count INTEGER,
    failure_count INTEGER,
    avg_latency_ms REAL
);
```

## Security

- API key authentication
- CORS configuration
- Rate limiting (slowapi)
- Environment variable secrets
