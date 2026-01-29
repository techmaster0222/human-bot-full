"""
Session Logger
Structured logging for session audit trail.

Provides both real-time logging and persistent storage of session data
in the mandatory audit format specified in the requirements.
"""

import json
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

from .runner import SessionResult
from ..core.constants import (
    ReputationTier,
    ReuseDecision,
    AUDIT_LOG_FILENAME,
)


@dataclass
class SessionLogRecord:
    """
    Structured log record for a session.
    
    Matches the mandatory audit format from requirements.
    """
    session_id: str
    profile_id: str
    proxy_session: str
    ip_tier: str  # GOOD, NEUTRAL, BAD
    score: int
    signals: List[str]
    reuse_allowed: bool
    reuse_count: int
    decision: str  # DESTROY, COOLDOWN, REUSE
    reason: str
    os: str
    vps_id: str
    duration_seconds: float
    country: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Remove None values for cleaner output
        return {k: v for k, v in result.items() if v is not None}
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent, default=str)


class SessionLogger:
    """
    Logs session data in structured audit format.
    
    Supports:
    - JSON file logging for audit trail
    - Real-time loguru output
    - Querying logged sessions
    
    Usage:
        logger = SessionLogger(data_dir=Path("data"))
        
        # Log a session
        record = SessionLogRecord(...)
        logger.log_session(record)
        
        # Export all logs
        logger.export_all()
    """
    
    def __init__(
        self,
        data_dir: Path,
        audit_filename: str = AUDIT_LOG_FILENAME,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True
    ):
        """
        Initialize session logger.
        
        Args:
            data_dir: Directory for log files
            audit_filename: Name of audit log file
            enable_file_logging: Write to JSON file
            enable_console_logging: Output to console via loguru
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.audit_file = self.data_dir / audit_filename
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        
        # In-memory log buffer
        self._records: List[SessionLogRecord] = []
        
        # Initialize audit file if needed
        if enable_file_logging and not self.audit_file.exists():
            self._init_audit_file()
        
        logger.info(f"SessionLogger initialized (file: {self.audit_file})")
    
    def _init_audit_file(self):
        """Initialize the audit log file"""
        with self.audit_file.open("w", encoding="utf-8") as f:
            # Start with empty JSON array
            f.write("[\n]\n")
    
    def log_session(self, record: SessionLogRecord):
        """
        Log a session record.
        
        Args:
            record: SessionLogRecord to log
        """
        # Add to in-memory buffer
        self._records.append(record)
        
        # Write to file
        if self.enable_file_logging:
            self._append_to_audit_file(record)
        
        # Console output
        if self.enable_console_logging:
            self._log_to_console(record)
    
    def log_from_result(
        self,
        result: SessionResult,
        proxy_session: str,
        tier: ReputationTier,
        score: int,
        reuse_decision: ReuseDecision,
        reuse_reason: str,
        reuse_count: int,
        os_name: str,
        vps_id: str,
        country: str
    ) -> SessionLogRecord:
        """
        Create and log a record from a SessionResult.
        
        Args:
            result: SessionResult from runner
            proxy_session: Proxy session ID
            tier: Computed reputation tier
            score: Computed score
            reuse_decision: Decision on profile reuse
            reuse_reason: Human-readable reason for decision
            reuse_count: Current reuse count for profile
            os_name: Operating system
            vps_id: VPS identifier
            country: Country for session
            
        Returns:
            The created SessionLogRecord
        """
        record = SessionLogRecord(
            session_id=result.session_id,
            profile_id=result.profile_id,
            proxy_session=proxy_session,
            ip_tier=tier.value,
            score=score,
            signals=result.signals,
            reuse_allowed=reuse_decision == ReuseDecision.REUSE,
            reuse_count=reuse_count,
            decision=reuse_decision.value,
            reason=reuse_reason,
            os=os_name,
            vps_id=vps_id,
            duration_seconds=result.duration_seconds,
            country=country,
            started_at=result.started_at.isoformat() if result.started_at else None,
            ended_at=result.ended_at.isoformat() if result.ended_at else None,
            error=result.error,
            metadata=result.metadata
        )
        
        self.log_session(record)
        return record
    
    def _append_to_audit_file(self, record: SessionLogRecord):
        """Append a record to the audit JSON file"""
        try:
            # Read existing content
            with self.audit_file.open("r", encoding="utf-8") as f:
                content = f.read().strip()
            
            # Parse existing array
            if content == "[\n]" or content == "[]":
                # Empty array, start fresh
                records = []
            else:
                # Remove trailing ] and parse
                records = json.loads(content)
            
            # Add new record
            records.append(record.to_dict())
            
            # Write back
            with self.audit_file.open("w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to write to audit file: {e}")
    
    def _log_to_console(self, record: SessionLogRecord):
        """Log record summary to console"""
        tier_emoji = {
            "GOOD": "+",
            "NEUTRAL": "o",
            "BAD": "x"
        }.get(record.ip_tier, "?")
        
        status = "SUCCESS" if record.decision != "DESTROY" or record.error is None else "FAILED"
        
        logger.info(
            f"[{tier_emoji} {record.ip_tier}] session={record.session_id} "
            f"score={record.score} decision={record.decision} "
            f"duration={record.duration_seconds:.1f}s"
        )
    
    def get_records(self) -> List[SessionLogRecord]:
        """Get all logged records from memory"""
        return self._records.copy()
    
    def get_record_count(self) -> int:
        """Get count of logged records"""
        return len(self._records)
    
    def get_records_by_tier(self, tier: ReputationTier) -> List[SessionLogRecord]:
        """Get records filtered by tier"""
        return [r for r in self._records if r.ip_tier == tier.value]
    
    def get_records_by_decision(self, decision: ReuseDecision) -> List[SessionLogRecord]:
        """Get records filtered by decision"""
        return [r for r in self._records if r.decision == decision.value]
    
    def load_from_file(self) -> List[Dict]:
        """Load records from audit file"""
        if not self.audit_file.exists():
            return []
        
        try:
            with self.audit_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load audit file: {e}")
            return []
    
    def export_session(self, session_id: str) -> Optional[Dict]:
        """Export a single session record as dict"""
        for record in self._records:
            if record.session_id == session_id:
                return record.to_dict()
        return None
    
    def export_all(self, output_path: Optional[Path] = None) -> str:
        """
        Export all records to JSON.
        
        Args:
            output_path: Path to write to (returns string if None)
            
        Returns:
            JSON string of all records
        """
        records = [r.to_dict() for r in self._records]
        json_str = json.dumps(records, indent=2, default=str)
        
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open("w", encoding="utf-8") as f:
                f.write(json_str)
            logger.info(f"Exported {len(records)} records to {output_path}")
        
        return json_str
    
    def get_summary(self) -> Dict:
        """Get summary statistics of logged sessions"""
        total = len(self._records)
        
        if total == 0:
            return {
                "total_sessions": 0,
                "by_tier": {},
                "by_decision": {},
                "avg_duration": 0,
                "avg_score": 0,
            }
        
        by_tier = {}
        by_decision = {}
        total_duration = 0
        total_score = 0
        
        for record in self._records:
            # Count by tier
            tier = record.ip_tier
            by_tier[tier] = by_tier.get(tier, 0) + 1
            
            # Count by decision
            decision = record.decision
            by_decision[decision] = by_decision.get(decision, 0) + 1
            
            # Sum for averages
            total_duration += record.duration_seconds
            total_score += record.score
        
        return {
            "total_sessions": total,
            "by_tier": by_tier,
            "by_decision": by_decision,
            "avg_duration": round(total_duration / total, 2),
            "avg_score": round(total_score / total, 2),
        }
    
    def print_summary(self):
        """Print a formatted summary"""
        summary = self.get_summary()
        
        print("\n" + "=" * 50)
        print("SESSION LOG SUMMARY")
        print("=" * 50)
        print(f"Total Sessions: {summary['total_sessions']}")
        print("-" * 50)
        print("By Tier:")
        for tier, count in summary["by_tier"].items():
            print(f"  {tier}: {count}")
        print("-" * 50)
        print("By Decision:")
        for decision, count in summary["by_decision"].items():
            print(f"  {decision}: {count}")
        print("-" * 50)
        print(f"Avg Duration: {summary['avg_duration']}s")
        print(f"Avg Score: {summary['avg_score']}")
        print("=" * 50 + "\n")
