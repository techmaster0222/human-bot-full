"""
Events module for centralized event logging.

This module provides:
- EventType: Enum of all event types
- Event: Structured event dataclass
- EventLogger: Async-safe event logger
- EventStore: SQLite-backed event storage
"""

from .types import (
    EventType,
    Event,
    create_session_event,
    create_profile_event,
    create_proxy_event,
    create_behavior_event,
    create_error_event,
)
from .store import EventStore, EventQueryResult
from .logger import EventLogger

__all__ = [
    "EventType",
    "Event",
    "EventStore",
    "EventQueryResult",
    "EventLogger",
    "create_session_event",
    "create_profile_event",
    "create_proxy_event",
    "create_behavior_event",
    "create_error_event",
]
