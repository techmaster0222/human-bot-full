import asyncio
from loguru import logger

from src.core import BotOrchestrator, load_config, Config
from src.core.config import setup_logging
from src.core.orchestrator import OrchestratorConfig
from src.bot import BotSession


def create_orchestrator_from_config(config: Config) -> BotOrchestrator:
    """Create orchestrator from Config object"""
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
        max_session_duration=config.bot.max_session_duration
    )
    
    return BotOrchestrator(orch_config)


# ============== Example Tasks (Async) ==============

async def example_google_search_task(session: BotSession):
    # Navigate to Google
    await session.visit_page("https://www.google.com")
    
    # Wait for page to settle
    await session.wait_random(1, 3)
    
    # Find and click search box, type query
    await session.click_element('textarea[name="q"], input[name="q"]')
    await session.type_in_field(
        'textarea[name="q"], input[name="q"]',
        "python playwright automation",
        submit=True
    )
    
    # Wait for results
    await session.wait_random(2, 4)
    
    # Simulate reading results
    await session.simulate_reading(content_length=2000)
    
    # Scroll through results naturally
    for _ in range(3):
        await session.scroll("down")
        await session.wait_random(1, 3)
    
    # Check network requests made
    requests = session.get_requests_by_type("xhr")
    logger.info(f"XHR requests made: {len(requests)}")
    
    logger.info("Google search task completed")


async def example_website_browse_task(session: BotSession):
    """
    Example task: Browse a website naturally with routing decisions.
    
    Demonstrates:
    - Link discovery
    - Random navigation
    - Content analysis
    """
    # Navigate to example site
    await session.visit_page("https://news.ycombinator.com")
    
    # Simulate reading the page
    await session.simulate_reading(content_length=1500)
    
    # Get all links on the page
    links = await session.get_all_links()
    logger.info(f"Found {len(links)} links on page")
    
    # Scroll down to see more content
    await session.scroll("down")
    await session.wait_random(2, 4)
    
    # Click on a story link (routing decision)
    story_links = [l for l in links if "item?id=" in l]
    if story_links:
        # Click first available story
        await session.click_element(f'a[href*="item?id="]')
        await session.wait_random(2, 3)
        await session.simulate_reading(2000)
    
    logger.info("Website browse task completed")


async def example_form_interaction_task(session: BotSession):
    """
    Example task: Interact with forms using human-like behavior.
    
    Demonstrates:
    - Form field interaction
    - Checkbox/radio handling
    - Button clicks
    """
    # This is a template - customize for your specific form
    
    # Navigate to a form page
    await session.visit_page("https://httpbin.org/forms/post")
    
    # Fill text fields with natural typing
    await session.type_in_field('input[name="custname"]', "John Doe")
    await session.wait_random(0.5, 1.5)
    
    await session.type_in_field('input[name="custtel"]', "555-1234")
    await session.wait_random(0.5, 1.5)
    
    await session.type_in_field('input[name="custemail"]', "john@example.com")
    await session.wait_random(0.5, 1.5)
    
    # Select dropdown/radio
    await session.click_element('input[value="medium"]')
    
    # Fill textarea
    await session.type_in_field(
        'textarea[name="comments"]',
        "This is a test comment with natural typing speed."
    )
    
    # Pause before submit (human hesitation)
    await session.wait_random(1, 3)
    
    # Click submit
    await session.click_element('button[type="submit"]')
    
    logger.info("Form interaction task completed")


async def example_network_monitoring_task(session: BotSession):
    """
    Example task: Monitor network requests during browsing.
    
    Demonstrates:
    - Network request tracking
    - Waiting for specific requests
    - Analyzing traffic patterns
    """
    # Clear any existing tracked requests
    session.actions.clear_network_requests()
    
    # Navigate to a page
    await session.visit_page("https://jsonplaceholder.typicode.com/")
    
    # Wait for network to settle
    await session.actions.wait_for_network_idle()
    
    # Get all requests made
    all_requests = session.get_network_requests()
    logger.info(f"Total network requests: {len(all_requests)}")
    
    # Filter by type
    xhr_requests = session.get_requests_by_type("xhr")
    fetch_requests = session.get_requests_by_type("fetch")
    
    logger.info(f"XHR: {len(xhr_requests)}, Fetch: {len(fetch_requests)}")
    
    # Click something that triggers an API call
    await session.click_element('a[href="/posts"]')
    
    # Wait for the API response
    try:
        response = await session.wait_for_response("**/posts**", timeout=10000)
        logger.info(f"Got posts response: {response.status}")
    except:
        logger.warning("No posts response received")
    
    logger.info("Network monitoring task completed")


# ============== Main Examples ==============

