"""
Proxy Statistics Manager
Tracks proxy performance metrics for data-driven rotation decisions.

Provides:
- Per-proxy success/failure tracking
- Latency statistics
- Automatic disable on consecutive failures
- Cooldown management
"""

import sqlite3
import json
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Generator

from loguru import logger


@dataclass
class ProxyStats:
    """
    Statistics for a single proxy.
    
    Used for weighted rotation decisions.
    """
    proxy_id: str
    country: str
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    total_latency_ms: int = 0
    avg_latency_ms: float = 0.0
    last_used: Optional[str] = None
    last_success: Optional[str] = None
    last_failure: Optional[str] = None
    is_disabled: bool = False
    disabled_at: Optional[str] = None
    cooldown_until: Optional[str] = None
    created_at: Optional[str] = None
    
    @property
    def total_count(self) -> int:
        """Total number of uses."""
        return self.success_count + self.failure_count
    
    @property
    def success_rate(self) -> float:
        """Success rate as a percentage (0-100)."""
        if self.total_count == 0:
            return 100.0  # No data = assume good
        return (self.success_count / self.total_count) * 100
    
    @property
    def is_in_cooldown(self) -> bool:
        """Check if proxy is currently in cooldown."""
        if not self.cooldown_until:
            return False
        try:
            cooldown_time = datetime.fromisoformat(self.cooldown_until)
            return datetime.now(timezone.utc) < cooldown_time
        except Exception:
            return False
    
    @property
    def is_available(self) -> bool:
        """Check if proxy is available for use."""
        return not self.is_disabled and not self.is_in_cooldown
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "ProxyStats":
        """Create from SQLite row."""
        return cls(
            proxy_id=row["proxy_id"],
            country=row["country"],
            success_count=row["success_count"],
            failure_count=row["failure_count"],
            consecutive_failures=row["consecutive_failures"],
            total_latency_ms=row["total_latency_ms"],
            avg_latency_ms=row["avg_latency_ms"],
            last_used=row["last_used"],
            last_success=row["last_success"],
            last_failure=row["last_failure"],
            is_disabled=bool(row["is_disabled"]),
            disabled_at=row["disabled_at"],
            cooldown_until=row["cooldown_until"],
            created_at=row["created_at"]
        )


