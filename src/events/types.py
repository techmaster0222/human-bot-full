"""
Event types and schema for the centralized event logging pipeline.

This module defines:
- EventType enum for all lifecycle events
- Event dataclass for structured event storage
"""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(Enum):
    """
    All event types captured by the event logging pipeline.

    Events are categorized by lifecycle phase:
    - SESSION_*: Session-level events
    - PROFILE_*: AdsPower profile events
    - PROXY_*: Proxy assignment and result events
    - BEHAVIOR_*: Human-like behavior events
    """

    # Session lifecycle
    SESSION_CREATED = "session_created"
    SESSION_STARTED = "session_started"
    SESSION_COMPLETED = "session_completed"
    SESSION_ABORTED = "session_aborted"
    SESSION_FAILED = "session_failed"
    SESSION_TIMEOUT = "session_timeout"

    # Profile lifecycle
    PROFILE_CREATED = "profile_created"
    PROFILE_STARTED = "profile_started"
    PROFILE_STOPPED = "profile_stopped"
    PROFILE_DESTROYED = "profile_destroyed"

    # Browser/CDP lifecycle
    BROWSER_CONNECTED = "browser_connected"
    BROWSER_DISCONNECTED = "browser_disconnected"

    # Proxy events
    PROXY_ASSIGNED = "proxy_assigned"
    PROXY_RESULT = "proxy_result"
    PROXY_DISABLED = "proxy_disabled"
    PROXY_ENABLED = "proxy_enabled"

    # Behavior events
    BEHAVIOR_EVENT = "behavior_event"
    NAVIGATION_START = "navigation_start"
    NAVIGATION_COMPLETE = "navigation_complete"
    NAVIGATION_FAILED = "navigation_failed"

    # Wave/orchestration events
    WAVE_STARTED = "wave_started"
    WAVE_COMPLETED = "wave_completed"

    # Error events
    ERROR = "error"


@dataclass
class Event:
    """
    Structured event for the logging pipeline.

    All events are:
    - Timestamped (ISO-8601)
    - Uniquely identified (UUID)
    - Associated with a session
    - Tagged with OS and VPS info

    Attributes:
        event_id: Unique identifier (UUID)
        timestamp: ISO-8601 timestamp
        event_type: Type of event (EventType enum value)
        session_id: Associated session ID
        profile_id: AdsPower profile ID (optional)
        proxy_id: Proxy session ID (optional)
        ip: IP address used (optional)
        latency_ms: Latency in milliseconds (optional)
        success: Whether the operation succeeded (optional)
        score: Session/proxy score (optional)
        os: Operating system
        vps_id: VPS identifier
        metadata: Additional event-specific data
    """

    event_type: EventType
    session_id: str
    os: str
    vps_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    profile_id: str | None = None
    proxy_id: str | None = None
    ip: str | None = None
    latency_ms: int | None = None
    success: bool | None = None
    score: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        data = asdict(self)
        # Convert EventType enum to string value
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        # Convert event_type string back to enum
        data = data.copy()
        if isinstance(data.get("event_type"), str):
            data["event_type"] = EventType(data["event_type"])
        return cls(**data)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Event":
        """Create Event from SQLite row."""
        data = dict(row)
        # Parse event_type
        if isinstance(data.get("event_type"), str):
            data["event_type"] = EventType(data["event_type"])
        # Parse metadata JSON
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"]) if data["metadata"] else {}
        # Convert success integer to bool
        if data.get("success") is not None:
            data["success"] = bool(data["success"])
        return cls(**data)


# Factory functions for common events


def create_session_event(
    event_type: EventType,
    session_id: str,
    profile_id: str,
    os: str,
    vps_id: str,
    proxy_id: str | None = None,
    success: bool | None = None,
    score: int | None = None,
    **metadata,
) -> Event:
    """Create a session lifecycle event."""
    return Event(
        event_type=event_type,
        session_id=session_id,
        profile_id=profile_id,
        os=os,
        vps_id=vps_id,
        proxy_id=proxy_id,
        success=success,
        score=score,
        metadata=metadata,
    )


def create_profile_event(
    event_type: EventType, session_id: str, profile_id: str, os: str, vps_id: str, **metadata
) -> Event:
    """Create a profile lifecycle event."""
    return Event(
        event_type=event_type,
        session_id=session_id,
        profile_id=profile_id,
        os=os,
        vps_id=vps_id,
        metadata=metadata,
    )


def create_proxy_event(
    event_type: EventType,
    session_id: str,
    profile_id: str,
    proxy_id: str,
    os: str,
    vps_id: str,
    ip: str | None = None,
    latency_ms: int | None = None,
    success: bool | None = None,
    **metadata,
) -> Event:
    """Create a proxy-related event."""
    return Event(
        event_type=event_type,
        session_id=session_id,
        profile_id=profile_id,
        proxy_id=proxy_id,
        ip=ip,
        latency_ms=latency_ms,
        success=success,
        os=os,
        vps_id=vps_id,
        metadata=metadata,
    )


def create_behavior_event(
    session_id: str, profile_id: str, os: str, vps_id: str, behavior_type: str, **metadata
) -> Event:
    """Create a behavior event."""
    return Event(
        event_type=EventType.BEHAVIOR_EVENT,
        session_id=session_id,
        profile_id=profile_id,
        os=os,
        vps_id=vps_id,
        metadata={"behavior_type": behavior_type, **metadata},
    )


def create_error_event(
    session_id: str,
    os: str,
    vps_id: str,
    error: str,
    profile_id: str | None = None,
    proxy_id: str | None = None,
    **metadata,
) -> Event:
    """Create an error event."""
    return Event(
        event_type=EventType.ERROR,
        session_id=session_id,
        profile_id=profile_id,
        proxy_id=proxy_id,
        os=os,
        vps_id=vps_id,
        success=False,
        metadata={"error": error, **metadata},
    )
