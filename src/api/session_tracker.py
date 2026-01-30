"""
Session Tracker - Integration module for bot sessions
Tracks active sessions and events for the dashboard.
Also integrates with ProxyStatsManager for IP health tracking.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import requests
from loguru import logger


@dataclass
class TrackedSession:
    """Tracked session data"""

    session_id: str
    profile_id: str
    device: str = "desktop"
    target_url: str | None = None
    proxy: str | None = None
    country: str | None = None
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    start_timestamp: float = field(default_factory=time.time)
    events: list = field(default_factory=list)


class SessionTracker:
    """
    Session tracker for dashboard integration.

    Tracks active sessions and logs events to the API.
    Also tracks proxy performance for IP health monitoring.

    Can work in two modes:
    - Local: Direct database access (when running in same process)
    - Remote: HTTP API calls (when API server is separate)

    Usage:
        tracker = SessionTracker()
        session_id = tracker.start_session(profile_id="abc123", device="desktop", proxy="geo.iproyal.com:12321")
        tracker.log_event(session_id, "navigation", {"url": "https://example.com"})
        tracker.end_session(session_id, success=True)  # Also records proxy success/failure
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        use_local: bool = False,
        db_path: str = "data/bot_events.db",
        track_proxy_stats: bool = True,
    ):
        """
        Initialize session tracker.

        Args:
            api_url: API server URL for remote mode
            use_local: If True, use direct database access instead of HTTP
            db_path: Database path for local mode
            track_proxy_stats: If True, also track proxy performance
        """
        self.api_url = api_url.rstrip("/")
        self.use_local = use_local
        self.db_path = db_path
        self.track_proxy_stats = track_proxy_stats
        self._active_sessions: dict[str, TrackedSession] = {}
        self._db = None
        self._event_logger = None
        self._proxy_stats_manager = None

        if use_local:
            self._init_local()

    def _init_local(self) -> None:
        """Initialize local database access"""
        try:
            from .database_logger import DatabaseLogger
            from .event_logger import EventLogger

            self._db = DatabaseLogger(db_path=self.db_path)
            self._event_logger = EventLogger(log_file="logs/session_events.log")
            logger.info("SessionTracker: Using local database mode")
        except ImportError:
            logger.warning("SessionTracker: Local modules not available, using remote mode")
            self.use_local = False

        # Initialize proxy stats manager for IP health tracking
        if self.track_proxy_stats:
            try:
                from src.proxy.stats import ProxyStatsManager

                self._proxy_stats_manager = ProxyStatsManager()
                logger.info("SessionTracker: Proxy stats tracking enabled")
            except ImportError:
                logger.warning("SessionTracker: ProxyStatsManager not available")
                self._proxy_stats_manager = None

    def start_session(
        self,
        profile_id: str,
        device: str = "desktop",
        target_url: str = None,
        proxy: str = None,
        country: str = None,
        session_id: str = None,
    ) -> str:
        """
        Start tracking a new session.

        Args:
            profile_id: AdsPower profile ID
            device: Device type (desktop/mobile)
            target_url: Target URL
            proxy: Proxy being used (e.g., "geo.iproyal.com:12321" or "192.168.1.1:8080")
            country: Country code (used for proxy stats grouping)
            session_id: Optional custom session ID

        Returns:
            Session ID
        """
        session_id = session_id or str(uuid.uuid4())

        session = TrackedSession(
            session_id=session_id,
            profile_id=profile_id,
            device=device,
            target_url=target_url,
            proxy=proxy,
            country=country or "unknown",
        )

        self._active_sessions[session_id] = session

        # Log to API/database
        if self.use_local and self._db:
            self._db.save_event(
                session_id,
                "session_start",
                {
                    "profile_id": profile_id,
                    "device": device,
                    "target_url": target_url,
                    "proxy": proxy,
                    "country": country,
                },
            )
            if self._event_logger:
                self._event_logger.log_session_start(
                    session_id, profile_id, device, target_url, proxy, country
                )
        else:
            self._send_to_api(
                "session_start",
                session_id,
                {
                    "profile_id": profile_id,
                    "device": device,
                    "target_url": target_url,
                    "proxy": proxy,
                    "country": country,
                },
            )

        # Also notify the running API server (if available)
        self._register_active_session(session)

        logger.debug(f"Session started: {session_id[:8]}...")
        return session_id

    def end_session(
        self, session_id: str, success: bool = True, error: str = None, latency_ms: int = None
    ) -> None:
        """
        End a tracked session.

        Also records proxy success/failure if proxy was used.

        Args:
            session_id: Session ID to end
            success: Whether session was successful
            error: Error message if failed
            latency_ms: Optional latency for proxy stats (if not provided, uses session duration)
        """
        session = self._active_sessions.pop(session_id, None)

        if not session:
            logger.warning(f"Session not found: {session_id}")
            return

        # Calculate duration
        start = datetime.fromisoformat(session.start_time.replace("Z", "+00:00"))
        duration = (datetime.now(timezone.utc) - start).total_seconds()

        # Record proxy stats (if proxy was used)
        if session.proxy and self._proxy_stats_manager:
            try:
                if success:
                    # Use provided latency or calculate from duration
                    proxy_latency = latency_ms or int(duration * 1000)
                    self._proxy_stats_manager.record_success(
                        proxy_id=session.proxy,
                        country=session.country or "unknown",
                        latency_ms=proxy_latency,
                        session_id=session_id,
                    )
                    logger.debug(f"Recorded proxy success: {session.proxy}")
                else:
                    was_disabled = self._proxy_stats_manager.record_failure(
                        proxy_id=session.proxy,
                        country=session.country or "unknown",
                        error=error,
                        session_id=session_id,
                    )
                    if was_disabled:
                        logger.warning(f"Proxy auto-disabled due to failures: {session.proxy}")
                    else:
                        logger.debug(f"Recorded proxy failure: {session.proxy}")
            except Exception as e:
                logger.warning(f"Failed to record proxy stats: {e}")

        # Log to API/database
        if self.use_local and self._db:
            self._db.save_session(
                {
                    "id": session_id,
                    "profile_id": session.profile_id,
                    "device": session.device,
                    "target_url": session.target_url,
                    "proxy": session.proxy,
                    "country": session.country,
                    "start_time": session.start_time,
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "duration": duration,
                    "success": success,
                    "error": error,
                }
            )
            self._db.save_event(
                session_id,
                "session_end",
                {"success": success, "duration": duration, "error": error},
            )
            if self._event_logger:
                self._event_logger.log_session_end(session_id, success, duration, error)
        else:
            self._send_to_api(
                "session_end",
                session_id,
                {"success": success, "duration": duration, "error": error},
            )

        # Notify API server
        self._unregister_active_session(session_id, success, duration, error)

        logger.debug(
            f"Session ended: {session_id[:8]}... (success={success}, duration={duration:.1f}s)"
        )

    def log_event(self, session_id: str, event_type: str, data: dict[str, Any] = None) -> None:
        """
        Log an event for a session.

        Args:
            session_id: Session ID
            event_type: Event type (navigation, click, scroll, error, etc.)
            data: Event data
        """
        data = data or {}

        # Add to session events
        if session_id in self._active_sessions:
            self._active_sessions[session_id].events.append(
                {
                    "type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": data,
                }
            )

        # Log to API/database
        if self.use_local and self._db:
            self._db.save_event(session_id, event_type, data)
        else:
            self._send_to_api(event_type, session_id, data)

    def log_navigation(
        self, session_id: str, url: str, success: bool = True, latency_ms: int = None
    ) -> None:
        """Log navigation event"""
        self.log_event(
            session_id, "navigation", {"url": url, "success": success, "latency_ms": latency_ms}
        )

    def log_click(self, session_id: str, element: str = None, url: str = None) -> None:
        """Log click event"""
        self.log_event(session_id, "click", {"element": element, "url": url})

    def log_scroll(self, session_id: str, direction: str, amount: int = None) -> None:
        """Log scroll event"""
        self.log_event(session_id, "scroll", {"direction": direction, "amount": amount})

    def log_error(self, session_id: str, error: str, error_type: str = None) -> None:
        """Log error event"""
        self.log_event(session_id, "error", {"error": error, "error_type": error_type})

    def get_active_sessions(self) -> dict[str, TrackedSession]:
        """Get all active sessions"""
        return self._active_sessions.copy()

    def get_active_count(self) -> int:
        """Get count of active sessions"""
        return len(self._active_sessions)

    def _send_to_api(self, event_type: str, session_id: str, data: dict[str, Any]) -> None:
        """Send event to API server"""
        try:
            # This notifies the API's WebSocket clients
            # For now, we'll use direct database if API is not available
            pass  # Events are stored in database directly
        except Exception as e:
            logger.debug(f"API notification skipped: {e}")

    def _register_active_session(self, session: TrackedSession) -> None:
        """Register session with API server for active session tracking via HTTP"""
        try:
            response = requests.post(
                f"{self.api_url}/api/sessions/register",
                json={
                    "session_id": session.session_id,
                    "profile_id": session.profile_id,
                    "device": session.device,
                    "target_url": session.target_url,
                    "proxy": session.proxy,
                    "country": session.country,
                },
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Session registered with API (active: {data.get('active_count', 0)})")
            else:
                logger.warning(f"Failed to register session with API: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"API not available for session registration: {e}")

    def _unregister_active_session(
        self, session_id: str, success: bool, duration: float, error: str = None
    ) -> None:
        """Unregister session from API server via HTTP"""
        try:
            response = requests.post(
                f"{self.api_url}/api/sessions/end",
                json={
                    "session_id": session_id,
                    "success": success,
                    "duration": duration,
                    "error": error,
                },
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                logger.debug(
                    f"Session unregistered from API (active: {data.get('active_count', 0)})"
                )
            else:
                logger.warning(f"Failed to unregister session from API: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"API not available for session unregistration: {e}")


# Global tracker instance
_tracker: SessionTracker | None = None


def get_tracker(
    api_url: str = "http://localhost:8000",
    use_local: bool = True,
    db_path: str = "data/bot_events.db",
) -> SessionTracker:
    """
    Get or create the global session tracker.

    Args:
        api_url: API server URL
        use_local: Use local database mode
        db_path: Database path

    Returns:
        SessionTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = SessionTracker(api_url, use_local, db_path)
    return _tracker
