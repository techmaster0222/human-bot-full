# API Reference

> Complete API documentation for the AdsPower Bot Engine

**Base URL**: `http://localhost:8000`  
**Authentication**: `X-API-Key` header (except `/api/health` and `/ws`)

---

## Table of Contents

1. [Authentication](#authentication)
2. [Health Check](#health-check)
3. [Sessions](#sessions)
4. [Events](#events)
5. [Statistics](#statistics)
6. [IP Status](#ip-status)
7. [WebSocket](#websocket)
8. [Error Handling](#error-handling)

---

## Authentication

All endpoints (except `/api/health` and `/ws`) require API key authentication.

### Header

```
X-API-Key: your_api_key_here
```

### Example

```bash
curl -H "X-API-Key: dev_secret_key_change_me_in_production_2026" \
  http://localhost:8000/api/stats
```

### Error Response (401/403)

```json
{
  "detail": "Missing API key. Provide X-API-Key header."
}
```

```json
{
  "detail": "Invalid API key"
}
```

---

## Health Check

### GET /api/health

Check API server status. **No authentication required.**

#### Response

```json
{
  "status": "healthy",
  "timestamp": "2026-01-29T12:00:00.000000+00:00",
  "active_sessions": 5,
  "database_path": "data/bot_events.db",
  "version": "1.0.0",
  "auth_enabled": true,
  "rate_limiting": true
}
```

#### Example

```bash
curl http://localhost:8000/api/health
```

---

## Sessions

### GET /api/sessions

List all sessions with pagination and filtering.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |
| `status` | string | - | Filter: "active", "completed", "failed" |
| `country` | string | - | Filter by country code |
| `search` | string | - | Search in session_id, profile_id, proxy |

#### Response

```json
{
  "sessions": [
    {
      "id": "abc123-...",
      "profile_id": "profile_1",
      "device": "desktop",
      "target_url": "https://example.com",
      "proxy": "1.2.3.4:12321",
      "country": "US",
      "start_time": "2026-01-29T12:00:00+00:00",
      "end_time": "2026-01-29T12:00:15+00:00",
      "duration": 15.0,
      "success": true,
      "error": null,
      "status": "completed"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "total_pages": 5
}
```

#### Example

```bash
# Get page 2 with 10 items, failed sessions only
curl -H "X-API-Key: your_key" \
  "http://localhost:8000/api/sessions?page=2&per_page=10&status=failed"
```

---

### GET /api/sessions/{session_id}

Get detailed information about a specific session.

#### Response

```json
{
  "session": {
    "id": "abc123-...",
    "profile_id": "profile_1",
    "device": "desktop",
    "target_url": "https://example.com",
    "proxy": "1.2.3.4:12321",
    "country": "US",
    "start_time": "2026-01-29T12:00:00+00:00",
    "end_time": "2026-01-29T12:00:15+00:00",
    "duration": 15.0,
    "success": true,
    "error": null,
    "status": "completed"
  },
  "events": [
    {
      "id": 1,
      "session_id": "abc123-...",
      "event_type": "navigation",
      "timestamp": "2026-01-29T12:00:01+00:00",
      "details": {"url": "https://example.com"}
    }
  ],
  "event_count": 5
}
```

---

### POST /api/sessions/register

Register a new session.

#### Request Body

```json
{
  "session_id": "abc123-...",
  "profile_id": "profile_1",
  "device": "desktop",
  "target_url": "https://example.com",
  "proxy": "1.2.3.4:12321",
  "country": "US"
}
```

#### Response

```json
{
  "status": "registered",
  "session_id": "abc123-...",
  "active_count": 6
}
```

---

### POST /api/sessions/end

End an active session and record results.

#### Request Body

```json
{
  "session_id": "abc123-...",
  "success": true,
  "duration": 15.0,
  "error": null
}
```

#### Response

```json
{
  "status": "ended",
  "active_count": 5
}
```

---

### GET /api/sessions/export

Export sessions to CSV file.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status |
| `country` | string | Filter by country |

#### Response

Returns CSV file download with headers:
- `session_id`
- `profile_id`
- `device`
- `start_time`
- `proxy`
- `country`
- `status`
- `duration`
- `success`

#### Example

```bash
curl -H "X-API-Key: your_key" \
  "http://localhost:8000/api/sessions/export?status=completed" \
  -o sessions.csv
```

---

## Events

### GET /api/events

List all events with pagination and filtering.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Items per page (max 200) |
| `event_type` | string | - | Filter by event type |
| `session_id` | string | - | Filter by session ID |

#### Response

```json
{
  "events": [
    {
      "id": 1,
      "session_id": "abc123-...",
      "event_type": "navigation",
      "timestamp": "2026-01-29T12:00:01+00:00",
      "details": {"url": "https://example.com", "status": "completed"}
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 50,
  "total_pages": 10
}
```

---

### POST /api/events

Log a new event.

#### Request Body

```json
{
  "session_id": "abc123-...",
  "event_type": "navigation",
  "details": {
    "url": "https://example.com",
    "load_time_ms": 1500
  }
}
```

#### Response

```json
{
  "status": "logged",
  "event_id": 123
}
```

#### Event Types

| Type | Description |
|------|-------------|
| `navigation` | Page navigation |
| `page_load` | Page finished loading |
| `click` | Element clicked |
| `scroll` | Page scrolled |
| `type` | Text typed |
| `screenshot` | Screenshot taken |
| `error` | Error occurred |
| `custom` | Custom event |

---

### GET /api/events/export

Export events to CSV file.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | string | Filter by event type |
| `session_id` | string | Filter by session ID |

#### Response

Returns CSV file download.

---

## Statistics

### GET /api/stats

Get overall statistics and proxy health.

#### Response

```json
{
  "total_sessions": 100,
  "active_sessions": 5,
  "successful_sessions": 85,
  "failed_sessions": 10,
  "total_events": 1500,
  "average_duration": 12.5,
  "success_rate": 85.0,
  "proxy_stats": [
    {
      "url": "1.2.3.4:12321",
      "uses": 20,
      "successes": 18,
      "failures": 2,
      "success_rate": 0.9,
      "status": "healthy",
      "enabled": true,
      "last_used": "2026-01-29T12:00:00+00:00",
      "avg_latency_ms": 1500.0,
      "country": "US"
    }
  ],
  "ip_health": {
    "healthy": 8,
    "flagged": 2,
    "blacklisted": 1
  }
}
```

---

## IP Status

### GET /api/ip/status

Get detailed proxy health information.

#### Response

```json
{
  "proxies": [
    {
      "url": "1.2.3.4:12321",
      "uses": 20,
      "successes": 18,
      "failures": 2,
      "success_rate": 0.9,
      "status": "healthy",
      "enabled": true,
      "last_used": "2026-01-29T12:00:00+00:00",
      "avg_latency_ms": 1500.0,
      "country": "US"
    }
  ],
  "health": {
    "healthy": 8,
    "flagged": 2,
    "blacklisted": 1
  }
}
```

#### Proxy Status Values

| Status | Condition |
|--------|-----------|
| `healthy` | Success rate ≥ 80% |
| `flagged` | Success rate 50-80% |
| `blacklisted` | Success rate < 50% OR disabled |

---

## WebSocket

### WS /ws

Real-time event streaming. **No authentication required.**

#### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.data);
};
```

#### Event Types

##### session_start

```json
{
  "type": "session_start",
  "timestamp": "2026-01-29T12:00:00+00:00",
  "data": {
    "session_id": "abc123-...",
    "profile_id": "profile_1",
    "device": "desktop",
    "proxy": "1.2.3.4:12321",
    "country": "US"
  }
}
```

##### session_end

```json
{
  "type": "session_end",
  "timestamp": "2026-01-29T12:00:15+00:00",
  "data": {
    "session_id": "abc123-...",
    "success": true,
    "duration": 15.0,
    "error": null
  }
}
```

##### event

```json
{
  "type": "event",
  "timestamp": "2026-01-29T12:00:01+00:00",
  "data": {
    "session_id": "abc123-...",
    "event_type": "navigation",
    "details": {"url": "https://example.com"}
  }
}
```

##### stats_update

```json
{
  "type": "stats_update",
  "timestamp": "2026-01-29T12:00:00+00:00",
  "data": {
    "total_sessions": 100,
    "active_sessions": 5,
    "success_rate": 85.0
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (missing API key) |
| 403 | Forbidden (invalid API key) |
| 404 | Not Found |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

### Rate Limiting

Default: 100 requests per minute per IP.

When exceeded:

```json
{
  "error": "Rate limit exceeded: 100 per 1 minute"
}
```

---

## Code Examples

### Python (httpx)

```python
import httpx

API_URL = "http://localhost:8000"
API_KEY = "your_key_here"

headers = {"X-API-Key": API_KEY}

# Get sessions
response = httpx.get(f"{API_URL}/api/sessions", headers=headers)
sessions = response.json()

# Register session
response = httpx.post(
    f"{API_URL}/api/sessions/register",
    headers=headers,
    json={
        "session_id": "my-session-123",
        "profile_id": "profile_1",
        "device": "desktop",
        "proxy": "1.2.3.4:12321",
        "country": "US"
    }
)
```

### JavaScript (fetch)

```javascript
const API_URL = 'http://localhost:8000';
const API_KEY = 'your_key_here';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

// Get sessions
const response = await fetch(`${API_URL}/api/sessions`, { headers });
const sessions = await response.json();

// Register session
const regResponse = await fetch(`${API_URL}/api/sessions/register`, {
  method: 'POST',
  headers,
  body: JSON.stringify({
    session_id: 'my-session-123',
    profile_id: 'profile_1',
    device: 'desktop',
    proxy: '1.2.3.4:12321',
    country: 'US'
  })
});
```

### cURL

```bash
# Health check
curl http://localhost:8000/api/health

# Get stats
curl -H "X-API-Key: your_key" http://localhost:8000/api/stats

# Register session
curl -X POST -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","profile_id":"p1","device":"desktop"}' \
  http://localhost:8000/api/sessions/register
```

---

*Last updated: January 2026*
