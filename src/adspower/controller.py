"""
AdsPower Controller
Manages browser profile lifecycle: start, stop, delete, archive.

This module provides clean lifecycle management for AdsPower profiles.
It does NOT set proxies - proxy configuration is done at profile creation time.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger

from .client import AdsPowerClient


@dataclass
class CDPEndpoint:
    """Chrome DevTools Protocol endpoint information"""

    profile_id: str
    puppeteer_ws: str
    selenium_ws: str
    webdriver_path: str
    started_at: datetime

    @property
    def cdp_url(self) -> str:
        """Get the primary CDP URL for Playwright connection"""
        # Playwright prefers puppeteer endpoint
        return self.puppeteer_ws or self.selenium_ws


@dataclass
class ProfileState:
    """Tracks the state of a profile"""

    profile_id: str
    is_running: bool = False
    cdp_endpoint: CDPEndpoint | None = None
    start_count: int = 0
    last_started: datetime | None = None
    last_stopped: datetime | None = None


class AdsPowerController:
    """
    Controller for AdsPower profile lifecycle.

    Responsibilities:
    - Start browser for profile (returns CDP endpoint)
    - Stop browser for profile
    - Delete or archive profile
    - Track profile states

    This controller NEVER sets proxies or modifies fingerprints.
    Those are set at profile creation time via ProfileFactory.

    Usage:
        controller = AdsPowerController(adspower_client)

        # Start profile
        endpoint = await controller.start_profile(profile_id)

        # Use endpoint.cdp_url with Playwright...

        # Stop profile
        await controller.stop_profile(profile_id)

        # Delete profile
        await controller.delete_profile(profile_id)
    """

    def __init__(self, adspower_client: AdsPowerClient):
        """
        Initialize controller.

        Args:
            adspower_client: AdsPower API client
        """
        self.client = adspower_client

        self._profile_states: dict[str, ProfileState] = {}
        self._running_profiles: set[str] = set()

        logger.info("AdsPowerController initialized")

    async def start_profile(
        self,
        profile_id: str,
        headless: bool = False,
        open_url: str | None = None,
        launch_args: list | None = None,
    ) -> CDPEndpoint | None:
        """
        Start browser for a profile.

        Args:
            profile_id: AdsPower profile ID
            headless: Run browser in headless mode (NOT recommended for stealth)
            open_url: URL to open on start
            launch_args: Additional Chrome launch arguments

        Returns:
            CDPEndpoint if successful, None otherwise
        """
        # Check if already running
        if profile_id in self._running_profiles:
            logger.warning(f"Profile {profile_id} is already running")
            state = self._profile_states.get(profile_id)
            if state and state.cdp_endpoint:
                return state.cdp_endpoint

        # Start browser via AdsPower API
        # Note: This is async-wrapped for consistency, but the underlying
        # client is synchronous. In production, consider httpx for true async.
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.start_browser(
                profile_id=profile_id, headless=headless, open_url=open_url, launch_args=launch_args
            ),
        )

        if not response.success:
            logger.error(f"Failed to start profile {profile_id}: {response.msg}")
            return None

        # Extract CDP endpoints from response
        ws_data = response.data.get("ws", {})
        puppeteer_ws = ws_data.get("puppeteer", "")
        selenium_ws = ws_data.get("selenium", "")
        webdriver_path = response.data.get("webdriver", "")

        if not puppeteer_ws and not selenium_ws:
            logger.error(f"No WebSocket URL in response for profile {profile_id}")
            return None

        # Create CDP endpoint
        cdp_endpoint = CDPEndpoint(
            profile_id=profile_id,
            puppeteer_ws=puppeteer_ws,
            selenium_ws=selenium_ws,
            webdriver_path=webdriver_path,
            started_at=datetime.now(timezone.utc),
        )

        # Update state tracking
        if profile_id not in self._profile_states:
            self._profile_states[profile_id] = ProfileState(profile_id=profile_id)

        state = self._profile_states[profile_id]
        state.is_running = True
        state.cdp_endpoint = cdp_endpoint
        state.start_count += 1
        state.last_started = datetime.now(timezone.utc)

        self._running_profiles.add(profile_id)

        logger.success(f"Started profile {profile_id}. CDP: {cdp_endpoint.cdp_url}")
        return cdp_endpoint

    async def stop_profile(self, profile_id: str) -> bool:
        """
        Stop browser for a profile.

        Args:
            profile_id: AdsPower profile ID

        Returns:
            True if successful
        """
        if profile_id not in self._running_profiles:
            logger.debug(f"Profile {profile_id} is not running")
            return True

        # Stop browser via API
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: self.client.stop_browser(profile_id))

        if not response.success:
            logger.error(f"Failed to stop profile {profile_id}: {response.msg}")
            return False

        # Update state
        if profile_id in self._profile_states:
            state = self._profile_states[profile_id]
            state.is_running = False
            state.cdp_endpoint = None
            state.last_stopped = datetime.now(timezone.utc)

        self._running_profiles.discard(profile_id)

        logger.info(f"Stopped profile {profile_id}")
        return True

    async def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a profile from AdsPower.

        Will stop the browser first if running.

        Args:
            profile_id: AdsPower profile ID

        Returns:
            True if successful
        """
        # Stop first if running
        if profile_id in self._running_profiles:
            await self.stop_profile(profile_id)

        # Delete profile
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: self.client.delete_profile([profile_id])
        )

        if not response.success:
            logger.error(f"Failed to delete profile {profile_id}: {response.msg}")
            return False

        # Clean up state
        self._profile_states.pop(profile_id, None)
        self._running_profiles.discard(profile_id)

        logger.info(f"Deleted profile {profile_id}")
        return True

    async def archive_profile(self, profile_id: str) -> bool:
        """
        Archive a profile (stop but don't delete).

        Used for GOOD-tier profiles that may be reused.

        Args:
            profile_id: AdsPower profile ID

        Returns:
            True if successful
        """
        # Just stop the browser, keep the profile
        return await self.stop_profile(profile_id)

    def get_cdp_endpoint(self, profile_id: str) -> str | None:
        """
        Get the CDP endpoint URL for a running profile.

        Args:
            profile_id: AdsPower profile ID

        Returns:
            CDP URL string or None if not running
        """
        state = self._profile_states.get(profile_id)
        if state and state.cdp_endpoint:
            return state.cdp_endpoint.cdp_url
        return None

    def is_running(self, profile_id: str) -> bool:
        """Check if a profile is currently running"""
        return profile_id in self._running_profiles

    def get_running_count(self) -> int:
        """Get count of running profiles"""
        return len(self._running_profiles)

    def get_running_profiles(self) -> set[str]:
        """Get set of running profile IDs"""
        return self._running_profiles.copy()

    async def stop_all(self) -> int:
        """
        Stop all running profiles.

        Returns:
            Number of profiles stopped
        """
        running = list(self._running_profiles)
        stopped = 0

        for profile_id in running:
            if await self.stop_profile(profile_id):
                stopped += 1

        logger.info(f"Stopped {stopped}/{len(running)} profiles")
        return stopped

    async def check_status(self, profile_id: str) -> bool:
        """
        Check if a profile browser is actually running.

        Uses the AdsPower API to verify status.

        Args:
            profile_id: AdsPower profile ID

        Returns:
            True if browser is active
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, lambda: self.client.check_browser_status(profile_id)
        )

        if response.success:
            status = response.data.get("status", "")
            is_active = status == "Active"

            # Sync our state with actual status
            if is_active and profile_id not in self._running_profiles:
                self._running_profiles.add(profile_id)
            elif not is_active and profile_id in self._running_profiles:
                self._running_profiles.discard(profile_id)
                if profile_id in self._profile_states:
                    self._profile_states[profile_id].is_running = False

            return is_active

        return False

    async def cleanup(self):
        """Clean up controller resources"""
        await self.stop_all()
        self._profile_states.clear()
        logger.info("AdsPowerController cleaned up")
