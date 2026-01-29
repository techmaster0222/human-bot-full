"""
Reputation Store
SQLite-based storage for IP reputation data with JSON export.

PERSISTENCE MODEL
=================
SQLite is the PRIMARY source of truth for:
  - Session scores
  - IP reputation tiers
  - Reuse counters
  - Cooldown timestamps

JSON export is used ONLY for:
  - Audit logs
  - Debugging
  - Offline inspection

IMPORTANT: No logic may depend on JSON files.
All queries and decisions MUST use SQLite.
"""

import json
import sqlite3
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager
from loguru import logger

from ..core.constants import ReputationTier, DEFAULT_DB_FILENAME


@dataclass
class ReputationRecord:
    """
    A single reputation record for a session/profile.
    """
    session_id: str
    profile_id: str
    proxy_session: str
    score: int
    tier: str  # ReputationTier value
    reuse_count: int
    signals: List[str]
    country: str
    os: str
    vps_id: str
    created_at: str  # ISO format
    duration_seconds: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ReputationRecord":
        """Create from SQLite row"""
        return cls(
            session_id=row["session_id"],
            profile_id=row["profile_id"],
            proxy_session=row["proxy_session"],
            score=row["score"],
            tier=row["tier"],
            reuse_count=row["reuse_count"],
            signals=json.loads(row["signals"]),
            country=row["country"],
            os=row["os"],
            vps_id=row["vps_id"],
            created_at=row["created_at"],
            duration_seconds=row["duration_seconds"],
            error=row["error"]
        )


