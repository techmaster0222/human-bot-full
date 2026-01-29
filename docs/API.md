# API Reference

Base URL: `http://localhost:8000`

## Authentication

All endpoints (except `/api/health`) require API key:

```bash
curl -H "X-API-Key: your_api_key" http://localhost:8000/api/stats
```

## Endpoints

### Health Check

```
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-29T12:00:00Z",
  "version": "1.0.0",
  "auth_enabled": true
}
```

### Sessions

#### List Sessions

```
GET /api/sessions?page=1&per_page=20&status=active&country=US
```

Response:
```json
{
  "sessions": [...],
  "total": 100,
  "page": 1,
  "per_page": 20
}
```

#### Register Session

```
POST /api/sessions/register
Content-Type: application/json

{
  "session_id": "uuid",
  "profile_id": "profile_1",
  "device": "desktop",
  "target_url": "https://example.com",
  "proxy": "1.2.3.4:8080",
  "country": "US"
}
```

#### End Session

```
POST /api/sessions/end
Content-Type: application/json

{
  "session_id": "uuid",
  "success": true,
  "duration": 15.5,
  "error": null
}
```

#### Export Sessions

```
GET /api/sessions/export?status=completed
```

Returns CSV file.

### Events

#### List Events

```
GET /api/events?page=1&per_page=50&session_id=uuid&event_type=navigation
```

#### Log Event

```
POST /api/events
Content-Type: application/json

{
  "session_id": "uuid",
  "event_type": "navigation",
  "details": {"url": "https://example.com"}
}
```

#### Export Events

```
GET /api/events/export
```

Returns CSV file.

### Statistics

```
GET /api/stats
```

Response:
```json
{
  "total_sessions": 1000,
  "active_sessions": 5,
  "successful_sessions": 850,
  "failed_sessions": 150,
  "success_rate": 85.0,
  "proxy_stats": [...],
  "ip_health": {
    "healthy": 10,
    "flagged": 2,
    "blacklisted": 1
  }
}
```

### IP Status

```
GET /api/ip/status
```

Response:
```json
{
  "proxies": [
    {
      "proxy_id": "1.2.3.4:8080",
      "success_rate": 95.0,
      "avg_latency_ms": 150,
      "status": "healthy"
    }
  ],
  "health": {
    "healthy": 10,
    "flagged": 2,
    "blacklisted": 1
  }
}
```

## WebSocket

```
WS /ws
```

Events:
```json
{"type": "session_started", "data": {...}}
{"type": "session_ended", "data": {...}}
{"type": "event_logged", "data": {...}}
{"type": "stats_updated", "data": {...}}
```

## Error Responses

```json
{
  "detail": "Error message"
}
```

Status codes:
- `401` - Missing API key
- `403` - Invalid API key
- `404` - Not found
- `422` - Validation error
- `429` - Rate limited
- `500` - Server error
