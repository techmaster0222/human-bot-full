"""
Events module for centralized event logging.

This module provides:
- EventType: Enum of all event types
- Event: Structured event dataclass
- EventLogger: Async-safe event logger
- EventStore: SQLite-backed event storage
"""

from .logger import EventLogger
from .store import EventQueryResult, EventStore
from .types import (
    Event,
    EventType,
    create_behavior_event,
    create_error_event,
    create_profile_event,
    create_proxy_event,
    create_session_event,
)

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