class ReputationStore:
    """
    SQLite-based storage for reputation data.
    
    Features:
    - Persistent storage across runs
    - Query by profile, session, tier
    - Track reuse counts
    - JSON export for audit
    
    Schema:
        CREATE TABLE reputation (
            session_id TEXT PRIMARY KEY,
            profile_id TEXT,
            proxy_session TEXT,
            score INTEGER,
            tier TEXT,
            reuse_count INTEGER,
            signals TEXT,  -- JSON array
            country TEXT,
            os TEXT,
            vps_id TEXT,
            created_at TEXT,
            duration_seconds REAL,
            error TEXT
        );
    
    Usage:
        store = ReputationStore(db_path=Path("data/reputation.db"))
        
        # Save a record
        store.save_record(record)
        
        # Query
        records = store.get_by_profile(profile_id)
        reuse_count = store.get_reuse_count(profile_id)
        
        # Export
        store.export_to_json(Path("audit.json"))
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize reputation store.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or Path("data") / DEFAULT_DB_FILENAME
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        
        logger.info(f"ReputationStore initialized (db: {self.db_path})")
    
    def _init_database(self):
        """Initialize the database schema"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reputation (
                    session_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    proxy_session TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    reuse_count INTEGER DEFAULT 0,
                    signals TEXT NOT NULL,
                    country TEXT,
                    os TEXT,
                    vps_id TEXT,
                    created_at TEXT NOT NULL,
                    duration_seconds REAL DEFAULT 0,
                    error TEXT
                )
            """)
            
            # Index for profile queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_profile_id ON reputation(profile_id)
            """)
            
            # Index for tier queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tier ON reputation(tier)
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_record(self, record: ReputationRecord):
        """
        Save a reputation record.
        
        Args:
            record: ReputationRecord to save
        """
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO reputation (
                    session_id, profile_id, proxy_session, score, tier,
                    reuse_count, signals, country, os, vps_id,
                    created_at, duration_seconds, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.session_id,
                record.profile_id,
                record.proxy_session,
                record.score,
                record.tier,
                record.reuse_count,
                json.dumps(record.signals),
                record.country,
                record.os,
                record.vps_id,
                record.created_at,
                record.duration_seconds,
                record.error
            ))
            conn.commit()
    
    def get_record(self, session_id: str) -> Optional[ReputationRecord]:
        """Get a record by session ID"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM reputation WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            if row:
                return ReputationRecord.from_row(row)
        return None
    
    def get_by_profile(self, profile_id: str) -> List[ReputationRecord]:
        """Get all records for a profile"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM reputation WHERE profile_id = ? ORDER BY created_at DESC",
                (profile_id,)
            )
            return [ReputationRecord.from_row(row) for row in cursor.fetchall()]
    
    def get_by_tier(self, tier: ReputationTier) -> List[ReputationRecord]:
        """Get all records with a specific tier"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM reputation WHERE tier = ? ORDER BY created_at DESC",
                (tier.value,)
            )
            return [ReputationRecord.from_row(row) for row in cursor.fetchall()]
    
    def get_reuse_count(self, profile_id: str) -> int:
        """
        Get the reuse count for a profile.
        
        Returns the maximum reuse_count from all records for this profile.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT MAX(reuse_count) as max_reuse FROM reputation WHERE profile_id = ?",
                (profile_id,)
            )
            row = cursor.fetchone()
            if row and row["max_reuse"] is not None:
                return row["max_reuse"]
        return 0
    
    def get_latest_for_profile(self, profile_id: str) -> Optional[ReputationRecord]:
        """Get the most recent record for a profile"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM reputation WHERE profile_id = ? ORDER BY created_at DESC LIMIT 1",
                (profile_id,)
            )
            row = cursor.fetchone()
            if row:
                return ReputationRecord.from_row(row)
        return None
    
    def get_all_records(self, limit: int = 1000) -> List[ReputationRecord]:
        """Get all records (with optional limit)"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM reputation ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [ReputationRecord.from_row(row) for row in cursor.fetchall()]
    
    def get_record_count(self) -> int:
        """Get total number of records"""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM reputation")
            return cursor.fetchone()["count"]
    
    def get_tier_counts(self) -> Dict[str, int]:
        """Get count of records by tier"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT tier, COUNT(*) as count FROM reputation GROUP BY tier"
            )
            return {row["tier"]: row["count"] for row in cursor.fetchall()}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics"""
        with self._get_connection() as conn:
            # Total records
            cursor = conn.execute("SELECT COUNT(*) as total FROM reputation")
            total = cursor.fetchone()["total"]
            
            # Average score
            cursor = conn.execute("SELECT AVG(score) as avg_score FROM reputation")
            avg_score = cursor.fetchone()["avg_score"] or 0
            
            # Tier distribution
            tier_counts = self.get_tier_counts()
            
            # Average duration
            cursor = conn.execute("SELECT AVG(duration_seconds) as avg_duration FROM reputation")
            avg_duration = cursor.fetchone()["avg_duration"] or 0
            
            return {
                "total_records": total,
                "avg_score": round(avg_score, 2),
                "avg_duration": round(avg_duration, 2),
                "tier_distribution": tier_counts,
            }
    
    def export_to_json(self, output_path: Path, limit: int = None) -> int:
        """
        Export records to JSON file.
        
        Args:
            output_path: Path to write JSON file
            limit: Maximum records to export (None for all)
            
        Returns:
            Number of records exported
        """
        records = self.get_all_records(limit=limit or 100000)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                [r.to_dict() for r in records],
                f,
                indent=2,
                default=str
            )
        
        logger.info(f"Exported {len(records)} records to {output_path}")
        return len(records)
    
    def export_audit_log(self, session_id: str) -> Optional[Dict]:
        """
        Export a single session's audit log in the mandatory format.
        
        Args:
            session_id: Session ID to export
            
        Returns:
            Dict in audit format or None if not found
        """
        record = self.get_record(session_id)
        if not record:
            return None
        
        return {
            "session_id": record.session_id,
            "profile_id": record.profile_id,
            "proxy_session": record.proxy_session,
            "ip_tier": record.tier,
            "score": record.score,
            "signals": record.signals,
            "reuse_count": record.reuse_count,
            "os": record.os,
            "vps_id": record.vps_id,
            "country": record.country,
            "duration_seconds": record.duration_seconds,
            "created_at": record.created_at,
        }
    
    def delete_by_profile(self, profile_id: str) -> int:
        """
        Delete all records for a profile.
        
        Args:
            profile_id: Profile ID to delete records for
            
        Returns:
            Number of records deleted
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM reputation WHERE profile_id = ?",
                (profile_id,)
            )
            conn.commit()
            return cursor.rowcount
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """
        Delete records older than specified days.
        
        Args:
            days: Delete records older than this many days
            
        Returns:
            Number of records deleted
        """
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM reputation WHERE created_at < ?",
                (cutoff,)
            )
            conn.commit()
            deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} records older than {days} days")
        
        return deleted
