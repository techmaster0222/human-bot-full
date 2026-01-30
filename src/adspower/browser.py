"""
AdsPower Browser Controller
Controls browser instances through AdsPower API and Playwright.
"""

import asyncio

from loguru import logger
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from .client import AdsPowerClient
from .profile import Profile, ProfileManager


class BrowserController:
    """
    Controller for AdsPower browser instances using Playwright.

    Manages browser lifecycle and provides Playwright connections
    to AdsPower browser profiles via CDP (Chrome DevTools Protocol).
    """

    def __init__(self, client: AdsPowerClient, profile_manager: ProfileManager):
        """
        Initialize BrowserController.

        Args:
            client: AdsPowerClient instance
            profile_manager: ProfileManager instance
        """
        self.client = client
        self.profile_manager = profile_manager
        self._browsers: dict[str, Browser] = {}
        self._contexts: dict[str, BrowserContext] = {}
        self._pages: dict[str, Page] = {}
        self._playwright: Playwright | None = None

        logger.info("BrowserController initialized (Playwright)")

    async def _ensure_playwright(self):
        """Ensure Playwright is initialized"""
        if self._playwright is None:
            self._playwright = await async_playwright().start()

    async def start_browser(
        self,
        profile: Profile,
        headless: bool = False,
        open_url: str = None,
        launch_args: list = None,
    ) -> Page | None:
        """
        Start browser for a profile and return Playwright Page.

        Args:
            profile: Profile instance to start
            headless: Run in headless mode
            open_url: URL to open on start
            launch_args: Additional Chrome arguments

        Returns:
            Playwright Page connected to AdsPower browser
        """
        # Check if already running
        if profile.id in self._pages:
            logger.warning(f"Browser already running for profile {profile.id}")
            return self._pages[profile.id]

        # Start browser via AdsPower API
        response = self.client.start_browser(
            profile_id=profile.id, headless=headless, open_url=open_url, launch_args=launch_args
        )

        if not response.success:
            logger.error(f"Failed to start browser: {response.msg}")
            return None

        # Extract CDP endpoint from response
        ws_data = response.data.get("ws", {})
        # AdsPower returns puppeteer WebSocket URL, we need to convert for Playwright
        puppeteer_ws = ws_data.get("puppeteer", "")
        selenium_ws = ws_data.get("selenium", "")

        if not puppeteer_ws and not selenium_ws:
            logger.error("No WebSocket URL in response")
            return None

        # Use puppeteer endpoint for CDP connection
        cdp_endpoint = puppeteer_ws or selenium_ws

        # Connect Playwright to the browser via CDP
        try:
            page = await self._connect_playwright(cdp_endpoint, profile.id)

            if page:
                self._pages[profile.id] = page
                self.profile_manager.mark_profile_active(profile, cdp_endpoint, "")
                logger.success(f"Browser started and connected for profile: {profile.name}")
                return page

        except Exception as e:
            logger.error(f"Failed to connect Playwright: {e}")
            # Try to stop the browser we started
            self.client.stop_browser(profile.id)

        return None

    async def _connect_playwright(self, cdp_endpoint: str, profile_id: str) -> Page | None:
        """
        Connect Playwright to AdsPower browser via CDP.

        Args:
            cdp_endpoint: WebSocket URL for CDP connection
            profile_id: Profile ID for tracking

        Returns:
            Connected Page instance
        """
        try:
            await self._ensure_playwright()

            # Connect to browser via CDP
            browser = await self._playwright.chromium.connect_over_cdp(cdp_endpoint)

            self._browsers[profile_id] = browser

            # Get existing context (AdsPower creates one)
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
            else:
                context = await browser.new_context()

            self._contexts[profile_id] = context

            # Get existing page or create new one
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = await context.new_page()

            logger.debug("Playwright connected to CDP endpoint")
            return page

        except Exception as e:
            logger.error(f"Playwright CDP connection error: {e}")
            return None

    async def stop_browser(self, profile_id: str) -> bool:
        """
        Stop browser for a profile.

        Args:
            profile_id: Profile ID to stop

        Returns:
            True if successful
        """
        # Close Playwright connections first
        if profile_id in self._pages:
            try:
                await self._pages[profile_id].close()
            except Exception as e:
                logger.debug(f"Error closing page: {e}")
            finally:
                del self._pages[profile_id]

        if profile_id in self._contexts:
            try:
                await self._contexts[profile_id].close()
            except Exception as e:
                logger.debug(f"Error closing context: {e}")
            finally:
                del self._contexts[profile_id]

        if profile_id in self._browsers:
            try:
                await self._browsers[profile_id].close()
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            finally:
                del self._browsers[profile_id]

        # Stop browser via AdsPower API
        response = self.client.stop_browser(profile_id)

        if response.success:
            self.profile_manager.mark_profile_inactive(profile_id)
            logger.info(f"Browser stopped for profile: {profile_id}")
            return True

        logger.error(f"Failed to stop browser: {response.msg}")
        return False

    async def stop_all_browsers(self) -> int:
        """
        Stop all running browsers.

        Returns:
            Number of browsers stopped
        """
        profile_ids = list(self._pages.keys())
        stopped = 0

        for profile_id in profile_ids:
            if await self.stop_browser(profile_id):
                stopped += 1

        logger.info(f"Stopped {stopped} browsers")
        return stopped

    def get_page(self, profile_id: str) -> Page | None:
        """Get Playwright Page for a profile"""
        return self._pages.get(profile_id)

    def get_context(self, profile_id: str) -> BrowserContext | None:
        """Get Playwright BrowserContext for a profile"""
        return self._contexts.get(profile_id)

    async def is_browser_running(self, profile_id: str) -> bool:
        """Check if browser is running for a profile"""
        # Check our local tracking first
        if profile_id in self._pages:
            try:
                # Verify page is still valid
                _ = self._pages[profile_id].url
                return True
            except Exception:
                # Page is dead, clean up
                del self._pages[profile_id]
                self._browsers.pop(profile_id, None)
                self._contexts.pop(profile_id, None)
                self.profile_manager.mark_profile_inactive(profile_id)
                return False

        # Check via API
        response = self.client.check_browser_status(profile_id)
        return response.success and response.data.get("status") == "Active"

    async def restart_browser(
        self, profile: Profile, headless: bool = False, open_url: str = None
    ) -> Page | None:
        """
        Restart browser for a profile.

        Args:
            profile: Profile to restart
            headless: Run in headless mode
            open_url: URL to open

        Returns:
            New Page instance
        """
        await self.stop_browser(profile.id)
        await asyncio.sleep(2)  # Brief pause before restarting
        return await self.start_browser(profile, headless=headless, open_url=open_url)

    def get_running_count(self) -> int:
        """Get number of running browsers"""
        return len(self._pages)

    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up BrowserController resources")
        await self.stop_all_browsers()

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


# Synchronous wrapper for non-async usage
class SyncBrowserController:
    """
    Synchronous wrapper for BrowserController.

    Use this if you prefer synchronous code.
    """

    def __init__(self, client: AdsPowerClient, profile_manager: ProfileManager):
        self._async_controller = BrowserController(client, profile_manager)
        self._loop = None

    def _get_loop(self):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def start_browser(self, profile: Profile, **kwargs) -> Page | None:
        return self._get_loop().run_until_complete(
            self._async_controller.start_browser(profile, **kwargs)
        )

    def stop_browser(self, profile_id: str) -> bool:
        return self._get_loop().run_until_complete(self._async_controller.stop_browser(profile_id))

    def stop_all_browsers(self) -> int:
        return self._get_loop().run_until_complete(self._async_controller.stop_all_browsers())

    def get_page(self, profile_id: str) -> Page | None:
        return self._async_controller.get_page(profile_id)

    def cleanup(self):
        self._get_loop().run_until_complete(self._async_controller.cleanup())
        if self._loop:
            self._loop.close()
