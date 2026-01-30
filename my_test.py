"""
Bot Detection Test - Tests browser against detection sites.
"""

import asyncio

from loguru import logger

from src.adspower import AdsPowerClient, BrowserController, ProfileManager
from src.api import get_tracker
from src.bot import BotActions, HumanBehavior
from src.core import load_config
from src.core.config import setup_logging
from src.proxy import IPRoyalProxy

TEST_SITES = [
    ("sannysoft", "https://bot.sannysoft.com", 5),
    ("pixelscan", "https://pixelscan.net", 8),
    ("creepjs", "https://abrahamjuliot.github.io/creepjs", 10),
]


async def run_detection_test():
    """Run bot detection test with dashboard tracking."""
    config = load_config()
    setup_logging(config)
    tracker = get_tracker(use_local=True, track_proxy_stats=True)

    logger.info("=" * 60)
    logger.info("BOT DETECTION TEST")
    logger.info("=" * 60)

    # Initialize AdsPower
    client = AdsPowerClient(config.adspower.api_url, config.adspower.api_key)
    if not client.check_status():
        logger.error("AdsPower is not running!")
        return False

    logger.info("AdsPower connected")

    profile_manager = ProfileManager(client)
    browser_controller = BrowserController(client, profile_manager)

    # Create proxy
    proxy = IPRoyalProxy(username=config.proxy.username, password=config.proxy.password)
    proxy_config, proxy_session = proxy.get_sticky_proxy(country="US", duration=600)
    proxy_address = f"{proxy_config.host}:{proxy_config.port}"

    logger.info(f"Proxy: {proxy_address} (session: {proxy_session})")

    # Create profile
    profile = profile_manager.create_profile(
        name="detection_test",
        proxy_host=proxy_config.host,
        proxy_port=proxy_config.port,
        proxy_user=proxy_config.username,
        proxy_pass=proxy_config.password,
        country="US",
        group_id=config.adspower.default_group_id,
    )

    if not profile:
        logger.error("Failed to create profile")
        return False

    logger.info(f"Profile created: {profile.name} ({profile.id})")

    session_id = None
    test_results = {name: None for name, _, _ in TEST_SITES}

    try:
        # Start browser
        vps_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        page = await browser_controller.start_browser(profile, launch_args=vps_args)

        if not page:
            logger.error("Failed to start browser")
            return False

        logger.info("Browser started")

        session_id = tracker.start_session(
            profile_id=profile.id,
            device="desktop",
            target_url="bot detection test",
            proxy=proxy_address,
            country="US",
        )

        behavior = HumanBehavior()
        actions = BotActions(page, behavior)

        # Run tests
        for name, url, wait_time in TEST_SITES:
            logger.info("-" * 40)
            logger.info(f"Test: {name}")

            await actions.navigate_to(url, wait_until="networkidle")
            tracker.log_navigation(session_id, url)
            await asyncio.sleep(wait_time)

            test_results[name] = await page.evaluate("() => navigator.webdriver")
            logger.info(f"  webdriver = {test_results[name]}")

            await actions.scroll_down()
            await asyncio.sleep(1)

            try:
                await actions.take_screenshot(f"screenshots/{name}.png", full_page=True)
            except Exception:
                logger.warning(f"Screenshot failed for {name}")

        # Results
        logger.info("=" * 60)
        logger.info("RESULTS")
        logger.info("=" * 60)

        all_passed = all(v is False or v is None for v in test_results.values())

        for test, result in test_results.items():
            status = "PASS" if result is False or result is None else "FAIL"
            logger.info(f"  {test}: webdriver={result} [{status}]")

        if all_passed:
            logger.success("All tests passed - Bot not detected!")
        else:
            logger.warning("Some tests may have issues")

        if session_id:
            tracker.end_session(session_id, success=all_passed)

        # Keep browser open for inspection
        logger.info("\nBrowser open for 2 minutes for inspection...")
        for remaining in range(120, 0, -30):
            logger.info(f"  Closing in {remaining}s...")
            await asyncio.sleep(30)

        return all_passed

    except Exception as e:
        logger.error(f"Test failed: {e}")
        if session_id:
            tracker.log_error(session_id, str(e))
            tracker.end_session(session_id, success=False, error=str(e))
        return False

    finally:
        logger.info("Cleaning up...")
        await browser_controller.stop_browser(profile.id)
        profile_manager.delete_profile(profile.id)
        await browser_controller.cleanup()


if __name__ == "__main__":
    asyncio.run(run_detection_test())
