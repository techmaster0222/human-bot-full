"""
Async-safe event logger for the centralized event logging pipeline.

Provides:
- Non-blocking event logging via asyncio queue
- Singleton pattern for global access
- Batch writing for performance
- Context managers for session/profile lifecycle
"""

import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from queue import Queue, Empty
import atexit

from loguru import logger as log

from .types import (
    Event,
    EventType,
    create_session_event,
    create_profile_event,
    create_proxy_event,
    create_behavior_event,
    create_error_event,
)
from .store import EventStore


class EventLogger:
    """
    Async-safe centralized event logger.
    
    Features:
    - Non-blocking writes via background thread
    - Batch writing for better performance
    - Thread-safe for use from sync and async code
    - Singleton pattern for global access
    
    Usage:
        logger = EventLogger.get_instance()
        logger.log_session_created(session_id, profile_id, ...)
        
        # Or use context manager
        with logger.session_context(session_id, profile_id, ...):
            # session events automatically logged
    """
    
    _instance: Optional["EventLogger"] = None
    _lock = threading.Lock()
    
    def __init__(
        self,
        store: Optional[EventStore] = None,
        db_path: Optional[Path] = None,
        batch_size: int = 10,
        flush_interval: float = 1.0,
        enabled: bool = True
    ):
        """
        Initialize EventLogger.
        
        Args:
            store: EventStore instance (created if not provided)
            db_path: Path to SQLite database (used if store not provided)
            batch_size: Number of events to batch before writing
            flush_interval: Seconds between automatic flushes
            enabled: Whether logging is enabled
        """
        self._store = store or EventStore(db_path)
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._enabled = enabled
        
        # Thread-safe queue for events
        self._queue: Queue = Queue()
        self._buffer: List[Event] = []
        
        # Background writer thread
        self._running = True
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="EventLoggerWriter"
        )
        self._writer_thread.start()
        
        # Register cleanup on exit
        atexit.register(self.shutdown)
        
        log.info("EventLogger initialized")
    
    @classmethod
    def get_instance(
        cls,
        store: Optional[EventStore] = None,
        db_path: Optional[Path] = None,
        **kwargs
    ) -> "EventLogger":
        """
        Get the singleton instance.
        
        Creates instance on first call, returns existing instance thereafter.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(store=store, db_path=db_path, **kwargs)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown()
                cls._instance = None
    
    def _writer_loop(self):
        """Background thread that writes events to store."""
        while self._running:
            try:
                # Wait for event or timeout
                try:
                    event = self._queue.get(timeout=self._flush_interval)
                    self._buffer.append(event)
                except Empty:
                    pass
                
                # Flush if buffer is full or on timeout
                if len(self._buffer) >= self._batch_size:
                    self._flush()
                elif self._buffer:
                    # Flush on timeout even with partial buffer
                    self._flush()
                    
            except Exception as e:
                log.error(f"EventLogger writer error: {e}")
        
        # Final flush on shutdown
        self._flush()
    
    def _flush(self):
        """Flush buffered events to store."""
        if not self._buffer:
            return
        
        events = self._buffer.copy()
        self._buffer.clear()
        
        try:
            count = self._store.append_batch(events)
            if count != len(events):
                log.warning(f"Only wrote {count}/{len(events)} events")
        except Exception as e:
            log.error(f"Failed to flush events: {e}")
    
    def shutdown(self):
        """Shutdown the logger and flush remaining events."""
        self._running = False
        if self._writer_thread.is_alive():
            self._writer_thread.join(timeout=5.0)
        self._flush()
        log.info("EventLogger shutdown complete")
    
    @property
    def enabled(self) -> bool:
        """Check if logging is enabled."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable logging."""
        self._enabled = value
    
    def log(self, event: Event):
        """
        Log an event (non-blocking).
        
        Args:
            event: Event to log
        """
        if not self._enabled:
            return
        
        self._queue.put(event)
    
    def log_sync(self, event: Event):
        """
        Log an event synchronously (blocking).
        
        Use this when you need to ensure the event is written immediately.
        """
        if not self._enabled:
            return
        
        self._store.append(event)
    
    # ==========================================================================
    # Session Events
    # ==========================================================================
    
    def log_session_created(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        proxy_id: Optional[str] = None,
        country: Optional[str] = None,
        **metadata
    ):
        """Log SESSION_CREATED event."""
        self.log(create_session_event(
            EventType.SESSION_CREATED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            proxy_id=proxy_id,
            country=country,
            **metadata
        ))
    
    def log_session_started(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        proxy_id: Optional[str] = None,
        **metadata
    ):
        """Log SESSION_STARTED event."""
        self.log(create_session_event(
            EventType.SESSION_STARTED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            proxy_id=proxy_id,
            **metadata
        ))
    
    def log_session_completed(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        proxy_id: Optional[str] = None,
        score: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        **metadata
    ):
        """Log SESSION_COMPLETED event."""
        if duration_seconds is not None:
            metadata["duration_seconds"] = duration_seconds
        self.log(create_session_event(
            EventType.SESSION_COMPLETED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            proxy_id=proxy_id,
            success=True,
            score=score,
            **metadata
        ))
    
    def log_session_failed(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        error: str,
        proxy_id: Optional[str] = None,
        **metadata
    ):
        """Log SESSION_FAILED event."""
        metadata["error"] = error
        self.log(create_session_event(
            EventType.SESSION_FAILED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            proxy_id=proxy_id,
            success=False,
            **metadata
        ))
    
    def log_session_aborted(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        reason: str,
        proxy_id: Optional[str] = None,
        **metadata
    ):
        """Log SESSION_ABORTED event."""
        metadata["reason"] = reason
        self.log(create_session_event(
            EventType.SESSION_ABORTED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            proxy_id=proxy_id,
            success=False,
            **metadata
        ))
    
    def log_session_timeout(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        timeout_seconds: float,
        proxy_id: Optional[str] = None,
        **metadata
    ):
        """Log SESSION_TIMEOUT event."""
        metadata["timeout_seconds"] = timeout_seconds
        self.log(create_session_event(
            EventType.SESSION_TIMEOUT,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            proxy_id=proxy_id,
            success=False,
            **metadata
        ))
    
    # ==========================================================================
    # Profile Events
    # ==========================================================================
    
    def log_profile_created(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        profile_name: Optional[str] = None,
        country: Optional[str] = None,
        **metadata
    ):
        """Log PROFILE_CREATED event."""
        if profile_name:
            metadata["profile_name"] = profile_name
        if country:
            metadata["country"] = country
        self.log(create_profile_event(
            EventType.PROFILE_CREATED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            **metadata
        ))
    
    def log_profile_started(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        cdp_url: Optional[str] = None,
        **metadata
    ):
        """Log PROFILE_STARTED event."""
        if cdp_url:
            metadata["cdp_url"] = cdp_url
        self.log(create_profile_event(
            EventType.PROFILE_STARTED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            **metadata
        ))
    
    def log_profile_stopped(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        **metadata
    ):
        """Log PROFILE_STOPPED event."""
        self.log(create_profile_event(
            EventType.PROFILE_STOPPED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            **metadata
        ))
    
    def log_profile_destroyed(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        **metadata
    ):
        """Log PROFILE_DESTROYED event."""
        self.log(create_profile_event(
            EventType.PROFILE_DESTROYED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            **metadata
        ))
    
    # ==========================================================================
    # Browser Events
    # ==========================================================================
    
    def log_browser_connected(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        cdp_url: Optional[str] = None,
        **metadata
    ):
        """Log BROWSER_CONNECTED event."""
        if cdp_url:
            metadata["cdp_url"] = cdp_url
        self.log(create_profile_event(
            EventType.BROWSER_CONNECTED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            **metadata
        ))
    
    def log_browser_disconnected(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        **metadata
    ):
        """Log BROWSER_DISCONNECTED event."""
        self.log(create_profile_event(
            EventType.BROWSER_DISCONNECTED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            **metadata
        ))
    
    # ==========================================================================
    # Proxy Events
    # ==========================================================================
    
    def log_proxy_assigned(
        self,
        session_id: str,
        profile_id: str,
        proxy_id: str,
        os: str,
        vps_id: str,
        ip: Optional[str] = None,
        country: Optional[str] = None,
        **metadata
    ):
        """Log PROXY_ASSIGNED event."""
        if country:
            metadata["country"] = country
        self.log(create_proxy_event(
            EventType.PROXY_ASSIGNED,
            session_id=session_id,
            profile_id=profile_id,
            proxy_id=proxy_id,
            os=os,
            vps_id=vps_id,
            ip=ip,
            **metadata
        ))
    
    def log_proxy_result(
        self,
        session_id: str,
        profile_id: str,
        proxy_id: str,
        os: str,
        vps_id: str,
        success: bool,
        ip: Optional[str] = None,
        latency_ms: Optional[int] = None,
        error: Optional[str] = None,
        **metadata
    ):
        """Log PROXY_RESULT event."""
        if error:
            metadata["error"] = error
        self.log(create_proxy_event(
            EventType.PROXY_RESULT,
            session_id=session_id,
            profile_id=profile_id,
            proxy_id=proxy_id,
            os=os,
            vps_id=vps_id,
            ip=ip,
            latency_ms=latency_ms,
            success=success,
            **metadata
        ))
    
    def log_proxy_disabled(
        self,
        proxy_id: str,
        os: str,
        vps_id: str,
        reason: str,
        **metadata
    ):
        """Log PROXY_DISABLED event."""
        metadata["reason"] = reason
        self.log(Event(
            event_type=EventType.PROXY_DISABLED,
            session_id="system",
            proxy_id=proxy_id,
            os=os,
            vps_id=vps_id,
            metadata=metadata
        ))
    
    def log_proxy_enabled(
        self,
        proxy_id: str,
        os: str,
        vps_id: str,
        **metadata
    ):
        """Log PROXY_ENABLED event."""
        self.log(Event(
            event_type=EventType.PROXY_ENABLED,
            session_id="system",
            proxy_id=proxy_id,
            os=os,
            vps_id=vps_id,
            metadata=metadata
        ))
    
    # ==========================================================================
    # Behavior Events
    # ==========================================================================
    
    def log_behavior_event(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        behavior_type: str,
        **metadata
    ):
        """Log BEHAVIOR_EVENT."""
        self.log(create_behavior_event(
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            behavior_type=behavior_type,
            **metadata
        ))
    
    def log_navigation_start(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        url: str,
        **metadata
    ):
        """Log NAVIGATION_START event."""
        metadata["url"] = url
        self.log(Event(
            event_type=EventType.NAVIGATION_START,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            metadata=metadata
        ))
    
    def log_navigation_complete(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        url: str,
        latency_ms: Optional[int] = None,
        **metadata
    ):
        """Log NAVIGATION_COMPLETE event."""
        metadata["url"] = url
        self.log(Event(
            event_type=EventType.NAVIGATION_COMPLETE,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            latency_ms=latency_ms,
            success=True,
            metadata=metadata
        ))
    
    def log_navigation_failed(
        self,
        session_id: str,
        profile_id: str,
        os: str,
        vps_id: str,
        url: str,
        error: str,
        **metadata
    ):
        """Log NAVIGATION_FAILED event."""
        metadata["url"] = url
        metadata["error"] = error
        self.log(Event(
            event_type=EventType.NAVIGATION_FAILED,
            session_id=session_id,
            profile_id=profile_id,
            os=os,
            vps_id=vps_id,
            success=False,
            metadata=metadata
        ))
    
    # ==========================================================================
    # Wave Events
    # ==========================================================================
    
    def log_wave_started(
        self,
        wave_number: int,
        session_count: int,
        os: str,
        vps_id: str,
        **metadata
    ):
        """Log WAVE_STARTED event."""
        metadata["wave_number"] = wave_number
        metadata["session_count"] = session_count
        self.log(Event(
            event_type=EventType.WAVE_STARTED,
            session_id=f"wave_{wave_number}",
            os=os,
            vps_id=vps_id,
            metadata=metadata
        ))
    
    def log_wave_completed(
        self,
        wave_number: int,
        success_count: int,
        failure_count: int,
        duration_seconds: float,
        os: str,
        vps_id: str,
        **metadata
    ):
        """Log WAVE_COMPLETED event."""
        metadata["wave_number"] = wave_number
        metadata["success_count"] = success_count
        metadata["failure_count"] = failure_count
        metadata["duration_seconds"] = duration_seconds
        self.log(Event(
            event_type=EventType.WAVE_COMPLETED,
            session_id=f"wave_{wave_number}",
            os=os,
            vps_id=vps_id,
            success=failure_count == 0,
            metadata=metadata
        ))
    
    # ==========================================================================
    # Error Events
    # ==========================================================================
    
    def log_error(
        self,
        session_id: str,
        os: str,
        vps_id: str,
        error: str,
        profile_id: Optional[str] = None,
        proxy_id: Optional[str] = None,
        **metadata
    ):
        """Log ERROR event."""
        self.log(create_error_event(
            session_id=session_id,
            os=os,
            vps_id=vps_id,
            error=error,
            profile_id=profile_id,
            proxy_id=proxy_id,
            **metadata
        ))
    
    # ==========================================================================
    # Query Methods (delegate to store)
    # ==========================================================================
    
    def get_events_by_session(self, session_id: str) -> List[Event]:
        """Get all events for a session."""
        return self._store.get_events_by_session(session_id)
    
    def get_session_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """Get timeline view for a session."""
        return self._store.get_session_timeline(session_id)
    
    def get_statistics(self, **kwargs) -> Dict[str, Any]:
        """Get event statistics."""
        return self._store.get_statistics(**kwargs)
    
    def get_recent_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent sessions summary."""
        return self._store.get_recent_sessions(limit)
    
    @property
    def store(self) -> EventStore:
        """Get the underlying EventStore."""
        return self._store
