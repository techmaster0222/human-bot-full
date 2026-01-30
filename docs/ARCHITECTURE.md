# Architecture Documentation

> AdsPower Bot Engine - Technical Architecture & Design

## Table of Contents

1. [System Overview](#system-overview)
2. [High-Level Architecture](#high-level-architecture)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Module Structure](#module-structure)
6. [Database Schema](#database-schema)
7. [API Architecture](#api-architecture)
8. [Security Architecture](#security-architecture)
9. [Deployment Architecture](#deployment-architecture)

---

## System Overview

The AdsPower Bot Engine is a modular automation framework designed for browser automation with anti-detection capabilities. It integrates multiple external services while maintaining a clean separation of concerns.

### Core Principles

- **Modularity**: Each component is self-contained and replaceable
- **Observability**: Real-time monitoring via WebSocket and REST API
- **Resilience**: Automatic proxy rotation and failure recovery
- **Human-like**: Sophisticated behavior simulation to avoid detection

---

## High-Level Architecture

```mermaid
flowchart TB
    subgraph External["External Services"]
        ADS[AdsPower Browser]
        IPR[IPRoyal Proxies]
        TARGET[Target Websites]
    end

    subgraph Backend["Python Backend"]
        CORE[Core Orchestrator]
        BOT[Bot Engine]
        PROXY[Proxy Manager]
        ADS_CLIENT[AdsPower Client]
        BEHAVIOR[Behavior Simulator]
        API[FastAPI Server]
        DB[(SQLite DB)]
    end

    subgraph Frontend["React Dashboard"]
        DASH[Dashboard UI]
        WS_CLIENT[WebSocket Client]
    end

    %% External connections
    ADS_CLIENT <--> ADS
    PROXY <--> IPR
    BOT --> TARGET

    %% Internal connections
    CORE --> BOT
    CORE --> PROXY
    CORE --> ADS_CLIENT
    BOT --> BEHAVIOR
    BOT --> ADS_CLIENT
    
    %% API connections
    API <--> DB
    API <-.->|WebSocket| WS_CLIENT
    DASH --> WS_CLIENT
    
    %% Monitoring
    BOT -.->|Events| API
    PROXY -.->|Stats| API

    style External fill:#f9f,stroke:#333
    style Backend fill:#bbf,stroke:#333
    style Frontend fill:#bfb,stroke:#333
```

---

## Component Details

### 1. Core Layer (`src/core/`)

The orchestration layer that coordinates all bot activities.

```mermaid
classDiagram
    class BotOrchestrator {
        +config: Config
        +proxy_manager: ProxyManager
        +ads_client: AdsPowerClient
        +run_session(task)
        +run_parallel(tasks, workers)
    }
    
    class Config {
        +adspower: AdsPowerConfig
        +proxy: ProxyConfig
        +behavior: BehaviorConfig
        +load_from_yaml()
        +load_from_env()
    }
    
    BotOrchestrator --> Config
    BotOrchestrator --> ProxyManager
    BotOrchestrator --> AdsPowerClient
```

**Key Files:**
- `config.py` - Configuration management (YAML + environment variables)
- `orchestrator.py` - Session orchestration and parallel execution

### 2. AdsPower Integration (`src/adspower/`)

Manages browser profiles and Playwright connections.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant C as AdsPowerClient
    participant P as ProfileManager
    participant B as BrowserController
    participant ADS as AdsPower API

    O->>C: check_status()
    C->>ADS: GET /status
    ADS-->>C: {status: ok}
    
    O->>P: create_profile(config)
    P->>ADS: POST /api/v1/user/create
    ADS-->>P: {user_id: "abc123"}
    
    O->>B: start_browser(profile)
    B->>ADS: GET /api/v1/browser/start
    ADS-->>B: {ws_endpoint, debug_port}
    B->>B: connect_playwright(ws_endpoint)
    B-->>O: Page instance
```

**Key Files:**
- `client.py` - HTTP client for AdsPower API
- `profile.py` - Profile data models
- `controller.py` - Browser lifecycle management
- `browser.py` - Playwright connection handling

### 3. Proxy Management (`src/proxy/`)

Handles proxy rotation, health tracking, and session management.

```mermaid
stateDiagram-v2
    [*] --> Healthy: New Proxy
    
    Healthy --> Healthy: Success
    Healthy --> Flagged: Success Rate < 80%
    
    Flagged --> Healthy: Success Rate ≥ 80%
    Flagged --> Blacklisted: Success Rate < 50%
    Flagged --> Blacklisted: 3 Consecutive Failures
    
    Blacklisted --> Cooldown: Auto-disable
    Cooldown --> Healthy: After 30 min
```

**Key Files:**
- `iproyal.py` - IPRoyal proxy configuration
- `rotation.py` - Rotation strategies (round-robin, weighted, random)
- `stats.py` - Proxy statistics and health scoring
- `session_manager.py` - Sticky session management

### 4. Bot Engine (`src/bot/`)

Executes bot actions with human-like behavior.

```mermaid
flowchart LR
    subgraph BotActions
        NAV[navigate_to]
        CLICK[click_element]
        TYPE[type_text]
        SCROLL[scroll_down/up]
        WAIT[random_wait]
    end

    subgraph HumanBehavior
        MOUSE[Mouse Curves]
        TIMING[Random Delays]
        TYPO[Typo Simulation]
        PAUSE[Reading Pauses]
    end

    NAV --> TIMING
    CLICK --> MOUSE
    TYPE --> TYPO
    TYPE --> TIMING
    SCROLL --> PAUSE
```

**Key Files:**
- `actions.py` - High-level bot actions (navigate, click, type, scroll)
- `human_behavior.py` - Human-like behavior patterns
- `session.py` - Bot session lifecycle

### 5. Behavior Simulation (`src/behavior/`)

Low-level human behavior simulation algorithms.

```mermaid
flowchart TB
    subgraph MouseMovement
        START[Start Point] --> BEZIER[Bezier Curve]
        BEZIER --> NOISE[Add Noise]
        NOISE --> SPEED[Variable Speed]
        SPEED --> END[End Point]
    end

    subgraph Timing
        BASE[Base Delay] --> GAUSSIAN[Gaussian Distribution]
        GAUSSIAN --> CLAMP[Min/Max Clamp]
    end

    subgraph Typing
        CHAR[Character] --> WPM[Words Per Minute]
        WPM --> VARIANCE[Random Variance]
        VARIANCE --> TYPO{Typo?}
        TYPO -->|Yes| BACKSPACE[Backspace + Retype]
        TYPO -->|No| NEXT[Next Character]
    end
```

**Key Files:**
- `mouse.py` - Bezier curve mouse movements
- `timing.py` - Gaussian-distributed delays
- `scroll.py` - Natural scrolling patterns
- `interaction.py` - Click and hover behaviors
- `focus.py` - Tab focus simulation

### 6. API Layer (`src/api/`)

FastAPI backend with WebSocket support.

```mermaid
flowchart TB
    subgraph Endpoints
        HEALTH[/api/health]
        SESSIONS[/api/sessions]
        STATS[/api/stats]
        EVENTS[/api/events]
        IP[/api/ip/status]
        EXPORT[/api/*/export]
    end

    subgraph Middleware
        AUTH[API Key Auth]
        CORS[CORS]
        RATE[Rate Limiting]
    end

    subgraph Realtime
        WS[WebSocket /ws]
        BROADCAST[Event Broadcast]
    end

    CLIENT --> AUTH
    AUTH --> CORS
    CORS --> RATE
    RATE --> Endpoints
    
    BOT -.->|Events| BROADCAST
    BROADCAST --> WS
    WS --> DASHBOARD
```

**Key Files:**
- `server.py` - FastAPI application and endpoints
- `session_tracker.py` - Session tracking (HTTP or local)
- `database_logger.py` - SQLite persistence
- `event_logger.py` - File-based logging

---

## Data Flow

### Session Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant AdsPower
    participant Proxy
    participant Bot
    participant API
    participant Dashboard

    User->>Orchestrator: Start Session
    Orchestrator->>Proxy: Get Proxy
    Proxy-->>Orchestrator: proxy_config
    
    Orchestrator->>AdsPower: Create Profile
    AdsPower-->>Orchestrator: profile_id
    
    Orchestrator->>AdsPower: Start Browser
    AdsPower-->>Orchestrator: page
    
    Orchestrator->>API: Register Session
    API->>Dashboard: WebSocket: session_start
    
    Orchestrator->>Bot: Execute Task
    Bot->>Bot: Human-like actions
    Bot->>API: Log Events
    API->>Dashboard: WebSocket: events
    
    Bot-->>Orchestrator: Result
    Orchestrator->>API: End Session
    API->>Proxy: Record Stats
    API->>Dashboard: WebSocket: session_end
    
    Orchestrator->>AdsPower: Stop Browser
    Orchestrator->>AdsPower: Delete Profile
```

### Event Flow

```mermaid
flowchart LR
    BOT[Bot Action] --> TRACKER[Session Tracker]
    TRACKER --> |HTTP| API[API Server]
    TRACKER --> |Local| DB[(SQLite)]
    
    API --> DB
    API --> WS[WebSocket]
    WS --> DASH[Dashboard]
    
    API --> LOG[Log File]
```

---

## Module Structure

```
src/
├── __init__.py
├── adspower/                 # AdsPower Integration
│   ├── __init__.py          # Exports: AdsPowerClient, ProfileManager, BrowserController
│   ├── client.py            # HTTP client for AdsPower API
│   ├── profile.py           # Profile data models
│   ├── profile_factory.py   # Profile creation helpers
│   ├── controller.py        # Browser lifecycle management
│   └── browser.py           # Playwright connection
│
├── api/                      # FastAPI Backend
│   ├── __init__.py          # Exports: get_tracker
│   ├── server.py            # FastAPI app, endpoints, WebSocket
│   ├── session_tracker.py   # HTTP/Local session tracking
│   ├── database_logger.py   # SQLite persistence
│   └── event_logger.py      # File logging
│
├── behavior/                 # Human Behavior Algorithms
│   ├── __init__.py
│   ├── mouse.py             # Bezier curve movements
│   ├── timing.py            # Gaussian delays
│   ├── scroll.py            # Natural scrolling
│   ├── interaction.py       # Click/hover patterns
│   └── focus.py             # Tab focus simulation
│
├── bot/                      # Bot Engine
│   ├── __init__.py          # Exports: BotActions, HumanBehavior
│   ├── actions.py           # High-level actions
│   ├── human_behavior.py    # Behavior orchestration
│   └── session.py           # Session management
│
├── core/                     # Core Orchestration
│   ├── __init__.py          # Exports: load_config, BotOrchestrator
│   ├── config.py            # Configuration (YAML + env)
│   └── orchestrator.py      # Session orchestration
│
├── proxy/                    # Proxy Management
│   ├── __init__.py          # Exports: IPRoyalProxy, ProxyManager
│   ├── iproyal.py           # IPRoyal configuration
│   ├── rotation.py          # Rotation strategies
│   ├── stats.py             # Health tracking
│   └── session_manager.py   # Sticky sessions
│
├── reputation/               # Proxy Reputation System
│   ├── cooldown.py          # Cooldown management
│   ├── policy.py            # Scoring policies
│   ├── scorer.py            # Health scoring
│   └── store.py             # Persistence
│
├── events/                   # Event System
│   ├── __init__.py
│   ├── types.py             # Event type definitions
│   ├── logger.py            # Event logging
│   └── store.py             # Event storage
│
└── session/                  # Session Management
    ├── context.py           # Session context
    ├── logger.py            # Session logging
    ├── orchestrator.py      # Multi-session orchestration
    └── runner.py            # Session execution
```

---

## Database Schema

### SQLite Tables

```mermaid
erDiagram
    sessions {
        TEXT id PK
        TEXT profile_id
        TEXT device
        TEXT target_url
        TEXT proxy
        TEXT country
        TEXT start_time
        TEXT end_time
        REAL duration
        INTEGER success
        TEXT error
        TEXT status
    }
    
    events {
        INTEGER id PK
        TEXT session_id FK
        TEXT event_type
        TEXT timestamp
        TEXT details
    }
    
    proxy_stats {
        TEXT proxy_url PK
        INTEGER uses
        INTEGER successes
        INTEGER failures
        INTEGER consecutive_failures
        REAL avg_latency_ms
        TEXT last_used
        TEXT country
        INTEGER enabled
    }
    
    sessions ||--o{ events : "has"
```

---

## API Architecture

### Endpoint Summary

| Endpoint | Method | Auth | Rate Limit | Description |
|----------|--------|------|------------|-------------|
| `/api/health` | GET | No | No | Health check |
| `/api/sessions` | GET | Yes | Yes | List sessions (paginated) |
| `/api/sessions/{id}` | GET | Yes | Yes | Session details |
| `/api/sessions/register` | POST | Yes | Yes | Register new session |
| `/api/sessions/end` | POST | Yes | Yes | End session |
| `/api/sessions/export` | GET | Yes | Yes | Export to CSV |
| `/api/stats` | GET | Yes | Yes | Statistics |
| `/api/events` | GET | Yes | Yes | List events (paginated) |
| `/api/events` | POST | Yes | Yes | Log event |
| `/api/events/export` | GET | Yes | Yes | Export to CSV |
| `/api/ip/status` | GET | Yes | Yes | Proxy health |
| `/ws` | WS | No | No | Real-time updates |

### WebSocket Events

```typescript
// Session events
{ type: "session_start", data: { session_id, profile_id, proxy, country } }
{ type: "session_end", data: { session_id, success, duration, error } }

// Bot events
{ type: "event", data: { session_id, event_type, details, timestamp } }

// Stats updates
{ type: "stats_update", data: { total_sessions, active_sessions, ... } }
```

---

## Security Architecture

```mermaid
flowchart TB
    subgraph Security["Security Layers"]
        API_KEY[API Key Header]
        CORS[CORS Whitelist]
        RATE[Rate Limiting]
    end

    subgraph Config["Configuration"]
        ENV[.env File]
        YAML[settings.yaml]
    end

    REQUEST[Incoming Request] --> API_KEY
    API_KEY -->|Valid| CORS
    API_KEY -->|Invalid| REJECT1[403 Forbidden]
    CORS -->|Allowed Origin| RATE
    CORS -->|Blocked| REJECT2[403 Forbidden]
    RATE -->|Under Limit| HANDLER[Request Handler]
    RATE -->|Over Limit| REJECT3[429 Too Many]

    ENV --> API_KEY
    ENV --> CORS
    ENV --> RATE
```

### Security Configuration

```env
# .env
API_KEY=your_secret_key_here
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
RATE_LIMIT=100/minute
```

---

## Deployment Architecture

### VPS Deployment

```mermaid
flowchart TB
    subgraph VPS["VPS Server"]
        subgraph Services
            ADS_PROC[AdsPower Process]
            API_PROC[FastAPI Process]
            DASH_PROC[Dashboard Process]
        end
        
        subgraph Storage
            SQLITE[(SQLite DB)]
            LOGS[Log Files]
        end
        
        subgraph Ports
            P50325[":50325 AdsPower"]
            P8000[":8000 API"]
            P3000[":3000 Dashboard"]
        end
    end

    subgraph External
        PROXY[IPRoyal Proxies]
        TARGET[Target Sites]
    end

    ADS_PROC --> P50325
    API_PROC --> P8000
    DASH_PROC --> P3000
    
    API_PROC --> SQLITE
    API_PROC --> LOGS
    
    ADS_PROC --> PROXY
    ADS_PROC --> TARGET
```

### Startup Sequence

```mermaid
sequenceDiagram
    participant User
    participant Script as start_all.sh
    participant ADS as AdsPower
    participant API as API Server
    participant DASH as Dashboard

    User->>Script: ./scripts/start_all.sh
    Script->>ADS: Start AdsPower (if VPS)
    Script->>API: ./scripts/start_api.sh
    
    loop Health Check
        Script->>API: GET /api/health
        API-->>Script: {status: healthy}
    end
    
    Script->>DASH: ./scripts/start_dashboard.sh
    DASH-->>User: Ready at :3000
```

---

## Related Documentation

- [README.md](../README.md) - Quick start guide
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development guide & extending the system
- [API.md](./API.md) - Full API reference

---

*Last updated: January 2026*