class ProxyStatsManager:
    """
    Manages proxy performance statistics for data-driven rotation.
    
    Features:
    - Track success/failure counts per proxy
    - Calculate average latency
    - Auto-disable after consecutive failures
    - Cooldown management before re-enabling
    - SQLite persistence for durability
    
    Usage:
        manager = ProxyStatsManager()
        
        # Record result
        manager.record_success("proxy_123", latency_ms=250, country="US")
        manager.record_failure("proxy_456", error="timeout", country="US")
        
        # Get stats
        stats = manager.get_stats("proxy_123")
        
        # Get available proxies for rotation
        available = manager.get_available_proxies(country="US")
    """
    
    # Default thresholds
    DEFAULT_CONSECUTIVE_FAILURE_THRESHOLD = 3
    DEFAULT_COOLDOWN_MINUTES = 30
    
    def __init__(
        self,
        db_path: Optional[Path] = None,
        consecutive_failure_threshold: int = DEFAULT_CONSECUTIVE_FAILURE_THRESHOLD,
        cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES
    ):
        """
        Initialize ProxyStatsManager.
        
        Args:
            db_path: Path to SQLite database. Defaults to data/proxy_stats.db
            consecutive_failure_threshold: Number of consecutive failures before disable
            cooldown_minutes: Minutes to wait before re-enabling disabled proxy
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "proxy_stats.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.consecutive_failure_threshold = consecutive_failure_threshold
        self.cooldown_minutes = cooldown_minutes
        
        self._init_database()
        logger.info(f"ProxyStatsManager initialized: {self.db_path}")
    
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proxy_stats (
                    proxy_id TEXT PRIMARY KEY,
                    country TEXT NOT NULL,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    consecutive_failures INTEGER DEFAULT 0,
                    total_latency_ms INTEGER DEFAULT 0,
                    avg_latency_ms REAL DEFAULT 0,
                    last_used TEXT,
                    last_success TEXT,
                    last_failure TEXT,
                    is_disabled INTEGER DEFAULT 0,
                    disabled_at TEXT,
                    cooldown_until TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proxy_country 
                ON proxy_stats(country)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proxy_disabled 
                ON proxy_stats(is_disabled)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_proxy_last_used 
                ON proxy_stats(last_used)
            """)
            
            conn.commit()
    
    def _ensure_proxy_exists(self, conn: sqlite3.Connection, proxy_id: str, country: str):
        """Ensure a proxy record exists, creating if necessary."""
        cursor = conn.execute(
            "SELECT 1 FROM proxy_stats WHERE proxy_id = ?",
            (proxy_id,)
        )
        if cursor.fetchone() is None:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT INTO proxy_stats (proxy_id, country, created_at)
                VALUES (?, ?, ?)
            """, (proxy_id, country, now))
    
    def record_success(
        self,
        proxy_id: str,
        country: str,
        latency_ms: Optional[int] = None,
        session_id: Optional[str] = None
    ):
        """
        Record a successful proxy use.
        
        Args:
            proxy_id: Proxy identifier
            country: Country code
            latency_ms: Request latency in milliseconds
            session_id: Associated session ID (for logging)
        """
        now = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            self._ensure_proxy_exists(conn, proxy_id, country)
            
            # Get current stats for latency calculation
            cursor = conn.execute(
                "SELECT success_count, total_latency_ms FROM proxy_stats WHERE proxy_id = ?",
                (proxy_id,)
            )
            row = cursor.fetchone()
            
            new_success_count = (row["success_count"] or 0) + 1
            new_total_latency = row["total_latency_ms"] or 0
            
            if latency_ms is not None:
                new_total_latency += latency_ms
            
            # Calculate new average
            new_avg_latency = new_total_latency / new_success_count if new_success_count > 0 else 0
            
            # Update stats
            conn.execute("""
                UPDATE proxy_stats SET
                    success_count = ?,
                    consecutive_failures = 0,
                    total_latency_ms = ?,
                    avg_latency_ms = ?,
                    last_used = ?,
                    last_success = ?
                WHERE proxy_id = ?
            """, (
                new_success_count,
                new_total_latency,
                new_avg_latency,
                now,
                now,
                proxy_id
            ))
            
            conn.commit()
        
        logger.debug(f"Recorded success for proxy {proxy_id} (latency: {latency_ms}ms)")
    
    def record_failure(
        self,
        proxy_id: str,
        country: str,
        error: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Record a failed proxy use.
        
        Args:
            proxy_id: Proxy identifier
            country: Country code
            error: Error message
            session_id: Associated session ID (for logging)
            
        Returns:
            True if proxy was auto-disabled due to consecutive failures
        """
        now = datetime.now(timezone.utc).isoformat()
        was_disabled = False
        
        with self._get_connection() as conn:
            self._ensure_proxy_exists(conn, proxy_id, country)
            
            # Get current consecutive failures
            cursor = conn.execute(
                "SELECT consecutive_failures FROM proxy_stats WHERE proxy_id = ?",
                (proxy_id,)
            )
            row = cursor.fetchone()
            new_consecutive = (row["consecutive_failures"] or 0) + 1
            
            # Check if should be disabled
            should_disable = new_consecutive >= self.consecutive_failure_threshold
            
            if should_disable:
                cooldown_until = (
                    datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)
                ).isoformat()
                
                conn.execute("""
                    UPDATE proxy_stats SET
                        failure_count = failure_count + 1,
                        consecutive_failures = ?,
                        last_used = ?,
                        last_failure = ?,
                        is_disabled = 1,
                        disabled_at = ?,
                        cooldown_until = ?
                    WHERE proxy_id = ?
                """, (new_consecutive, now, now, now, cooldown_until, proxy_id))
                
                was_disabled = True
                logger.warning(
                    f"Proxy {proxy_id} auto-disabled after {new_consecutive} consecutive failures. "
                    f"Cooldown until: {cooldown_until}"
                )
            else:
                conn.execute("""
                    UPDATE proxy_stats SET
                        failure_count = failure_count + 1,
                        consecutive_failures = ?,
                        last_used = ?,
                        last_failure = ?
                    WHERE proxy_id = ?
                """, (new_consecutive, now, now, proxy_id))
            
            conn.commit()
        
        logger.debug(f"Recorded failure for proxy {proxy_id} (consecutive: {new_consecutive})")
        return was_disabled
    
    def get_stats(self, proxy_id: str) -> Optional[ProxyStats]:
        """Get statistics for a specific proxy."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM proxy_stats WHERE proxy_id = ?",
                (proxy_id,)
            )
            row = cursor.fetchone()
            if row:
                return ProxyStats.from_row(dict(row))
        return None
    
    def get_all_stats(self, country: Optional[str] = None) -> List[ProxyStats]:
        """
        Get statistics for all proxies.
        
        Args:
            country: Optional filter by country
            
        Returns:
            List of ProxyStats
        """
        with self._get_connection() as conn:
            if country:
                cursor = conn.execute(
                    "SELECT * FROM proxy_stats WHERE country = ? ORDER BY last_used DESC",
                    (country,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM proxy_stats ORDER BY last_used DESC"
                )
            
            return [ProxyStats.from_row(dict(row)) for row in cursor.fetchall()]
    
    def get_available_proxies(self, country: Optional[str] = None) -> List[ProxyStats]:
        """
        Get proxies available for rotation (not disabled, not in cooldown).
        
        Args:
            country: Optional filter by country
            
        Returns:
            List of available ProxyStats
        """
        now = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            if country:
                cursor = conn.execute("""
                    SELECT * FROM proxy_stats 
                    WHERE country = ? 
                    AND is_disabled = 0
                    AND (cooldown_until IS NULL OR cooldown_until < ?)
                    ORDER BY last_used ASC
                """, (country, now))
            else:
                cursor = conn.execute("""
                    SELECT * FROM proxy_stats 
                    WHERE is_disabled = 0
                    AND (cooldown_until IS NULL OR cooldown_until < ?)
                    ORDER BY last_used ASC
                """, (now,))
            
            return [ProxyStats.from_row(dict(row)) for row in cursor.fetchall()]
    
    def disable_proxy(self, proxy_id: str, reason: str = "manual") -> bool:
        """
        Manually disable a proxy.
        
        Args:
            proxy_id: Proxy identifier
            reason: Reason for disabling
            
        Returns:
            True if successful
        """
        now = datetime.now(timezone.utc).isoformat()
        cooldown_until = (
            datetime.now(timezone.utc) + timedelta(minutes=self.cooldown_minutes)
        ).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM proxy_stats WHERE proxy_id = ?",
                (proxy_id,)
            )
            if cursor.fetchone() is None:
                return False
            
            conn.execute("""
                UPDATE proxy_stats SET
                    is_disabled = 1,
                    disabled_at = ?,
                    cooldown_until = ?
                WHERE proxy_id = ?
            """, (now, cooldown_until, proxy_id))
            conn.commit()
        
        logger.info(f"Disabled proxy {proxy_id}: {reason}")
        return True
    
    def enable_proxy(self, proxy_id: str) -> bool:
        """
        Manually re-enable a proxy.
        
        Args:
            proxy_id: Proxy identifier
            
        Returns:
            True if successful
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM proxy_stats WHERE proxy_id = ?",
                (proxy_id,)
            )
            if cursor.fetchone() is None:
                return False
            
            conn.execute("""
                UPDATE proxy_stats SET
                    is_disabled = 0,
                    disabled_at = NULL,
                    cooldown_until = NULL,
                    consecutive_failures = 0
                WHERE proxy_id = ?
            """, (proxy_id,))
            conn.commit()
        
        logger.info(f"Enabled proxy {proxy_id}")
        return True
    
    def check_and_reenable_cooled_down(self) -> int:
        """
        Check for proxies that have finished cooldown and re-enable them.
        
        Returns:
            Number of proxies re-enabled
        """
        now = datetime.now(timezone.utc).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT proxy_id FROM proxy_stats 
                WHERE is_disabled = 1 
                AND cooldown_until IS NOT NULL 
                AND cooldown_until < ?
            """, (now,))
            
            proxy_ids = [row["proxy_id"] for row in cursor.fetchall()]
            
            if proxy_ids:
                conn.execute("""
                    UPDATE proxy_stats SET
                        is_disabled = 0,
                        disabled_at = NULL,
                        cooldown_until = NULL,
                        consecutive_failures = 0
                    WHERE proxy_id IN ({})
                """.format(",".join("?" * len(proxy_ids))), proxy_ids)
                conn.commit()
        
        if proxy_ids:
            logger.info(f"Re-enabled {len(proxy_ids)} proxies after cooldown")
        
        return len(proxy_ids)
    
    def get_statistics(self, country: Optional[str] = None) -> Dict[str, Any]:
        """
        Get aggregate statistics.
        
        Args:
            country: Optional filter by country
            
        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            if country:
                where_clause = "WHERE country = ?"
                params = [country]
            else:
                where_clause = ""
                params = []
            
            # Total proxies
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM proxy_stats {where_clause}",
                params
            )
            total_proxies = cursor.fetchone()["count"]
            
            # Disabled count
            cursor = conn.execute(
                f"SELECT COUNT(*) as count FROM proxy_stats {where_clause} {'AND' if where_clause else 'WHERE'} is_disabled = 1",
                params
            )
            disabled_count = cursor.fetchone()["count"]
            
            # Total successes and failures
            cursor = conn.execute(f"""
                SELECT 
                    COALESCE(SUM(success_count), 0) as total_successes,
                    COALESCE(SUM(failure_count), 0) as total_failures,
                    COALESCE(AVG(avg_latency_ms), 0) as avg_latency
                FROM proxy_stats {where_clause}
            """, params)
            row = cursor.fetchone()
            total_successes = row["total_successes"]
            total_failures = row["total_failures"]
            avg_latency = row["avg_latency"]
            
            total_uses = total_successes + total_failures
            success_rate = (total_successes / total_uses * 100) if total_uses > 0 else 0
        
        return {
            "total_proxies": total_proxies,
            "disabled_count": disabled_count,
            "available_count": total_proxies - disabled_count,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "country_filter": country
        }
    
    def export_to_csv(self, output_path: Path) -> int:
        """
        Export proxy stats to CSV.
        
        Args:
            output_path: Path to output CSV file
            
        Returns:
            Number of records exported
        """
        import csv
        
        stats = self.get_all_stats()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", newline="") as f:
            if stats:
                writer = csv.DictWriter(f, fieldnames=stats[0].to_dict().keys())
                writer.writeheader()
                for s in stats:
                    writer.writerow(s.to_dict())
        
        logger.info(f"Exported {len(stats)} proxy stats to {output_path}")
        return len(stats)
