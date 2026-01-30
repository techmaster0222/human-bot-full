"""
Proxy Session Manager
Manages proxy sessions with UUID-based IDs and strict reuse prevention.

This module enforces the core rotation model:
- One session ID = one proxy identity
- Session IDs are never reused within runtime
- Rotation achieved via profile lifecycle (create → run → stop → destroy)
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from ..core.constants import (
    PROXY_SESSION_PREFIX,
    PROXY_TEST_TIMEOUT,
    PROXY_TEST_URL,
)


@dataclass
class ProxyCredentials:
    """
    IPRoyal proxy credentials.

    IPRoyal format:
    - Username: static (e.g., "1yDk0Suq7flACwNg")
    - Password: base_password + session params (e.g., "5o5qYiIfA5cvAC6l_session-xxx_lifetime-30m")

    The session configuration goes in the PASSWORD field, not username.
    """

    username: str
    password: str  # Base password WITHOUT session params
    host: str = "geo.iproyal.com"
    port: int = 12321


@dataclass
class ProxySession:
    """
    Represents a single proxy session with strict lifecycle.

    IPRoyal Format:
    - Username: static (from credentials)
    - Password: {base_password}_country-{CC}_session-{ID}_lifetime-{DURATION}m_streaming-1

    Once created, a session is immutable. Session IDs cannot be reused.
    """

    session_id: str
    country: str
    proxy_username: str  # Static username
    proxy_password: str  # Password WITH session params embedded
    proxy_host: str
    proxy_port: int
    created_at: datetime
    sticky_duration: int  # In seconds

    # Lifecycle tracking
    used: bool = False
    profile_id: str | None = None

    @property
    def proxy_url(self) -> str:
        """Get full proxy URL with auth"""
        auth = f"{self.proxy_username}:{self.proxy_password}"
        return f"http://{auth}@{self.proxy_host}:{self.proxy_port}"

    def to_adspower_config(self) -> dict:
        """Convert to AdsPower proxy config format"""
        return {
            "proxy_type": "http",
            "proxy_host": self.proxy_host,
            "proxy_port": str(self.proxy_port),
            "proxy_user": self.proxy_username,
            "proxy_password": self.proxy_password,
            "proxy_soft": "other",
        }


class SessionIDGenerator:
    """
    Generates unique session IDs that cannot be reused.

    Format: human_{uuid_short}_{timestamp}
    Example: human_a3f2b1c4_1706451234
    """

    def __init__(self):
        self._generated_ids: set[str] = set()

    def generate(self) -> str:
        """
        Generate a unique session ID.

        Returns:
            Unique session ID string

        Raises:
            RuntimeError: If unable to generate unique ID (should never happen)
        """
        for _ in range(100):  # Safety limit
            # Use UUID4 for randomness, truncate for readability
            uuid_part = uuid.uuid4().hex[:8]
            timestamp = int(datetime.now(timezone.utc).timestamp())
            session_id = f"{PROXY_SESSION_PREFIX}_{uuid_part}_{timestamp}"

            if session_id not in self._generated_ids:
                self._generated_ids.add(session_id)
                return session_id

        raise RuntimeError("Unable to generate unique session ID")

    def is_used(self, session_id: str) -> bool:
        """Check if a session ID has been generated"""
        return session_id in self._generated_ids

    def mark_used(self, session_id: str):
        """Mark a session ID as used (for external IDs)"""
        self._generated_ids.add(session_id)

    @property
    def generated_count(self) -> int:
        """Get count of generated session IDs"""
        return len(self._generated_ids)


class ProxySessionManager:
    """
    Manages proxy sessions with strict single-use enforcement.

    Core principles:
    - Each session ID maps to exactly one proxy identity
    - Session IDs are UUID-based and never reused
    - No mid-session IP rotation
    - Tracks all sessions for audit trail

    Usage:
        manager = ProxySessionManager(credentials)
        session = manager.create_session(country="US")
        # Use session.to_adspower_config() for profile creation
        manager.mark_session_used(session.session_id, profile_id)
    """

    def __init__(self, credentials: ProxyCredentials, sticky_duration: int = 600):
        """
        Initialize proxy session manager.

        Args:
            credentials: IPRoyal proxy credentials
            sticky_duration: Default sticky session duration in seconds
        """
        self.credentials = credentials
        self.sticky_duration = sticky_duration

        self._id_generator = SessionIDGenerator()
        self._sessions: dict[str, ProxySession] = {}
        self._used_sessions: set[str] = set()  # Sessions that have been assigned to profiles

        logger.info(
            f"ProxySessionManager initialized (host: {credentials.host}:{credentials.port})"
        )

    def create_session(
        self,
        country: str,
        state: str | None = None,
        city: str | None = None,
        duration: int | None = None,
    ) -> ProxySession:
        """
        Create a new proxy session with unique ID.

        Args:
            country: Target country code (e.g., "US")
            state: Target state (optional)
            city: Target city (optional)
            duration: Session duration in seconds (optional)

        Returns:
            ProxySession instance
        """
        session_id = self._id_generator.generate()
        duration = duration or self.sticky_duration

        # Build IPRoyal password with session params embedded
        # Format: {base_password}_country-{CC}_session-{ID}_lifetime-{DURATION}m_streaming-1
        proxy_password = self._build_proxy_password(
            country=country, state=state, city=city, session_id=session_id, duration=duration
        )

        session = ProxySession(
            session_id=session_id,
            country=country,
            proxy_username=self.credentials.username,  # Static username
            proxy_password=proxy_password,  # Password with session params
            proxy_host=self.credentials.host,
            proxy_port=self.credentials.port,
            created_at=datetime.now(timezone.utc),
            sticky_duration=duration,
        )

        self._sessions[session_id] = session

        logger.info(f"Created proxy session: {session_id} (country: {country})")
        return session

    def mark_session_used(self, session_id: str, profile_id: str):
        """
        Mark a session as used by a profile.

        This prevents the session from being assigned to another profile.

        Args:
            session_id: Session ID to mark
            profile_id: AdsPower profile ID using this session

        Raises:
            ValueError: If session doesn't exist or is already used
        """
        if session_id not in self._sessions:
            raise ValueError(f"Session {session_id} does not exist")

        if session_id in self._used_sessions:
            raise ValueError(f"Session {session_id} is already used")

        session = self._sessions[session_id]
        session.used = True
        session.profile_id = profile_id
        self._used_sessions.add(session_id)

        logger.debug(f"Session {session_id} assigned to profile {profile_id}")

    def get_session(self, session_id: str) -> ProxySession | None:
        """Get a session by ID"""
        return self._sessions.get(session_id)

    def get_session_by_profile(self, profile_id: str) -> ProxySession | None:
        """Get session assigned to a specific profile"""
        for session in self._sessions.values():
            if session.profile_id == profile_id:
                return session
        return None

    def is_session_used(self, session_id: str) -> bool:
        """Check if a session has been assigned to a profile"""
        return session_id in self._used_sessions

    def end_session(self, session_id: str):
        """
        End a session (for cleanup).

        Note: This doesn't allow reuse - the session ID remains marked as used.
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            logger.info(f"Ending session: {session_id} (profile: {session.profile_id})")
            # Keep in used set to prevent reuse
            # Remove from active sessions
            del self._sessions[session_id]

    def get_active_sessions(self) -> dict[str, ProxySession]:
        """Get all active (not ended) sessions"""
        return self._sessions.copy()

    def get_used_session_count(self) -> int:
        """Get count of sessions that have been used"""
        return len(self._used_sessions)

    def get_total_session_count(self) -> int:
        """Get total count of sessions created"""
        return self._id_generator.generated_count

    def _build_proxy_password(
        self,
        country: str,
        state: str | None,
        city: str | None,
        session_id: str,
        duration: int,
    ) -> str:
        """
        Build IPRoyal password with targeting and session params.

        IPRoyal Format (session params in PASSWORD):
        {base_password}_country-{CC}_session-{ID}_lifetime-{DURATION}m_streaming-1

        Example: 5o5qYiIfA5cvAC6l_country-us_session-human_abc123_lifetime-30m_streaming-1
        """
        parts = [self.credentials.password]  # Base password

        # Add country targeting
        parts.append(f"country-{country.lower()}")

        # Add state targeting (if provided)
        if state:
            parts.append(f"state-{state.lower()}")

        # Add city targeting (if provided)
        if city:
            parts.append(f"city-{city.lower()}")

        # Add session ID for sticky session
        parts.append(f"session-{session_id}")

        # Add lifetime in minutes (convert from seconds)
        lifetime_minutes = max(1, duration // 60)
        parts.append(f"lifetime-{lifetime_minutes}m")

        # Add streaming mode (required for residential)
        parts.append("streaming-1")

        return "_".join(parts)

    def test_session(self, session: ProxySession, timeout: int = None) -> tuple[bool, str | None]:
        """
        Test if a proxy session is working.

        Args:
            session: ProxySession to test
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, ip_address)
        """
        import requests

        timeout = timeout or PROXY_TEST_TIMEOUT
        proxies = {"http": session.proxy_url, "https": session.proxy_url}

        try:
            response = requests.get(PROXY_TEST_URL, proxies=proxies, timeout=timeout)
            ip = response.json().get("ip")
            logger.info(f"Proxy test successful for {session.session_id}. IP: {ip}")
            return True, ip
        except Exception as e:
            logger.error(f"Proxy test failed for {session.session_id}: {e}")
            return False, None

    def cleanup(self):
        """Clean up all sessions"""
        session_count = len(self._sessions)
        self._sessions.clear()
        logger.info(f"ProxySessionManager cleaned up {session_count} sessions")

    def get_stats(self) -> dict:
        """Get manager statistics"""
        return {
            "total_created": self._id_generator.generated_count,
            "active_sessions": len(self._sessions),
            "used_sessions": len(self._used_sessions),
            "unused_active": len([s for s in self._sessions.values() if not s.used]),
        }
