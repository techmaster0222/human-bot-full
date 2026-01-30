"""
FastAPI Server - REST API and WebSocket for Dashboard
"""

import asyncio
import csv
import io
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import APIKeyHeader
from loguru import logger
from pydantic import BaseModel

from .database_logger import DatabaseLogger
from .event_logger import EventLogger

# Load .env before accessing environment variables
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Rate limiting (optional)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    RATE_LIMITING_ENABLED = True
except ImportError:
    RATE_LIMITING_ENABLED = False


# ============== Configuration ==============

API_KEY = os.getenv("API_KEY", "")  # Empty = no auth required (dev mode)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(
    ","
)
RATE_LIMIT = os.getenv("RATE_LIMIT", "100/minute")  # Default: 100 requests per minute


# ============== Security ==============

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)) -> bool:
    """Verify API key if authentication is enabled"""
    # If no API_KEY is set, allow all requests (development mode)
    if not API_KEY:
        return True

    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Provide X-API-Key header.")

    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return True


# ============== Rate Limiter ==============

if RATE_LIMITING_ENABLED:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None


# ============== Pydantic Models ==============


class SessionResponse(BaseModel):
    session_id: str
    profile_id: str
    device: str
    start_time: str
    target_url: str | None = None
    proxy: str | None = None
    country: str | None = None
    status: str = "active"
    duration: float | None = None
    success: bool | None = None


class StatsResponse(BaseModel):
    total_sessions: int
    active_sessions: int
    successful_sessions: int
    failed_sessions: int
    total_events: int
    average_duration: float
    success_rate: float
    proxy_stats: list[dict[str, Any]]
    ip_health: dict[str, int]


class EventResponse(BaseModel):
    id: int
    session_id: str | None
    event_type: str
    timestamp: str
    data: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    active_sessions: int
    database_path: str
    version: str = "1.0.0"
    auth_enabled: bool = False
    rate_limiting: bool = False


