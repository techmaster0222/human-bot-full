# Dashboard

Real-time monitoring dashboard for AdsPower Bot Engine.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Recharts** - Charts
- **Axios** - HTTP client
- **date-fns** - Date formatting

## Features

- Real-time session monitoring
- Statistics dashboard
- IP health status tracking
- Activity timeline charts
- WebSocket live updates

## Quick Start

### Prerequisites

- Node.js 18+ 
- API server running on port 8000

### Install & Run

```bash
npm install
npm run dev
```

Dashboard available at **http://localhost:3000**

## Project Structure

```
dashboard/
├── src/
│   ├── components/     # React components
│   │   ├── Dashboard.tsx
│   │   ├── StatsCards.tsx
│   │   ├── SessionList.tsx
│   │   ├── IPStatus.tsx
│   │   └── ActivityChart.tsx
│   ├── services/       # API & WebSocket
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── types/          # TypeScript types
│   └── App.tsx
├── package.json
└── vite.config.ts
```

## Configuration

Create `.env` file (optional):

```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## Scripts

```bash
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview build
```

## API Requirements

The dashboard requires the API server to be running:

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/sessions` | Session list |
| `GET /api/stats` | Statistics |
| `GET /api/events` | Event log |
| `WS /ws` | Real-time updates |
