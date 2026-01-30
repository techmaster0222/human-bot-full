"""
AdsPower Bot Engine - Main Entry Point
"""

import asyncio

from loguru import logger

from src.bot import BotSession
from src.core import BotOrchestrator, Config, load_config
from src.core.config import setup_logging
from src.core.orchestrator import OrchestratorConfig


def create_orchestrator_from_config(config: Config) -> BotOrchestrator:
    """Create orchestrator from Config object."""
    orch_config = OrchestratorConfig(
        adspower_url=config.adspower.api_url,
        adspower_api_key=config.adspower.api_key,
        iproyal_username=config.proxy.username,
        iproyal_password=config.proxy.password,
        iproyal_host=config.proxy.host,
        iproyal_port=config.proxy.port,
        proxy_countries=config.proxy.countries,
        sticky_session_duration=config.proxy.sticky_duration,
        max_concurrent_profiles=config.max_concurrent_profiles,
        min_session_duration=config.bot.min_session_duration,
        max_session_duration=config.bot.max_session_duration,
    )
    return BotOrchestrator(orch_config)


async def google_search_task(session: BotSession):
    """Example task: Google search."""
    await session.visit_page("https://www.google.com")
    await session.wait_random(1, 3)
    await session.click_element('textarea[name="q"], input[name="q"]')
    await session.type_in_field(
        'textarea[name="q"], input[name="q"]',
        "python playwright automation",
        submit=True,
    )
    await session.wait_random(2, 4)
    await session.simulate_reading(content_length=2000)
    await session.scroll_down()
    await session.wait_random(1, 2)
    return {"status": "completed", "query": "python playwright automation"}


async def amazon_browse_task(session: BotSession):
    """Example task: Amazon browse."""
    await session.visit_page("https://www.amazon.com")
    await session.wait_random(2, 4)
    await session.click_element("#twotabsearchtextbox")
    await session.type_in_field("#twotabsearchtextbox", "wireless headphones", submit=True)
    await session.wait_random(3, 5)
    await session.scroll_down()
    await session.simulate_reading(content_length=3000)
    return {"status": "completed", "search": "wireless headphones"}


async def reddit_browse_task(session: BotSession):
    """Example task: Reddit browse."""
    await session.visit_page("https://www.reddit.com/r/technology")
    await session.wait_random(2, 4)
    await session.simulate_reading(content_length=5000)
    for _ in range(3):
        await session.scroll_down()
        await session.wait_random(1, 3)
    return {"status": "completed", "subreddit": "technology"}


async def run_bot_sessions(config: Config, num_sessions: int = 3):
    """Run bot sessions with tasks."""
    orchestrator = create_orchestrator_from_config(config)

    tasks = [google_search_task, amazon_browse_task, reddit_browse_task]
    countries = config.proxy.countries or ["US", "UK", "DE"]
    devices = ["desktop", "mobile"]

    logger.info("=" * 60)
    logger.info(f"Starting {num_sessions} bot sessions")
    logger.info("=" * 60)

    results = []
    for i in range(num_sessions):
        country = countries[i % len(countries)]
        device = devices[i % len(devices)]
        task_func = tasks[i % len(tasks)]

        logger.info(f"[Session {i + 1}] Country: {country}, Device: {device}")

        try:
            result = await orchestrator.run_session(
                task_func=task_func, country=country, device=device
            )
            results.append({"session": i + 1, "success": True, "result": result})
            logger.success(f"[Session {i + 1}] Completed")
        except Exception as e:
            results.append({"session": i + 1, "success": False, "error": str(e)})
            logger.error(f"[Session {i + 1}] Failed: {e}")

    successful = sum(1 for r in results if r["success"])
    logger.info("=" * 60)
    logger.info(f"Results: {successful}/{num_sessions} successful")
    logger.info("=" * 60)

    return results


async def main():
    """Main entry point."""
    config = load_config()
    setup_logging(config)

    logger.info("AdsPower Bot Engine Starting...")
    logger.info(f"AdsPower URL: {config.adspower.api_url}")
    logger.info(f"Proxy Provider: IPRoyal ({config.proxy.host})")

    try:
        results = await run_bot_sessions(config, num_sessions=3)
        return results
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
