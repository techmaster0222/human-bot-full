"""
IPRoyal Proxy Pool Manager
Manages residential proxy connections through IPRoyal.
"""

import random
import time
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from loguru import logger
import requests


@dataclass
class ProxyConfig:
    """Proxy connection configuration"""
    host: str
    port: int
    username: str
    password: str
    proxy_type: str = "http"
    country: str = None
    city: str = None
    session_id: str = None
    sticky_duration: int = 600  # seconds
    
    @property
    def url(self) -> str:
        """Get proxy URL with auth"""
        auth = f"{self.username}:{self.password}"
        return f"{self.proxy_type}://{auth}@{self.host}:{self.port}"
    
    @property
    def url_no_auth(self) -> str:
        """Get proxy URL without auth"""
        return f"{self.proxy_type}://{self.host}:{self.port}"
    
    def to_adspower_config(self) -> Dict:
        """Convert to AdsPower proxy config format"""
        return {
            "proxy_type": self.proxy_type,
            "proxy_host": self.host,
            "proxy_port": str(self.port),
            "proxy_user": self.username,
            "proxy_password": self.password,
            "proxy_soft": "other"
        }
    
    def to_selenium_config(self) -> Dict:
        """Convert to Selenium proxy format"""
        return {
            "httpProxy": f"{self.host}:{self.port}",
            "httpsProxy": f"{self.host}:{self.port}",
            "proxyType": "MANUAL",
        }


@dataclass
class ProxySession:
    """Tracks a sticky proxy session"""
    config: ProxyConfig
    session_id: str
    started_at: datetime
    expires_at: datetime
    profile_id: str = None
    requests_made: int = 0
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at
    
    @property
    def time_remaining(self) -> timedelta:
        return self.expires_at - datetime.now()


