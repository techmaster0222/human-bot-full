"""
Session Context
Immutable context object for session-wide state.

Every session MUST be initialized with a SessionContext that provides:
- Unique identifiers
- Deterministic seed for all randomness
- Environment information

All behavior engines derive their randomness from this context.
The context is immutable after creation.
"""

import hashlib
from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)  # frozen=True makes it immutable
class SessionContext:
    """
    Immutable session context containing all session-wide state.
    
    This context is passed to all behavior engines and session components.
    All randomness in a session is derived from the deterministic seed.
    
    Attributes:
        session_id: Unique session identifier (e.g., "human_a3f2b1c4_1706451234")
        profile_id: AdsPower profile ID created for this session
        proxy_session: Full proxy session string for IPRoyal
        seed: Deterministic seed for all random behavior
        os_type: Operating system ("windows" or "linux")
        vps_id: VPS identifier for tracking/logging
        start_timestamp: Session start time (UTC)
        country: Target country for this session
    
    Usage:
        context = SessionContext.create(
            session_id="human_abc123",
            profile_id="ap_xyz789",
            proxy_session="customer-xxx-country-us-session-human_abc123",
            os_type="windows",
            vps_id="dev_local",
            country="US"
        )
        
        # Pass to behavior engines
        timing = TimingDistributionEngine(seed=context.seed)
        mouse = MouseMovementEngine(seed=context.seed)
    
    Immutability:
        SessionContext is frozen (immutable). Once created, it cannot be modified.
        This ensures consistency throughout the session lifecycle.
    """
    session_id: str
    profile_id: str
    proxy_session: str
    seed: int
    os_type: str
    vps_id: str
    start_timestamp: datetime
    country: str
    
    @classmethod
    def create(
        cls,
        session_id: str,
        profile_id: str,
        proxy_session: str,
        os_type: str,
        vps_id: str,
        country: str,
        seed: Optional[int] = None,
        start_timestamp: Optional[datetime] = None
    ) -> "SessionContext":
        """
        Create a new SessionContext.
        
        Args:
            session_id: Unique session identifier
            profile_id: AdsPower profile ID
            proxy_session: Full proxy session string
            os_type: Operating system type
            vps_id: VPS identifier
            country: Target country
            seed: Deterministic seed (auto-generated from session_id if None)
            start_timestamp: Start time (current UTC if None)
            
        Returns:
            Immutable SessionContext instance
        """
        # Generate deterministic seed from session_id if not provided
        if seed is None:
            seed = cls._generate_seed(session_id)
        
        # Use current UTC time if not provided
        if start_timestamp is None:
            start_timestamp = datetime.now(timezone.utc)
        
        return cls(
            session_id=session_id,
            profile_id=profile_id,
            proxy_session=proxy_session,
            seed=seed,
            os_type=os_type,
            vps_id=vps_id,
            start_timestamp=start_timestamp,
            country=country
        )
    
    @staticmethod
    def _generate_seed(session_id: str) -> int:
        """
        Generate a deterministic seed from session ID.
        
        Uses SHA-256 hash to create a reproducible integer seed.
        Same session_id always produces same seed.
        """
        hash_bytes = hashlib.sha256(session_id.encode()).digest()
        # Use first 4 bytes to create a 32-bit integer
        seed = int.from_bytes(hash_bytes[:4], byteorder='big')
        # Ensure positive and within numpy's accepted range
        return seed % (2**31)
    
    def derive_subseed(self, component: str) -> int:
        """
        Derive a subseed for a specific component.
        
        This allows different components to have different random streams
        while still being deterministic from the main seed.
        
        Args:
            component: Component name (e.g., "timing", "mouse", "scroll")
            
        Returns:
            Derived seed for the component
        """
        combined = f"{self.session_id}:{component}"
        return self._generate_seed(combined)
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since session start"""
        delta = datetime.now(timezone.utc) - self.start_timestamp
        return delta.total_seconds()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/storage"""
        return {
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "proxy_session": self.proxy_session,
            "seed": self.seed,
            "os_type": self.os_type,
            "vps_id": self.vps_id,
            "start_timestamp": self.start_timestamp.isoformat(),
            "country": self.country,
        }
    
    def __str__(self) -> str:
        return f"SessionContext(session={self.session_id}, profile={self.profile_id}, seed={self.seed})"