async def run_single_profile_example():
    """Example: Run a task on a single profile"""
    
    # Load configuration
    config = load_config()
    setup_logging(config)
    
    # Create orchestrator
    orchestrator = create_orchestrator_from_config(config)
    
    try:
        # Check AdsPower status
        if not orchestrator.adspower_client.check_status():
            logger.error("AdsPower is not running! Please start AdsPower first.")
            return
        
        # Create a profile with proxy
        profile = orchestrator.create_profile(
            name="test_profile_1",
            country="US",
            domain="google.com"
        )
        
        if not profile:
            logger.error("Failed to create profile")
            return
        
        logger.info(f"Created profile: {profile.name} ({profile.id})")
        
        # Run async task on the profile
        result = await orchestrator.run_task(
            profile=profile,
            task=example_google_search_task,
            headless=False  # Set True for headless mode
        )
        
        # Print status
        orchestrator.print_status()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        
    finally:
        # Cleanup
        await orchestrator.cleanup()


async def run_multiple_profiles_example():
    """Example: Run tasks on multiple profiles in parallel"""
    
    config = load_config()
    setup_logging(config)
    orchestrator = create_orchestrator_from_config(config)
    
    try:
        if not orchestrator.adspower_client.check_status():
            logger.error("AdsPower is not running!")
            return
        
        # Create multiple profiles with different countries
        profiles = orchestrator.create_profiles(
            count=3,
            name_prefix="multi_bot",
            countries=["US", "UK", "DE"]
        )
        
        logger.info(f"Created {len(profiles)} profiles")
        
        # Run task on all profiles in parallel
        results = await orchestrator.run_on_all_profiles(
            task=example_website_browse_task,
            profiles=profiles,
            parallel=True,  # Parallel execution
            max_concurrent=3
        )
        
        # Print results
        for profile_id, result in results.items():
            logger.info(f"Profile {profile_id}: {result}")
        
        orchestrator.print_status()
        
    finally:
        await orchestrator.cleanup()


async def run_custom_task_example():
    """Example: Create and run a custom task"""
    
    config = load_config()
    setup_logging(config)
    orchestrator = create_orchestrator_from_config(config)
    
    # Define your custom async task
    async def my_custom_task(session: BotSession):
        """Your custom automation logic here"""
        
        # Visit target website
        await session.visit_page("https://your-target-site.com")
        
        # Your automation steps...
        await session.wait_random(2, 5)
        await session.scroll("down")
        
        # Example: Click a button
        # await session.click_element(".my-button")
        
        # Example: Fill a form
        # await session.type_in_field("#username", "myuser")
        # await session.type_in_field("#password", "mypass")
        
        # Check for success element
        # success = await session.check_element_exists(".success-message")
        
        # Simulate natural behavior
        await session.simulate_reading(1000)
        
        logger.info("Custom task completed!")
        return {"status": "success"}
    
    try:
        if not orchestrator.adspower_client.check_status():
            logger.error("AdsPower is not running!")
            return
        
        profile = orchestrator.create_profile(
            name="custom_task_profile",
            country="US"
        )
        
        if profile:
            result = await orchestrator.run_task(profile, my_custom_task)
            logger.info(f"Task result: {result}")
            
    finally:
        await orchestrator.cleanup()


# ============== Quick Start ==============

def quick_start():
    """
    Quick start guide - run this to test the setup.
    
    Prerequisites:
    1. AdsPower must be running
    2. IPRoyal credentials in .env file
    3. pip install playwright && playwright install chromium
    """
    print("""
    +---------------------------------------------------------------+
    |    AdsPower + IPRoyal + Human Bot (Playwright) - Quick Start  |
    +---------------------------------------------------------------+
    |                                                               |
    |  Before running:                                              |
    |  1. Make sure AdsPower is running on your system              |
    |  2. Copy .env.example to .env and fill in your credentials    |
    |  3. Install dependencies:                                     |
    |     pip install -r requirements.txt                           |
    |     playwright install chromium                               |
    |                                                               |
    +---------------------------------------------------------------+
    """)
    
    try:
        config = load_config()
        setup_logging(config)
        
        if not config.proxy.username or not config.proxy.password:
            logger.warning("IPRoyal credentials not set in .env file")
            logger.info("Set IPROYAL_USERNAME and IPROYAL_PASSWORD in .env")
        
        orchestrator = create_orchestrator_from_config(config)
        
        if orchestrator.adspower_client.check_status():
            logger.success("AdsPower is running and accessible!")
            orchestrator.print_status()
        else:
            logger.error("Cannot connect to AdsPower. Make sure it's running.")
            logger.info(f"AdsPower API URL: {config.adspower.api_url}")
        
    except Exception as e:
        logger.error(f"Setup error: {e}")
        logger.info("Make sure all dependencies are installed:")
        logger.info("  pip install -r requirements.txt")
        logger.info("  playwright install chromium")


if __name__ == "__main__":
    # Run quick start by default
    quick_start()
    
    # Uncomment to run async examples:
    # asyncio.run(run_single_profile_example())
    # asyncio.run(run_multiple_profiles_example())
    # asyncio.run(run_custom_task_example())