class IPRoyalProxy:
    """
    IPRoyal Residential Proxy Manager
    
    Supports:
    - Rotating proxies (new IP each request)
    - Sticky sessions (same IP for duration)
    - Geo-targeting by country, state, city
    - Multiple authentication methods
    """
    
    # IPRoyal proxy endpoints
    RESIDENTIAL_HOST = "geo.iproyal.com"
    RESIDENTIAL_PORT = 12321
    
    # Supported countries (common ones)
    SUPPORTED_COUNTRIES = [
        "US", "UK", "CA", "AU", "DE", "FR", "ES", "IT", "NL", "BE",
        "BR", "MX", "JP", "KR", "IN", "SG", "HK", "TW", "PH", "VN"
    ]
    
    def __init__(
        self,
        username: str,
        password: str,
        host: str = None,
        port: int = None,
        default_country: str = "US",
        sticky_duration: int = 600
    ):
        """
        Initialize IPRoyal proxy manager.
        
        Args:
            username: IPRoyal username
            password: IPRoyal password
            host: Proxy host (default: geo.iproyal.com)
            port: Proxy port (default: 12321)
            default_country: Default country for geo-targeting
            sticky_duration: Default sticky session duration in seconds
        """
        self.username = username
        self.password = password
        self.host = host or self.RESIDENTIAL_HOST
        self.port = port or self.RESIDENTIAL_PORT
        self.default_country = default_country
        self.sticky_duration = sticky_duration
        
        self._sessions: Dict[str, ProxySession] = {}
        self._session_counter = 0
        
        logger.info(f"IPRoyal proxy manager initialized (host: {self.host}:{self.port})")
    
    def get_rotating_proxy(
        self,
        country: str = None,
        state: str = None,
        city: str = None
    ) -> ProxyConfig:
        """
        Get a rotating proxy (new IP each request).
        
        Args:
            country: Target country code (e.g., "US")
            state: Target state (for US)
            city: Target city
            
        Returns:
            ProxyConfig for rotating proxy
        """
        password = self._build_password(
            country=country,
            state=state,
            city=city,
            session_type="rotating"
        )
        
        return ProxyConfig(
            host=self.host,
            port=self.port,
            username=self.username,
            password=password,
            country=country or self.default_country
        )
    
    def get_sticky_proxy(
        self,
        country: str = None,
        state: str = None,
        city: str = None,
        duration: int = None,
        session_id: str = None
    ) -> Tuple[ProxyConfig, str]:
        """
        Get a sticky proxy (same IP for duration).
        
        Args:
            country: Target country code
            state: Target state
            city: Target city
            duration: Session duration in seconds
            session_id: Custom session ID (auto-generated if not provided)
            
        Returns:
            Tuple of (ProxyConfig, session_id)
        """
        duration = duration or self.sticky_duration
        
        if not session_id:
            self._session_counter += 1
            # Generate shorter session ID (8 chars like IPRoyal examples)
            import random
            import string
            session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        
        password = self._build_password(
            country=country,
            state=state,
            city=city,
            session_type="sticky",
            session_id=session_id,
            duration=duration
        )
        
        config = ProxyConfig(
            host=self.host,
            port=self.port,
            username=self.username,
            password=password,
            country=country or self.default_country,
            session_id=session_id,
            sticky_duration=duration
        )
        
        return config, session_id
    
    def create_session(
        self,
        profile_id: str = None,
        country: str = None,
        state: str = None,
        city: str = None,
        duration: int = None
    ) -> ProxySession:
        """
        Create a new sticky proxy session.
        
        Args:
            profile_id: Associated browser profile ID
            country: Target country
            state: Target state
            city: Target city
            duration: Session duration
            
        Returns:
            ProxySession instance
        """
        duration = duration or self.sticky_duration
        config, session_id = self.get_sticky_proxy(
            country=country,
            state=state,
            city=city,
            duration=duration
        )
        
        session = ProxySession(
            config=config,
            session_id=session_id,
            started_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=duration),
            profile_id=profile_id
        )
        
        self._sessions[session_id] = session
        logger.info(f"Created sticky session: {session_id} (country: {country or self.default_country}, duration: {duration}s)")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[ProxySession]:
        """Get an existing session"""
        return self._sessions.get(session_id)
    
    def get_or_create_session(
        self,
        profile_id: str,
        country: str = None,
        **kwargs
    ) -> ProxySession:
        """
        Get existing session for profile or create new one.
        
        Args:
            profile_id: Browser profile ID
            country: Target country if creating new session
            **kwargs: Additional args for create_session
            
        Returns:
            ProxySession instance
        """
        # Look for existing valid session
        for session in self._sessions.values():
            if session.profile_id == profile_id and not session.is_expired:
                logger.debug(f"Reusing existing session for profile {profile_id}")
                return session
        
        # Create new session
        return self.create_session(profile_id=profile_id, country=country, **kwargs)
    
    def refresh_session(self, session_id: str) -> Optional[ProxySession]:
        """
        Refresh an expired or expiring session with new IP.
        
        Args:
            session_id: Session ID to refresh
            
        Returns:
            New ProxySession with fresh IP
        """
        old_session = self._sessions.get(session_id)
        if not old_session:
            return None
        
        # Create new session with same parameters
        new_session = self.create_session(
            profile_id=old_session.profile_id,
            country=old_session.config.country,
            duration=old_session.config.sticky_duration
        )
        
        # Remove old session
        del self._sessions[session_id]
        
        logger.info(f"Refreshed session {session_id} -> {new_session.session_id}")
        return new_session
    
    def end_session(self, session_id: str):
        """End a session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Ended session: {session_id}")
    
    def cleanup_expired_sessions(self) -> int:
        """Remove all expired sessions"""
        expired = [sid for sid, sess in self._sessions.items() if sess.is_expired]
        for sid in expired:
            del self._sessions[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def _build_password(
        self,
        country: str = None,
        state: str = None,
        city: str = None,
        session_type: str = "rotating",
        session_id: str = None,
        duration: int = None
    ) -> str:
        """
        Build IPRoyal password with targeting options.
        
        IPRoyal format: password_country-XX_city-YY_session-ID_lifetime-30m_streaming-1
        """
        parts = [self.password]
        
        # Add country targeting
        if country:
            parts.append(f"country-{country.lower()}")
        
        # Add state targeting (US only)
        if state:
            parts.append(f"state-{state.lower()}")
        
        # Add city targeting
        if city:
            parts.append(f"city-{city.lower()}")
        
        # Add session/streaming mode
        if session_type == "sticky" and session_id:
            parts.append(f"session-{session_id}")
            if duration:
                # Convert seconds to minutes format (e.g., 600 -> 10m)
                minutes = duration // 60
                parts.append(f"lifetime-{minutes}m")
            parts.append("streaming-1")
        
        return "_".join(parts)
    
    def test_proxy(self, config: ProxyConfig) -> bool:
        """
        Test if proxy is working.
        
        Args:
            config: Proxy configuration to test
            
        Returns:
            True if proxy is working
        """
        proxies = {
            "http": config.url,
            "https": config.url
        }
        
        try:
            response = requests.get(
                "https://api.ipify.org?format=json",
                proxies=proxies,
                timeout=30
            )
            ip = response.json().get("ip")
            logger.info(f"Proxy test successful. IP: {ip}")
            return True
        except Exception as e:
            logger.error(f"Proxy test failed: {e}")
            return False
    
    def get_current_ip(self, config: ProxyConfig) -> Optional[str]:
        """Get current IP address through proxy"""
        proxies = {
            "http": config.url,
            "https": config.url
        }
        
        try:
            response = requests.get(
                "https://api.ipify.org?format=json",
                proxies=proxies,
                timeout=30
            )
            return response.json().get("ip")
        except:
            return None


class ProxyRotator:
    """
    Manages proxy rotation across multiple profiles.
    
    Ensures each browser profile gets a unique proxy and handles
    automatic rotation when sessions expire.
    """
    
    def __init__(self, proxy_manager: IPRoyalProxy, countries: List[str] = None):
        """
        Initialize proxy rotator.
        
        Args:
            proxy_manager: IPRoyalProxy instance
            countries: List of countries to rotate through
        """
        self.proxy_manager = proxy_manager
        self.countries = countries or ["US"]
        self._profile_sessions: Dict[str, ProxySession] = {}
        self._country_index = 0
        
        logger.info(f"ProxyRotator initialized with {len(self.countries)} countries")
    
    def get_proxy_for_profile(
        self,
        profile_id: str,
        country: str = None,
        sticky: bool = True,
        duration: int = None
    ) -> ProxyConfig:
        """
        Get proxy for a specific profile.
        
        Args:
            profile_id: Browser profile ID
            country: Specific country (rotates if not provided)
            sticky: Use sticky session
            duration: Session duration
            
        Returns:
            ProxyConfig for the profile
        """
        # Check for existing valid session
        if profile_id in self._profile_sessions:
            session = self._profile_sessions[profile_id]
            if not session.is_expired:
                session.requests_made += 1
                return session.config
            else:
                # Session expired, need new one
                del self._profile_sessions[profile_id]
        
        # Determine country
        if not country:
            country = self._get_next_country()
        
        if sticky:
            session = self.proxy_manager.create_session(
                profile_id=profile_id,
                country=country,
                duration=duration
            )
            self._profile_sessions[profile_id] = session
            return session.config
        else:
            return self.proxy_manager.get_rotating_proxy(country=country)
    
    def refresh_proxy_for_profile(self, profile_id: str) -> Optional[ProxyConfig]:
        """Get a new proxy for a profile"""
        if profile_id in self._profile_sessions:
            old_session = self._profile_sessions[profile_id]
            self.proxy_manager.end_session(old_session.session_id)
            del self._profile_sessions[profile_id]
        
        return self.get_proxy_for_profile(profile_id)
    
    def _get_next_country(self) -> str:
        """Get next country in rotation"""
        country = self.countries[self._country_index]
        self._country_index = (self._country_index + 1) % len(self.countries)
        return country
    
    def get_all_sessions(self) -> Dict[str, ProxySession]:
        """Get all active sessions"""
        return self._profile_sessions.copy()
    
    def cleanup(self):
        """Clean up all sessions"""
        for session in self._profile_sessions.values():
            self.proxy_manager.end_session(session.session_id)
        self._profile_sessions.clear()
        logger.info("ProxyRotator cleaned up")
