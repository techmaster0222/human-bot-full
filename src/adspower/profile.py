"""
AdsPower Profile Manager
High-level interface for managing browser profiles.
"""

from dataclasses import dataclass, field
from datetime import datetime

from loguru import logger

from .client import AdsPowerClient, create_proxy_config


@dataclass
class Profile:
    """Represents an AdsPower browser profile"""

    id: str
    name: str
    group_id: str = ""
    domain: str = ""
    created_at: datetime = None
    last_open_time: datetime = None
    proxy_config: dict = field(default_factory=dict)
    fingerprint_config: dict = field(default_factory=dict)
    is_running: bool = False
    selenium_ws: str = ""
    webdriver_path: str = ""

    @classmethod
    def from_api_response(cls, data: dict) -> "Profile":
        """Create Profile instance from API response data"""
        return cls(
            id=data.get("user_id", ""),
            name=data.get("name", ""),
            group_id=data.get("group_id", "0"),
            domain=data.get("domain_name", ""),
            proxy_config=data.get("user_proxy_config", {}),
            fingerprint_config=data.get("fingerprint_config", {}),
        )


class ProfileManager:
    """
    High-level manager for AdsPower profiles.

    Provides convenient methods for creating, managing, and operating
    browser profiles with proxy integration.
    """

    def __init__(self, client: AdsPowerClient):
        """
        Initialize ProfileManager.

        Args:
            client: AdsPowerClient instance
        """
        self.client = client
        self._active_profiles: dict[str, Profile] = {}
        self._profile_cache: dict[str, Profile] = {}

        logger.info("ProfileManager initialized")

    def create_profile(
        self,
        name: str,
        proxy_host: str = None,
        proxy_port: int = None,
        proxy_user: str = None,
        proxy_pass: str = None,
        proxy_type: str = "http",
        country: str = None,
        domain: str = None,
        group_id: str = None,
        fingerprint_config: dict = None,
    ) -> Profile | None:
        """
        Create a new browser profile with optional proxy.

        Args:
            name: Profile name
            proxy_host: Proxy host address
            proxy_port: Proxy port
            proxy_user: Proxy username
            proxy_pass: Proxy password
            proxy_type: Proxy type (http, https, socks5)
            country: Country for geo-targeting (affects fingerprint)
            domain: Primary domain for this profile
            group_id: Group ID for organization
            fingerprint_config: Custom fingerprint configuration

        Returns:
            Profile instance if successful, None otherwise
        """
        # Build proxy config if provided
        proxy_config = None
        if proxy_host and proxy_port:
            proxy_config = create_proxy_config(
                proxy_type=proxy_type,
                host=proxy_host,
                port=proxy_port,
                username=proxy_user,
                password=proxy_pass,
            )

        # Build fingerprint config
        fp_config = fingerprint_config or self._get_default_fingerprint(country)

        # Create profile via API
        response = self.client.create_profile(
            name=name,
            group_id=group_id,
            domain_name=domain,
            proxy_config=proxy_config,
            fingerprint_config=fp_config,
        )

        if not response.success:
            logger.error(f"Failed to create profile '{name}': {response.msg}")
            return None

        # Create Profile object
        profile = Profile(
            id=response.data.get("id", ""),
            name=name,
            group_id=group_id or "",
            domain=domain or "",
            proxy_config=proxy_config or {},
            fingerprint_config=fp_config,
        )

        self._profile_cache[profile.id] = profile
        logger.success(f"Created profile '{name}' with ID: {profile.id}")

        return profile

    def get_profile(self, profile_id: str, force_refresh: bool = False) -> Profile | None:
        """
        Get profile by ID.

        Args:
            profile_id: Profile ID
            force_refresh: Force API call even if cached

        Returns:
            Profile instance or None
        """
        if not force_refresh and profile_id in self._profile_cache:
            return self._profile_cache[profile_id]

        response = self.client.get_profile(profile_id)
        if not response.success:
            return None

        profile = Profile.from_api_response(response.data)
        self._profile_cache[profile_id] = profile
        return profile

    def list_profiles(
        self, group_id: str = None, search: str = None, page: int = 1, page_size: int = 100
    ) -> list[Profile]:
        """
        List all profiles.

        Args:
            group_id: Filter by group
            search: Search keyword
            page: Page number
            page_size: Results per page

        Returns:
            List of Profile instances
        """
        response = self.client.list_profiles(
            page=page, page_size=page_size, group_id=group_id, search=search
        )

        if not response.success:
            logger.error(f"Failed to list profiles: {response.msg}")
            return []

        profiles = []
        for item in response.data.get("list", []):
            profile = Profile.from_api_response(item)
            self._profile_cache[profile.id] = profile
            profiles.append(profile)

        return profiles

    def find_or_create_profile(self, name: str, **create_kwargs) -> Profile | None:
        """
        Find existing profile by name or create new one.

        Args:
            name: Profile name to search for
            **create_kwargs: Arguments passed to create_profile if creating

        Returns:
            Profile instance
        """
        # Search for existing profile
        profiles = self.list_profiles(search=name)
        for profile in profiles:
            if profile.name == name:
                logger.info(f"Found existing profile: {name} ({profile.id})")
                return profile

        # Create new profile
        logger.info(f"Profile '{name}' not found, creating new one")
        return self.create_profile(name=name, **create_kwargs)

    def update_proxy(
        self,
        profile_id: str,
        proxy_host: str,
        proxy_port: int,
        proxy_user: str = None,
        proxy_pass: str = None,
        proxy_type: str = "http",
    ) -> bool:
        """
        Update proxy settings for a profile.

        Args:
            profile_id: Profile ID
            proxy_host: New proxy host
            proxy_port: New proxy port
            proxy_user: Proxy username
            proxy_pass: Proxy password
            proxy_type: Proxy type

        Returns:
            True if successful
        """
        proxy_config = create_proxy_config(
            proxy_type=proxy_type,
            host=proxy_host,
            port=proxy_port,
            username=proxy_user,
            password=proxy_pass,
        )

        response = self.client.update_profile_proxy(profile_id, proxy_config)

        if response.success:
            # Update cache
            if profile_id in self._profile_cache:
                self._profile_cache[profile_id].proxy_config = proxy_config
            logger.info(f"Updated proxy for profile {profile_id}")
            return True

        logger.error(f"Failed to update proxy: {response.msg}")
        return False

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile"""
        response = self.client.delete_profile([profile_id])

        if response.success:
            self._profile_cache.pop(profile_id, None)
            self._active_profiles.pop(profile_id, None)
            logger.info(f"Deleted profile: {profile_id}")
            return True

        logger.error(f"Failed to delete profile: {response.msg}")
        return False

    def delete_profiles(self, profile_ids: list[str]) -> bool:
        """Delete multiple profiles"""
        response = self.client.delete_profile(profile_ids)

        if response.success:
            for pid in profile_ids:
                self._profile_cache.pop(pid, None)
                self._active_profiles.pop(pid, None)
            logger.info(f"Deleted {len(profile_ids)} profiles")
            return True

        return False

    def get_active_profiles(self) -> dict[str, Profile]:
        """Get all currently running profiles"""
        return self._active_profiles.copy()

    def mark_profile_active(self, profile: Profile, selenium_ws: str, webdriver_path: str):
        """Mark a profile as active (browser running)"""
        profile.is_running = True
        profile.selenium_ws = selenium_ws
        profile.webdriver_path = webdriver_path
        self._active_profiles[profile.id] = profile

    def mark_profile_inactive(self, profile_id: str):
        """Mark a profile as inactive (browser stopped)"""
        if profile_id in self._active_profiles:
            self._active_profiles[profile_id].is_running = False
            self._active_profiles[profile_id].selenium_ws = ""
            del self._active_profiles[profile_id]

        if profile_id in self._profile_cache:
            self._profile_cache[profile_id].is_running = False

    def _get_default_fingerprint(self, country: str = None) -> dict:
        """Get default fingerprint configuration"""
        config = {
            "automatic_timezone": "1",
            "language": ["en-US", "en"],
            "ua": "",  # Auto-generate
            "flash": "block",
            "scan_port_type": "1",
            "allow_scan_ports": [],
            "audio": "1",
            "webrtc": "proxy",
            "fonts": [],
            "canvas": "1",
            "webgl_image": "1",
            "webgl": "3",
            "client_rects": "1",
            "device_name_switch": "1",
            "random_ua": {
                "ua_browser": ["chrome"],
                "ua_version": ["120", "121", "122", "123", "124", "125"],
            },
        }

        # Adjust language based on country
        if country:
            country_languages = {
                "US": ["en-US", "en"],
                "UK": ["en-GB", "en"],
                "DE": ["de-DE", "de", "en"],
                "FR": ["fr-FR", "fr", "en"],
                "ES": ["es-ES", "es", "en"],
                "IT": ["it-IT", "it", "en"],
                "BR": ["pt-BR", "pt", "en"],
                "JP": ["ja-JP", "ja", "en"],
            }
            config["language"] = country_languages.get(country, ["en-US", "en"])

        return config
