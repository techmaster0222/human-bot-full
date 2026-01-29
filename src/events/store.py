"""
SQLite-backed event storage for the event logging pipeline.

Provides:
- Append-only event storage
- Indexed queries by session, type, timestamp, proxy
- JSON export for audits
- Statistics and aggregations
"""

import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator
from dataclasses import dataclass

from loguru import logger

from .types import Event, EventType


@dataclass
class EventQueryResult:
    """Result of an event query with pagination info."""
    events: List[Event]
    total_count: int
    page: int
    page_size: int
    has_more: bool


class EventStore:
    """
    SQLite-backed storage for events.
    
    Features:
    - Append-only writes (events are immutable)
    - Indexed queries on session_id, event_type, timestamp, proxy_id
    - JSON export for audit purposes
    - Statistics aggregation
    
    Thread-safety: Uses connection pooling with context managers.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize EventStore.
        
        Args:
            db_path: Path to SQLite database. Defaults to data/events.db
        """
        if db_path is None:
            # Default to project data directory
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "events.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"EventStore initialized: {self.db_path}")
    
    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Initialize the database schema."""
        with self._get_connection() as conn:
            # Create events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    profile_id TEXT,
                    proxy_id TEXT,
                    ip TEXT,
                    latency_ms INTEGER,
                    success INTEGER,
                    score INTEGER,
                    os TEXT,
                    vps_id TEXT,
                    metadata TEXT
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session 
                ON events(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON events(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_proxy 
                ON events(proxy_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_vps 
                ON events(vps_id)
            """)
            
            conn.commit()
    
    def append(self, event: Event) -> bool:
        """
        Append an event to the store.
        
        Events are immutable - once written, they cannot be modified.
        
        Args:
            event: Event to store
            
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO events (
                        event_id, timestamp, event_type, session_id,
                        profile_id, proxy_id, ip, latency_ms,
                        success, score, os, vps_id, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.timestamp,
                    event.event_type.value,
                    event.session_id,
                    event.profile_id,
                    event.proxy_id,
                    event.ip,
                    event.latency_ms,
                    1 if event.success else (0 if event.success is False else None),
                    event.score,
                    event.os,
                    event.vps_id,
                    json.dumps(event.metadata) if event.metadata else None
                ))
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Event already exists: {event.event_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to append event: {e}")
            return False
    
    def append_batch(self, events: List[Event]) -> int:
        """
        Append multiple events in a single transaction.
        
        Args:
            events: List of events to store
            
        Returns:
            Number of events successfully stored
        """
        if not events:
            return 0
        
        count = 0
        try:
            with self._get_connection() as conn:
                for event in events:
                    try:
                        conn.execute("""
                            INSERT INTO events (
                                event_id, timestamp, event_type, session_id,
                                profile_id, proxy_id, ip, latency_ms,
                                success, score, os, vps_id, metadata
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            event.event_id,
                            event.timestamp,
                            event.event_type.value,
                            event.session_id,
                            event.profile_id,
                            event.proxy_id,
                            event.ip,
                            event.latency_ms,
                            1 if event.success else (0 if event.success is False else None),
                            event.score,
                            event.os,
                            event.vps_id,
                            json.dumps(event.metadata) if event.metadata else None
                        ))
                        count += 1
                    except sqlite3.IntegrityError:
                        continue
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to append batch: {e}")
        
        return count
    
    def get_event(self, event_id: str) -> Optional[Event]:
        """Get a single event by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM events WHERE event_id = ?",
                (event_id,)
            )
            row = cursor.fetchone()
            if row:
                return Event.from_row(dict(row))
        return None
    
    def get_events_by_session(
        self,
        session_id: str,
        event_types: Optional[List[EventType]] = None
    ) -> List[Event]:
        """
        Get all events for a session.
        
        Args:
            session_id: Session ID to query
            event_types: Optional filter by event types
            
        Returns:
            List of events ordered by timestamp
        """
        with self._get_connection() as conn:
            if event_types:
                type_values = [t.value for t in event_types]
                placeholders = ",".join("?" * len(type_values))
                cursor = conn.execute(f"""
                    SELECT * FROM events 
                    WHERE session_id = ? AND event_type IN ({placeholders})
                    ORDER BY timestamp ASC
                """, [session_id] + type_values)
            else:
                cursor = conn.execute("""
                    SELECT * FROM events 
                    WHERE session_id = ?
                    ORDER BY timestamp ASC
                """, (session_id,))
            
            return [Event.from_row(dict(row)) for row in cursor.fetchall()]
    
    def query_events(
        self,
        event_type: Optional[EventType] = None,
        session_id: Optional[str] = None,
        proxy_id: Optional[str] = None,
        vps_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        order_desc: bool = True
    ) -> EventQueryResult:
        """
        Query events with filters and pagination.
        
        Args:
            event_type: Filter by event type
            session_id: Filter by session ID
            proxy_id: Filter by proxy ID
            vps_id: Filter by VPS ID
            start_time: Filter events after this time
            end_time: Filter events before this time
            success: Filter by success status
            page: Page number (1-indexed)
            page_size: Number of events per page
            order_desc: Order by timestamp descending (newest first)
            
        Returns:
            EventQueryResult with events and pagination info
        """
        conditions = []
        params = []
        
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type.value)
        
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if proxy_id:
            conditions.append("proxy_id = ?")
            params.append(proxy_id)
        
        if vps_id:
            conditions.append("vps_id = ?")
            params.append(vps_id)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        if success is not None:
            conditions.append("success = ?")
            params.append(1 if success else 0)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order = "DESC" if order_desc else "ASC"
        offset = (page - 1) * page_size
        
        with self._get_connection() as conn:
            # Get total count
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM events WHERE {where_clause}",
                params
            )
            total_count = cursor.fetchone()["count"]
            
            # Get page of events
            cursor = conn.execute(f"""
                SELECT * FROM events 
                WHERE {where_clause}
                ORDER BY timestamp {order}
                LIMIT ? OFFSET ?
            """, params + [page_size, offset])
            
            events = [Event.from_row(dict(row)) for row in cursor.fetchall()]
        
        return EventQueryResult(
            events=events,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=(offset + len(events)) < total_count
        )
    
    def get_session_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get a timeline view of events for a session.
        
        Returns simplified event data for timeline display.
        """
        events = self.get_events_by_session(session_id)
        return [
            {
                "timestamp": e.timestamp,
                "event_type": e.event_type.value,
                "success": e.success,
                "latency_ms": e.latency_ms,
                "metadata": e.metadata
            }
            for e in events
        ]
    
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        vps_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics for events.
        
        Args:
            start_time: Filter events after this time
            end_time: Filter events before this time
            vps_id: Filter by VPS ID
            
        Returns:
            Dictionary with statistics
        """
        conditions = []
        params = []
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        if vps_id:
            conditions.append("vps_id = ?")
            params.append(vps_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with self._get_connection() as conn:
            # Total events
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM events WHERE {where_clause}",
                params
            )
            total_events = cursor.fetchone()["count"]
            
            # Events by type
            cursor = conn.execute(f"""
                SELECT event_type, COUNT(*) as count 
                FROM events 
                WHERE {where_clause}
                GROUP BY event_type
            """, params)
            events_by_type = {row["event_type"]: row["count"] for row in cursor.fetchall()}
            
            # Unique sessions
            cursor = conn.execute(f"""
                SELECT COUNT(DISTINCT session_id) as count 
                FROM events 
                WHERE {where_clause}
            """, params)
            unique_sessions = cursor.fetchone()["count"]
            
            # Success rate for session events
            cursor = conn.execute(f"""
                SELECT 
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failures
                FROM events 
                WHERE {where_clause} AND success IS NOT NULL
            """, params)
            row = cursor.fetchone()
            successes = row["successes"] or 0
            failures = row["failures"] or 0
            total_with_status = successes + failures
            success_rate = (successes / total_with_status * 100) if total_with_status > 0 else 0
            
            # Average latency
            cursor = conn.execute(f"""
                SELECT AVG(latency_ms) as avg_latency 
                FROM events 
                WHERE {where_clause} AND latency_ms IS NOT NULL
            """, params)
            avg_latency = cursor.fetchone()["avg_latency"] or 0
        
        return {
            "total_events": total_events,
            "unique_sessions": unique_sessions,
            "events_by_type": events_by_type,
            "success_count": successes,
            "failure_count": failures,
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2)
        }
    
    def export_to_json(
        self,
        output_path: Path,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Export events to JSON file for auditing.
        
        Args:
            output_path: Path to output JSON file
            session_id: Optional filter by session
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            Number of events exported
        """
        conditions = []
        params = []
        
        if session_id:
            conditions.append("session_id = ?")
            params.append(session_id)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        events = []
        with self._get_connection() as conn:
            cursor = conn.execute(f"""
                SELECT * FROM events 
                WHERE {where_clause}
                ORDER BY timestamp ASC
            """, params)
            
            for row in cursor.fetchall():
                event = Event.from_row(dict(row))
                events.append(event.to_dict())
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump({
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "count": len(events),
                "events": events
            }, f, indent=2)
        
        logger.info(f"Exported {len(events)} events to {output_path}")
        return len(events)
    
    def cleanup_old_events(self, days: int = 30) -> int:
        """
        Delete events older than specified days.
        
        Args:
            days: Delete events older than this many days
            
        Returns:
            Number of events deleted
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM events WHERE timestamp < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()
        
        logger.info(f"Deleted {deleted} events older than {days} days")
        return deleted
    
    def get_recent_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent sessions with summary info.
        
        Returns list of session summaries for dashboard.
        """
        with self._get_connection() as conn:
            # Get distinct sessions with their first and last events
            cursor = conn.execute("""
                SELECT 
                    session_id,
                    profile_id,
                    proxy_id,
                    vps_id,
                    os,
                    MIN(timestamp) as started_at,
                    MAX(timestamp) as ended_at,
                    MAX(CASE WHEN event_type = 'session_completed' THEN 1 
                             WHEN event_type = 'session_failed' THEN 0 
                             ELSE NULL END) as success,
                    MAX(score) as score
                FROM events
                WHERE session_id IS NOT NULL AND session_id != ''
                GROUP BY session_id
                ORDER BY started_at DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "session_id": row["session_id"],
                    "profile_id": row["profile_id"],
                    "proxy_id": row["proxy_id"],
                    "vps_id": row["vps_id"],
                    "os": row["os"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "success": bool(row["success"]) if row["success"] is not None else None,
                    "score": row["score"]
                })
            
            return sessions
