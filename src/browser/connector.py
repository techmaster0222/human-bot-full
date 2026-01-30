"""
Browser Connector
Connects to AdsPower browsers via Chrome DevTools Protocol (CDP).

This module NEVER launches browsers. It ONLY connects to existing browsers
that were started by AdsPower via the AdsPowerController.

Architecture:
    AdsPower starts browser → provides CDP endpoint → BrowserConnector attaches
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


@dataclass
class BrowserConnection:
    """Represents an active browser connection"""

    profile_id: str
    cdp_endpoint: str
    browser: Browser
    context: BrowserContext
    page: Page
    connected_at: datetime

    @property
    def is_valid(self) -> bool:
        """Check if connection is still valid"""
        try:
            # Try to access page URL to verify connection
            _ = self.page.url
            return True
        except Exception:
            return False


class BrowserConnector:
    """
    Connects Playwright to AdsPower browsers via CDP.

    Key principles:
    - NEVER launches browsers
    - NEVER sets proxies
    - ONLY connects via connect_over_cdp()
    - Clean disconnect when done

    Usage:
        connector = BrowserConnector()

        # Connect to AdsPower browser
        page = await connector.connect(cdp_endpoint, profile_id)

        # Use page for automation...

        # Disconnect when done
        await connector.disconnect(profile_id)

        # Cleanup all
        await connector.cleanup()
    """

    def __init__(self):
        """Initialize BrowserConnector"""
        self._playwright: Playwright | None = None
        self._connections: dict[str, BrowserConnection] = {}

        logger.info("BrowserConnector initialized (CDP-only)")

    async def _ensure_playwright(self):
        """Ensure Playwright is initialized"""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def connect(self, cdp_endpoint: str, profile_id: str) -> Page | None:
        """
        Connect to an AdsPower browser via CDP.

        The browser must already be running (started by AdsPowerController).
        This method NEVER starts browsers.

        Args:
            cdp_endpoint: CDP WebSocket URL (from AdsPowerController)
            profile_id: AdsPower profile ID for tracking

        Returns:
            Playwright Page if successful, None otherwise
        """
        # Check if already connected
        if profile_id in self._connections:
            conn = self._connections[profile_id]
            if conn.is_valid:
                logger.debug(f"Reusing existing connection for profile {profile_id}")
                return conn.page
            else:
                # Connection is stale, clean up
                await self._close_connection(profile_id)

        await self._ensure_playwright()

        try:
            # Connect via CDP - this does NOT launch a browser
            browser = await self._playwright.chromium.connect_over_cdp(cdp_endpoint)

            # Get existing context (AdsPower creates one)
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
            else:
                # Fallback: create new context (shouldn't normally happen)
                context = await browser.new_context()

            # Get existing page or create new one
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()

            # Create connection record
            connection = BrowserConnection(
                profile_id=profile_id,
                cdp_endpoint=cdp_endpoint,
                browser=browser,
                context=context,
                page=page,
                connected_at=datetime.now(timezone.utc),
            )

            self._connections[profile_id] = connection

            logger.success(f"Connected to browser for profile {profile_id}")
            return page

        except Exception as e:
            logger.error(f"Failed to connect to browser for profile {profile_id}: {e}")
            return None

    async def disconnect(self, profile_id: str) -> bool:
        """
        Disconnect from a browser.

        This closes the Playwright connection but does NOT stop the browser.
        The browser continues running in AdsPower.

        Args:
            profile_id: Profile ID to disconnect

        Returns:
            True if disconnected successfully
        """
        if profile_id not in self._connections:
            logger.debug(f"No connection found for profile {profile_id}")
            return True

        return await self._close_connection(profile_id)

    async def _close_connection(self, profile_id: str) -> bool:
        """Close a connection and clean up resources"""
        if profile_id not in self._connections:
            return True

        conn = self._connections[profile_id]

        try:
            # Close page first
            try:
                await conn.page.close()
            except Exception as e:
                logger.debug(f"Error closing page for {profile_id}: {e}")

            # Don't close context - it belongs to AdsPower
            # Don't close browser - it's managed by AdsPower

            # But we need to disconnect our CDP connection
            try:
                # Playwright doesn't have explicit disconnect, but closing
                # our references should release them
                pass
            except Exception as e:
                logger.debug(f"Error disconnecting from {profile_id}: {e}")

            del self._connections[profile_id]
            logger.info(f"Disconnected from browser for profile {profile_id}")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting from profile {profile_id}: {e}")
            # Still remove from tracking
            self._connections.pop(profile_id, None)
            return False

    def get_page(self, profile_id: str) -> Page | None:
        """
        Get the Playwright Page for a connected profile.

        Args:
            profile_id: Profile ID

        Returns:
            Page if connected, None otherwise
        """
        conn = self._connections.get(profile_id)
        if conn and conn.is_valid:
            return conn.page
        return None

    def get_context(self, profile_id: str) -> BrowserContext | None:
        """
        Get the BrowserContext for a connected profile.

        Args:
            profile_id: Profile ID

        Returns:
            BrowserContext if connected, None otherwise
        """
        conn = self._connections.get(profile_id)
        if conn and conn.is_valid:
            return conn.context
        return None

    def is_connected(self, profile_id: str) -> bool:
        """Check if we have an active connection to a profile"""
        conn = self._connections.get(profile_id)
        return conn is not None and conn.is_valid

    def get_connection_count(self) -> int:
        """Get count of active connections"""
        return len(self._connections)

    def get_connected_profiles(self) -> list:
        """Get list of connected profile IDs"""
        return list(self._connections.keys())

    async def disconnect_all(self) -> int:
        """
        Disconnect from all browsers.

        Returns:
            Number of connections closed
        """
        profile_ids = list(self._connections.keys())
        disconnected = 0

        for profile_id in profile_ids:
            if await self.disconnect(profile_id):
                disconnected += 1

        logger.info(f"Disconnected from {disconnected}/{len(profile_ids)} browsers")
        return disconnected

    async def cleanup(self):
        """
        Clean up all resources.

        Call this when done with the connector.
        """
        logger.info("Cleaning up BrowserConnector...")

        await self.disconnect_all()

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("BrowserConnector cleaned up")
