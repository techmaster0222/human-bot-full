"""
Database Logger - SQLite storage for sessions and events
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DatabaseLogger:
    """
    SQLite database logger for storing sessions and events.

    Features:
    - Session tracking with metadata
    - Event storage with filtering
    - Statistics calculation
    - Query capabilities

    Usage:
        db = DatabaseLogger(db_path="data/bot_events.db")
        db.save_session({...})
        db.save_event(session_id, "click", {...})
        stats = db.get_statistics()
    """

    def __init__(self, db_path: str = "data/bot_events.db"):
        """
        Initialize database logger.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

        # Create data directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self) -> None:
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT,
                    device TEXT,
                    target_url TEXT,
                    proxy TEXT,
                    country TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration REAL,
                    success INTEGER,
                    error TEXT,
                    metadata TEXT
                )
            """)

            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_start
                ON sessions(start_time)
            """)

            conn.commit()

    def save_session(self, session_data: dict[str, Any]) -> None:
        """
        Save session to database.

        Args:
            session_data: Session data dictionary with keys:
                - id: Session ID
                - profile_id: Profile ID
                - device: Device type
                - target_url: Target URL
                - proxy: Proxy used
                - country: Country
                - start_time: Start timestamp
                - end_time: End timestamp
                - duration: Duration in seconds
                - success: Success boolean
                - error: Error message (if any)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO sessions
                (id, profile_id, device, target_url, proxy, country,
                 start_time, end_time, duration, success, error, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_data.get("id"),
                    session_data.get("profile_id"),
                    session_data.get("device"),
                    session_data.get("target_url"),
                    session_data.get("proxy"),
                    session_data.get("country"),
                    session_data.get("start_time"),
                    session_data.get("end_time"),
                    session_data.get("duration"),
                    1 if session_data.get("success") else 0,
                    session_data.get("error"),
                    json.dumps(session_data.get("metadata", {})),
                ),
            )

            conn.commit()

    def save_event(
        self,
        session_id: str,
        event_type: str,
        data: dict[str, Any],
        timestamp: str | None = None,
    ) -> int:
        """
        Save event to database.

        Args:
            session_id: Session ID
            event_type: Event type
            data: Event data
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Event ID
        """
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO events (session_id, event_type, timestamp, data)
                VALUES (?, ?, ?, ?)
            """,
                (session_id, event_type, timestamp, json.dumps(data)),
            )

            conn.commit()
            return cursor.lastrowid

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Get session by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_session(row)

    def get_sessions(
        self,
        limit: int = 100,
        offset: int = 0,
        success: bool | None = None,
        country: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get sessions with optional filtering.

        Args:
            limit: Maximum number of sessions
            offset: Offset for pagination
            success: Filter by success status
            country: Filter by country

        Returns:
            List of session dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM sessions WHERE 1=1"
            params = []

            if success is not None:
                query += " AND success = ?"
                params.append(1 if success else 0)

            if country:
                query += " AND country = ?"
                params.append(country)

            query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_session(row) for row in rows]

    def get_events(
        self,
        session_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get events with optional filtering.

        Args:
            session_id: Filter by session ID
            event_type: Filter by event type
            limit: Maximum number of events
            offset: Offset for pagination

        Returns:
            List of event dictionaries
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)

            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_event(row) for row in rows]

    def get_statistics(self) -> dict[str, Any]:
        """
        Get overall statistics.

        Returns:
            Statistics dictionary with:
            - total_sessions
            - successful_sessions
            - failed_sessions
            - total_events
            - average_duration
            - success_rate
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total sessions
            cursor.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            # Successful sessions
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE success = 1")
            successful_sessions = cursor.fetchone()[0]

            # Failed sessions
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE success = 0")
            failed_sessions = cursor.fetchone()[0]

            # Total events
            cursor.execute("SELECT COUNT(*) FROM events")
            total_events = cursor.fetchone()[0]

            # Average duration
            cursor.execute("""
                SELECT AVG(duration) FROM sessions
                WHERE duration IS NOT NULL AND duration > 0
            """)
            avg_duration = cursor.fetchone()[0] or 0.0

            # Success rate
            success_rate = successful_sessions / total_sessions * 100 if total_sessions > 0 else 0.0

            return {
                "total_sessions": total_sessions,
                "successful_sessions": successful_sessions,
                "failed_sessions": failed_sessions,
                "total_events": total_events,
                "average_duration": round(avg_duration, 2),
                "success_rate": round(success_rate, 2),
            }

    def get_event_counts_by_type(self) -> dict[str, int]:
        """Get event counts grouped by type"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM events
                GROUP BY event_type
                ORDER BY count DESC
            """)
            return {row["event_type"]: row["count"] for row in cursor.fetchall()}

    def delete_old_events(self, days: int = 30) -> int:
        """
        Delete events older than specified days.

        Args:
            days: Delete events older than this many days

        Returns:
            Number of events deleted
        """
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    def _row_to_session(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert database row to session dictionary"""
        return {
            "id": row["id"],
            "profile_id": row["profile_id"],
            "device": row["device"],
            "target_url": row["target_url"],
            "proxy": row["proxy"],
            "country": row["country"],
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "duration": row["duration"],
            "success": bool(row["success"]),
            "error": row["error"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
        }

    def _row_to_event(self, row: sqlite3.Row) -> dict[str, Any]:
        """Convert database row to event dictionary"""
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "event_type": row["event_type"],
            "timestamp": row["timestamp"],
            "data": json.loads(row["data"]) if row["data"] else {},
        }