class PaginatedSessionsResponse(BaseModel):
    sessions: list[SessionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class PaginatedEventsResponse(BaseModel):
    events: list[EventResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ============== Global State ==============

event_logger: EventLogger | None = None
db_logger: DatabaseLogger | None = None
proxy_stats_manager = None
websocket_connections: list[WebSocket] = []
active_sessions: dict[str, dict[str, Any]] = {}


# ============== WebSocket Broadcast ==============


async def broadcast_event(event: dict[str, Any]) -> None:
    """Broadcast event to all connected WebSocket clients"""
    if not websocket_connections:
        return

    message = {"type": "event", "data": event}

    disconnected = []
    for ws in websocket_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)


def event_callback(event: dict[str, Any]) -> None:
    """Callback for logging events"""
    if event_logger:
        event_logger.log_event(
            event["type"], event.get("data", {}), level=event.get("level", "INFO")
        )

    if db_logger and event["type"] in [
        "session_start",
        "session_end",
        "click",
        "scroll",
        "navigation",
        "error",
        "proxy_assigned",
        "ip_rotation",
    ]:
        db_logger.save_event(
            event.get("data", {}).get("session_id", ""),
            event["type"],
            event.get("data", {}),
            event.get("timestamp"),
        )

    asyncio.create_task(broadcast_event(event))


# ============== Lifespan ==============


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global event_logger, db_logger, proxy_stats_manager

    logger.info("Starting API server...")

    event_logger = EventLogger(log_file="logs/api_events.log", log_format="json", log_level="INFO")

    db_logger = DatabaseLogger(db_path="data/bot_events.db")

    try:
        from src.proxy.stats import ProxyStatsManager

        proxy_stats_manager = ProxyStatsManager()
        logger.info("ProxyStatsManager initialized")
    except Exception as e:
        logger.warning(f"Could not initialize ProxyStatsManager: {e}")
        proxy_stats_manager = None

    # Log security status
    auth_status = "enabled" if API_KEY else "disabled (dev mode)"
    rate_status = "enabled" if RATE_LIMITING_ENABLED else "disabled"
    logger.info(f"Security: Auth={auth_status}, RateLimit={rate_status}")
    logger.info(f"Allowed origins: {ALLOWED_ORIGINS}")

    event_logger.log_event("system_start", {"message": "API server started"})
    logger.info("API server started on http://0.0.0.0:8000")

    yield

    logger.info("Shutting down API server...")
    if event_logger:
        event_logger.log_event("system_stop", {"message": "API server stopped"})


# ============== FastAPI App ==============

app = FastAPI(
    title="Human Bot Dashboard API",
    description="Real-time monitoring API for AdsPower bot sessions",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting middleware
if RATE_LIMITING_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware - configured for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ============== API Endpoints ==============


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint (no auth required)"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        active_sessions=len(active_sessions),
        database_path=db_logger.db_path if db_logger else "not_initialized",
        auth_enabled=bool(API_KEY),
        rate_limiting=RATE_LIMITING_ENABLED,
    )


@app.get("/api/sessions", response_model=PaginatedSessionsResponse)
async def get_sessions(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter: active, completed, failed"),
    search: str | None = Query(None, description="Search in session_id, profile_id, proxy"),
    country: str | None = Query(None, description="Filter by country"),
    _: bool = Depends(verify_api_key),
):
    """Get sessions with pagination, filtering, and search"""
    sessions_list = []

    # Get active sessions
    for sid, info in active_sessions.items():
        sessions_list.append(
            {
                "session_id": sid,
                "profile_id": info.get("profile_id", ""),
                "device": info.get("device", "unknown"),
                "start_time": info.get("start_time", ""),
                "target_url": info.get("target_url"),
                "proxy": info.get("proxy"),
                "country": info.get("country"),
                "status": "active",
                "duration": None,
                "success": None,
            }
        )

    # Get historical sessions
    if db_logger:
        try:
            historical = db_logger.get_sessions(limit=500)
            for session in historical:
                if session["id"] not in active_sessions:
                    sessions_list.append(
                        {
                            "session_id": session["id"],
                            "profile_id": session.get("profile_id", ""),
                            "device": session.get("device", "unknown"),
                            "start_time": session.get("start_time", ""),
                            "target_url": session.get("target_url"),
                            "proxy": session.get("proxy"),
                            "country": session.get("country"),
                            "status": "completed" if session.get("success") else "failed",
                            "duration": session.get("duration"),
                            "success": session.get("success"),
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to get historical sessions: {e}")

    # Apply filters
    if status:
        sessions_list = [s for s in sessions_list if s["status"] == status]

    if country:
        sessions_list = [s for s in sessions_list if s.get("country") == country]

    if search:
        search_lower = search.lower()
        sessions_list = [
            s
            for s in sessions_list
            if (
                search_lower in s["session_id"].lower()
                or search_lower in (s.get("profile_id") or "").lower()
                or search_lower in (s.get("proxy") or "").lower()
            )
        ]

    # Sort by start_time descending
    sessions_list.sort(key=lambda x: x["start_time"], reverse=True)

    # Calculate pagination
    total = len(sessions_list)
    total_pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    end = start + per_page

    paginated = sessions_list[start:end]

    return PaginatedSessionsResponse(
        sessions=[SessionResponse(**s) for s in paginated],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@app.get("/api/sessions/export")
async def export_sessions_csv(
    request: Request,
    status: str | None = None,
    country: str | None = None,
    _: bool = Depends(verify_api_key),
):
    """Export sessions to CSV"""
    sessions_list = []

    # Get all sessions
    for sid, info in active_sessions.items():
        sessions_list.append(
            {
                "session_id": sid,
                "profile_id": info.get("profile_id", ""),
                "device": info.get("device", "unknown"),
                "start_time": info.get("start_time", ""),
                "proxy": info.get("proxy", ""),
                "country": info.get("country", ""),
                "status": "active",
                "duration": "",
                "success": "",
            }
        )

    if db_logger:
        historical = db_logger.get_sessions(limit=1000)
        for session in historical:
            if session["id"] not in active_sessions:
                sessions_list.append(
                    {
                        "session_id": session["id"],
                        "profile_id": session.get("profile_id", ""),
                        "device": session.get("device", "unknown"),
                        "start_time": session.get("start_time", ""),
                        "proxy": session.get("proxy", ""),
                        "country": session.get("country", ""),
                        "status": "completed" if session.get("success") else "failed",
                        "duration": session.get("duration", ""),
                        "success": session.get("success", ""),
                    }
                )

    # Apply filters
    if status:
        sessions_list = [s for s in sessions_list if s["status"] == status]
    if country:
        sessions_list = [s for s in sessions_list if s.get("country") == country]

    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "session_id",
            "profile_id",
            "device",
            "start_time",
            "proxy",
            "country",
            "status",
            "duration",
            "success",
        ],
    )
    writer.writeheader()
    writer.writerows(sessions_list)

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@app.get("/api/sessions/{session_id}")
async def get_session_detail(session_id: str, _: bool = Depends(verify_api_key)):
    """Get detailed session information"""
    if db_logger:
        session = db_logger.get_session(session_id)
        if session:
            events = db_logger.get_events(session_id=session_id, limit=100)
            return {"session": session, "events": events, "event_count": len(events)}

    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(request: Request, _: bool = Depends(verify_api_key)):
    """Get statistics"""
    if not db_logger:
        raise HTTPException(status_code=500, detail="Database not initialized")

    stats = db_logger.get_statistics()

    proxy_stats = []
    ip_health = {"healthy": 0, "flagged": 0, "blacklisted": 0}

    if proxy_stats_manager:
        try:
            all_proxies = proxy_stats_manager.get_all_stats()

            for p in all_proxies:
                if p.is_disabled:
                    status = "blacklisted"
                elif p.success_rate < 50:
                    status = "blacklisted"
                elif p.success_rate < 80:
                    status = "flagged"
                else:
                    status = "healthy"

                ip_health[status] += 1

                proxy_stats.append(
                    {
                        "url": p.proxy_id,
                        "uses": p.total_count,
                        "successes": p.success_count,
                        "failures": p.failure_count,
                        "success_rate": p.success_rate / 100,
                        "status": status,
                        "enabled": not p.is_disabled and not p.is_in_cooldown,
                        "last_used": p.last_used,
                        "avg_latency_ms": p.avg_latency_ms,
                        "country": p.country,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to get proxy stats: {e}")

    return StatsResponse(
        total_sessions=stats.get("total_sessions", 0),
        active_sessions=len(active_sessions),
        successful_sessions=stats.get("successful_sessions", 0),
        failed_sessions=stats.get("failed_sessions", 0),
        total_events=stats.get("total_events", 0),
        average_duration=stats.get("average_duration", 0.0),
        success_rate=stats.get("success_rate", 0.0),
        proxy_stats=proxy_stats,
        ip_health=ip_health,
    )


@app.get("/api/events", response_model=PaginatedEventsResponse)
async def get_events(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None, description="Filter by event type"),
    session_id: str | None = Query(None, description="Filter by session"),
    _: bool = Depends(verify_api_key),
):
    """Get events with pagination and filtering"""
    if not db_logger:
        return PaginatedEventsResponse(events=[], total=0, page=1, per_page=per_page, total_pages=0)

    try:
        # Get total count first
        all_events = db_logger.get_events(session_id=session_id, event_type=event_type, limit=1000)
        total = len(all_events)
        total_pages = (total + per_page - 1) // per_page

        # Get paginated results
        start = (page - 1) * per_page
        paginated_events = all_events[start : start + per_page]

        return PaginatedEventsResponse(
            events=[
                EventResponse(
                    id=e["id"],
                    session_id=e.get("session_id"),
                    event_type=e["event_type"],
                    timestamp=e["timestamp"],
                    data=e.get("data", {}),
                )
                for e in paginated_events
            ],
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Failed to get events: {e}")
        return PaginatedEventsResponse(events=[], total=0, page=1, per_page=per_page, total_pages=0)


@app.get("/api/events/export")
async def export_events_csv(
    request: Request,
    event_type: str | None = None,
    session_id: str | None = None,
    _: bool = Depends(verify_api_key),
):
    """Export events to CSV"""
    if not db_logger:
        raise HTTPException(status_code=500, detail="Database not initialized")

    events = db_logger.get_events(session_id=session_id, event_type=event_type, limit=5000)

    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=["id", "session_id", "event_type", "timestamp", "data"]
    )
    writer.writeheader()

    for e in events:
        writer.writerow(
            {
                "id": e["id"],
                "session_id": e.get("session_id", ""),
                "event_type": e["event_type"],
                "timestamp": e["timestamp"],
                "data": str(e.get("data", {})),
            }
        )

    output.seek(0)

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@app.get("/api/ip/status")
async def get_ip_status(request: Request, _: bool = Depends(verify_api_key)):
    """Get IP/proxy status"""
    proxies = []
    health = {"healthy": 0, "flagged": 0, "blacklisted": 0}

    if proxy_stats_manager:
        try:
            all_proxies = proxy_stats_manager.get_all_stats()

            for p in all_proxies:
                if p.is_disabled:
                    status = "blacklisted"
                elif p.success_rate < 50:
                    status = "blacklisted"
                elif p.success_rate < 80:
                    status = "flagged"
                else:
                    status = "healthy"

                health[status] += 1

                proxies.append(
                    {
                        "proxy_id": p.proxy_id,
                        "country": p.country,
                        "success_count": p.success_count,
                        "failure_count": p.failure_count,
                        "success_rate": p.success_rate,
                        "avg_latency_ms": p.avg_latency_ms,
                        "status": status,
                        "is_disabled": p.is_disabled,
                        "is_in_cooldown": p.is_in_cooldown,
                        "cooldown_until": p.cooldown_until,
                        "last_used": p.last_used,
                        "last_success": p.last_success,
                        "last_failure": p.last_failure,
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to get IP status: {e}")

    return {"proxies": proxies, "health": health}


# ============== Session Registration (Bot Integration) ==============


class SessionRegisterRequest(BaseModel):
    session_id: str
    profile_id: str
    device: str = "desktop"
    target_url: str | None = None
    proxy: str | None = None
    country: str | None = None


class SessionEndRequest(BaseModel):
    session_id: str
    success: bool = True
    duration: float = 0.0
    error: str | None = None


@app.post("/api/sessions/register")
async def register_session_endpoint(
    request: SessionRegisterRequest, _: bool = Depends(verify_api_key)
):
    """Register an active session"""
    session_data = {
        "session_id": request.session_id,
        "profile_id": request.profile_id,
        "device": request.device,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "target_url": request.target_url,
        "proxy": request.proxy,
        "country": request.country,
    }
    active_sessions[request.session_id] = session_data

    await broadcast_event(
        {"type": "session_start", "timestamp": session_data["start_time"], "data": session_data}
    )

    logger.info(f"Session registered: {request.session_id[:8]}... (active: {len(active_sessions)})")
    return {"status": "registered", "active_count": len(active_sessions)}


@app.post("/api/sessions/end")
async def end_session_endpoint(request: SessionEndRequest, _: bool = Depends(verify_api_key)):
    """End an active session"""
    session_data = active_sessions.pop(request.session_id, None)

    # Get proxy and country from session
    proxy = session_data.get("proxy") if session_data else None
    country = session_data.get("country") if session_data else None

    # Record proxy stats
    if proxy and proxy_stats_manager:
        try:
            if request.success:
                # Convert duration (seconds) to latency (ms)
                latency_ms = int(request.duration * 1000) if request.duration else None
                proxy_stats_manager.record_success(proxy, latency_ms=latency_ms, country=country)
                logger.debug(f"Recorded proxy success: {proxy}")
            else:
                proxy_stats_manager.record_failure(proxy, error=request.error, country=country)
                logger.debug(f"Recorded proxy failure: {proxy}")
        except Exception as e:
            logger.warning(f"Failed to record proxy stats: {e}")

    if db_logger and session_data:
        db_logger.save_session(
            {
                "id": request.session_id,
                "profile_id": session_data.get("profile_id", ""),
                "device": session_data.get("device", "unknown"),
                "target_url": session_data.get("target_url"),
                "proxy": proxy,
                "country": country,
                "start_time": session_data.get("start_time"),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "duration": request.duration,
                "success": request.success,
                "error": request.error,
            }
        )

    await broadcast_event(
        {
            "type": "session_end",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "session_id": request.session_id,
                "success": request.success,
                "duration": request.duration,
                "error": request.error,
            },
        }
    )

    logger.info(f"Session ended: {request.session_id[:8]}... (active: {len(active_sessions)})")
    return {"status": "ended", "active_count": len(active_sessions)}


# ============== WebSocket ==============


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(websocket_connections)}")

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(websocket_connections)}")


# ============== Internal Functions ==============


def register_session(
    session_id: str,
    profile_id: str,
    device: str = "unknown",
    target_url: str = None,
    proxy: str = None,
    country: str = None,
) -> None:
    """Register an active session (called by bot)"""
    active_sessions[session_id] = {
        "session_id": session_id,
        "profile_id": profile_id,
        "device": device,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "target_url": target_url,
        "proxy": proxy,
        "country": country,
    }

    event_callback(
        {
            "type": "session_start",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": active_sessions[session_id],
            "level": "INFO",
        }
    )


def unregister_session(
    session_id: str, success: bool = True, duration: float = 0.0, error: str = None
) -> None:
    """Unregister a session"""
    session_info = active_sessions.pop(session_id, {})

    if db_logger:
        db_logger.save_session(
            {
                "id": session_id,
                "profile_id": session_info.get("profile_id", ""),
                "device": session_info.get("device", "unknown"),
                "target_url": session_info.get("target_url"),
                "proxy": session_info.get("proxy"),
                "country": session_info.get("country"),
                "start_time": session_info.get("start_time"),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "duration": duration,
                "success": success,
                "error": error,
            }
        )

    event_callback(
        {
            "type": "session_end",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "session_id": session_id,
                "success": success,
                "duration": duration,
                "error": error,
            },
            "level": "INFO" if success else "WARNING",
        }
    )


def log_session_event(session_id: str, event_type: str, data: dict[str, Any] = None) -> None:
    """Log an event for a session"""
    event_callback(
        {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"session_id": session_id, **(data or {})},
            "level": "INFO",
        }
    )


# ============== Run Server ==============


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server"""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
