"""
Cooldown Manager
Time-based cooldown management for profile reuse.

Tracks profiles in cooldown and prevents premature reuse.
Uses UTC time for cross-platform consistency.
"""

from typing import Optional, Dict, Set
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from loguru import logger

from ..core.constants import (
    DEFAULT_COOLDOWN_SECONDS,
    MIN_COOLDOWN_SECONDS,
)


@dataclass
class CooldownEntry:
    """A single cooldown entry"""
    profile_id: str
    started_at: datetime
    duration_seconds: int
    expires_at: datetime
    reason: str = ""
    
    @property
    def is_expired(self) -> bool:
        """Check if cooldown has expired"""
        return datetime.now(timezone.utc) >= self.expires_at
    
    @property
    def remaining_seconds(self) -> float:
        """Get remaining cooldown time in seconds"""
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.now(timezone.utc)
        return delta.total_seconds()


class CooldownManager:
    """
    Manages cooldown periods for profiles.
    
    Cooldowns are time-based gates that prevent profile reuse
    until a specified duration has passed.
    
    Uses UTC time (datetime.now(timezone.utc)) for cross-platform consistency.
    
    Usage:
        manager = CooldownManager()
        
        # Start cooldown
        manager.start_cooldown(profile_id, duration_seconds=3600)
        
        # Check status
        if manager.is_in_cooldown(profile_id):
            remaining = manager.get_remaining(profile_id)
            print(f"Cooldown: {remaining}s remaining")
        
        # Clear expired
        manager.clear_expired()
    """
    
    def __init__(self, default_duration: int = DEFAULT_COOLDOWN_SECONDS):
        """
        Initialize cooldown manager.
        
        Args:
            default_duration: Default cooldown duration in seconds
        """
        self.default_duration = default_duration
        self._cooldowns: Dict[str, CooldownEntry] = {}
        
        logger.info(f"CooldownManager initialized (default: {default_duration}s)")
    
    def start_cooldown(
        self,
        profile_id: str,
        duration_seconds: Optional[int] = None,
        reason: str = ""
    ) -> CooldownEntry:
        """
        Start a cooldown for a profile.
        
        Args:
            profile_id: Profile to put in cooldown
            duration_seconds: Cooldown duration (uses default if None)
            reason: Reason for cooldown (for logging)
            
        Returns:
            CooldownEntry created
        """
        duration = duration_seconds or self.default_duration
        
        # Enforce minimum
        duration = max(duration, MIN_COOLDOWN_SECONDS)
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=duration)
        
        entry = CooldownEntry(
            profile_id=profile_id,
            started_at=now,
            duration_seconds=duration,
            expires_at=expires_at,
            reason=reason
        )
        
        self._cooldowns[profile_id] = entry
        
        logger.info(f"Cooldown started for {profile_id}: {duration}s (reason: {reason})")
        return entry
    
    def is_in_cooldown(self, profile_id: str) -> bool:
        """
        Check if a profile is currently in cooldown.
        
        Args:
            profile_id: Profile to check
            
        Returns:
            True if in cooldown (not expired)
        """
        entry = self._cooldowns.get(profile_id)
        if entry is None:
            return False
        
        if entry.is_expired:
            # Clean up expired entry
            del self._cooldowns[profile_id]
            return False
        
        return True
    
    def get_remaining(self, profile_id: str) -> float:
        """
        Get remaining cooldown time in seconds.
        
        Args:
            profile_id: Profile to check
            
        Returns:
            Remaining seconds (0 if not in cooldown)
        """
        entry = self._cooldowns.get(profile_id)
        if entry is None:
            return 0
        
        return entry.remaining_seconds
    
    def get_entry(self, profile_id: str) -> Optional[CooldownEntry]:
        """Get cooldown entry for a profile"""
        return self._cooldowns.get(profile_id)
    
    def cancel_cooldown(self, profile_id: str) -> bool:
        """
        Cancel a cooldown early.
        
        Args:
            profile_id: Profile to cancel cooldown for
            
        Returns:
            True if cancelled, False if not in cooldown
        """
        if profile_id in self._cooldowns:
            del self._cooldowns[profile_id]
            logger.info(f"Cooldown cancelled for {profile_id}")
            return True
        return False
    
    def clear_expired(self) -> int:
        """
        Clear all expired cooldowns.
        
        Returns:
            Number of cooldowns cleared
        """
        expired = [
            pid for pid, entry in self._cooldowns.items()
            if entry.is_expired
        ]
        
        for pid in expired:
            del self._cooldowns[pid]
        
        if expired:
            logger.debug(f"Cleared {len(expired)} expired cooldowns")
        
        return len(expired)
    
    def get_all_in_cooldown(self) -> Set[str]:
        """Get all profile IDs currently in cooldown"""
        self.clear_expired()
        return set(self._cooldowns.keys())
    
    def get_cooldown_count(self) -> int:
        """Get count of active cooldowns"""
        self.clear_expired()
        return len(self._cooldowns)
    
    def clear_all(self):
        """Clear all cooldowns"""
        count = len(self._cooldowns)
        self._cooldowns.clear()
        logger.info(f"Cleared all {count} cooldowns")
