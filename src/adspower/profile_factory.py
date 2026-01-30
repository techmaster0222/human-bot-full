"""
Profile Factory
Creates disposable AdsPower profiles with IPRoyal sticky sessions.

PROFILE OWNERSHIP & SCOPE
=========================
- This system EXCLUSIVELY manages AdsPower profiles it creates itself
- Existing AdsPower profiles (manually created or legacy) are IGNORED
- Profiles are disposable by default and tied to a single session lifecycle
- Profile import/reuse from external sources is explicitly OUT OF SCOPE

Core rotation model:
- One profile = one human identity
- One profile = one residential IP
- Profiles are disposable by default
- No profile reuse unless explicitly allowed by scoring logic
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from ..core.constants import (
    COUNTRY_LANGUAGES,
    DEFAULT_FINGERPRINT_TEMPLATE,
)
from ..proxy.session_manager import ProxySession, ProxySessionManager
from .client import AdsPowerClient


@dataclass
class ProfileInfo:
    """
    Information about a created profile.

    Contains all data needed to track and manage a disposable profile.
    """

    profile_id: str
    profile_name: str
    session_id: str
    proxy_session: ProxySession
    country: str
    created_at: datetime
    fingerprint_template: dict

    @property
    def proxy_username(self) -> str:
        """Get the proxy username for this profile"""
        return self.proxy_session.proxy_username


class ProfileFactory:
    """
    Factory for creating disposable AdsPower profiles.

    Each profile is created with:
    - A unique proxy session (via ProxySessionManager)
    - A fingerprint configuration based on country
    - Tracking information for lifecycle management

    Profiles created by this factory are intended to be disposable.
    They should be destroyed after use unless explicitly allowed for reuse.

    Usage:
        factory = ProfileFactory(adspower_client, proxy_manager)
        profile_info = factory.create_profile(country="US")
        # Use profile...
        factory.destroy_profile(profile_info.profile_id)
    """

    def __init__(
        self,
        adspower_client: AdsPowerClient,
        proxy_manager: ProxySessionManager,
        group_id: str = "0",
    ):
        """
        Initialize ProfileFactory.

        Args:
            adspower_client: AdsPower API client
            proxy_manager: Proxy session manager for creating sessions
            group_id: AdsPower group ID for organizing profiles
        """
        self.adspower_client = adspower_client
        self.proxy_manager = proxy_manager
        self.group_id = group_id

        self._created_profiles: dict[str, ProfileInfo] = {}
        self._profile_counter = 0

        logger.info("ProfileFactory initialized")

    def create_profile(
        self,
        country: str,
        state: str | None = None,
        city: str | None = None,
        name_prefix: str = "human",
        fingerprint_template: dict | None = None,
        sticky_duration: int = 600,
    ) -> ProfileInfo | None:
        """
        Create a new disposable profile with proxy session.

        Args:
            country: Target country code (e.g., "US", "UK")
            state: Target state (optional, for US)
            city: Target city (optional)
            name_prefix: Prefix for profile name
            fingerprint_template: Custom fingerprint config (uses default if None)
            sticky_duration: Proxy session duration in seconds

        Returns:
            ProfileInfo if successful, None otherwise
        """
        # Create proxy session first
        proxy_session = self.proxy_manager.create_session(
            country=country, state=state, city=city, duration=sticky_duration
        )

        # Generate profile name
        self._profile_counter += 1
        profile_name = f"{name_prefix}_{proxy_session.session_id}"

        # Build fingerprint configuration
        fingerprint_config = self._build_fingerprint_config(
            country=country, template=fingerprint_template
        )

        # Create profile in AdsPower
        response = self.adspower_client.create_profile(
            name=profile_name,
            group_id=self.group_id,
            proxy_config=proxy_session.to_adspower_config(),
            fingerprint_config=fingerprint_config,
        )

        if not response.success:
            logger.error(f"Failed to create profile: {response.msg}")
            # Clean up proxy session
            self.proxy_manager.end_session(proxy_session.session_id)
            return None

        profile_id = response.data.get("id", "")

        # Mark proxy session as used by this profile
        self.proxy_manager.mark_session_used(proxy_session.session_id, profile_id)

        # Create ProfileInfo
        profile_info = ProfileInfo(
            profile_id=profile_id,
            profile_name=profile_name,
            session_id=proxy_session.session_id,
            proxy_session=proxy_session,
            country=country,
            created_at=datetime.now(timezone.utc),
            fingerprint_template=fingerprint_config,
        )

        self._created_profiles[profile_id] = profile_info

        logger.success(
            f"Created profile: {profile_name} (ID: {profile_id}, session: {proxy_session.session_id})"
        )
        return profile_info

    def get_profile_info(self, profile_id: str) -> ProfileInfo | None:
        """Get information about a created profile"""
        return self._created_profiles.get(profile_id)

    def destroy_profile(self, profile_id: str) -> bool:
        """
        Destroy a profile and its associated proxy session.

        Args:
            profile_id: AdsPower profile ID to destroy

        Returns:
            True if successful
        """
        profile_info = self._created_profiles.get(profile_id)

        # Delete from AdsPower
        response = self.adspower_client.delete_profile([profile_id])

        if not response.success:
            logger.error(f"Failed to delete profile {profile_id}: {response.msg}")
            return False

        # Clean up proxy session if we have info
        if profile_info:
            self.proxy_manager.end_session(profile_info.session_id)
            del self._created_profiles[profile_id]

        logger.info(f"Destroyed profile: {profile_id}")
        return True

    def destroy_all_profiles(self) -> int:
        """
        Destroy all profiles created by this factory.

        Returns:
            Number of profiles destroyed
        """
        profile_ids = list(self._created_profiles.keys())
        destroyed = 0

        for profile_id in profile_ids:
            if self.destroy_profile(profile_id):
                destroyed += 1

        logger.info(f"Destroyed {destroyed}/{len(profile_ids)} profiles")
        return destroyed

    def get_created_profile_count(self) -> int:
        """Get count of profiles created by this factory"""
        return len(self._created_profiles)

    def get_all_profile_ids(self) -> list:
        """Get all profile IDs created by this factory"""
        return list(self._created_profiles.keys())

    def _build_fingerprint_config(self, country: str, template: dict | None = None) -> dict:
        """
        Build fingerprint configuration for a country.

        Args:
            country: Target country code
            template: Base template to use (uses default if None)

        Returns:
            Fingerprint configuration dict
        """
        # Start with template or default
        config = (template or DEFAULT_FINGERPRINT_TEMPLATE).copy()

        # Set language based on country
        if country.upper() in COUNTRY_LANGUAGES:
            config["language"] = COUNTRY_LANGUAGES[country.upper()]
        else:
            # Default to English
            config["language"] = ["en-US", "en"]

        return config
