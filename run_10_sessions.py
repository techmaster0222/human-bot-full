"""
Dashboard Test - Simulates 10 bot sessions for dashboard monitoring.
Tests API and dashboard without requiring AdsPower.
"""

import asyncio
import random
import uuid

import httpx
from loguru import logger

# Configuration
API_URL = "http://localhost:8000"
API_KEY = "dev_secret_key_change_me_in_production_2026"

PROXY_CONFIG = {
    "host": "geo.iproyal.com",
    "port": 12321,
    "username": "1yDk0Suq7flACwNg",
    "password": "5o5qYiIfA5cvAC6l",
}

COUNTRIES = ["US", "UK", "DE", "FR", "JP", "CA", "AU", "NL", "SG", "KR"]
DEVICES = ["desktop", "mobile"]
TARGETS = [
    "https://www.google.com",
    "https://www.amazon.com",
    "https://www.youtube.com",
    "https://www.reddit.com",
]
ERRORS = ["Connection timeout", "Proxy blocked", "CAPTCHA detected", "Rate limited"]


async def test_proxy(country: str) -> tuple[bool, str | None, float]:
    """Test proxy and get real IP."""
    proxy_url = (
        f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}_country-{country.lower()}"
        f"@{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
    )

    try:
        async with httpx.AsyncClient(proxy=proxy_url, timeout=15) as client:
            start = asyncio.get_event_loop().time()
            response = await client.get("https://api.ipify.org?format=json")
            latency = asyncio.get_event_loop().time() - start
            return True, response.json().get("ip"), latency
    except Exception:
        return False, None, 0


async def api_request(client: httpx.AsyncClient, method: str, endpoint: str, **kwargs):
    """Make API request with auth header."""
    headers = {"X-API-Key": API_KEY}
    url = f"{API_URL}{endpoint}"

    if method == "GET":
        return await client.get(url, headers=headers, **kwargs)
    return await client.post(url, headers=headers, **kwargs)


async def run_session(session_num: int, client: httpx.AsyncClient) -> bool:
    """Run a single simulated session."""
    session_id = str(uuid.uuid4())
    country = random.choice(COUNTRIES)
    device = random.choice(DEVICES)
    target = random.choice(TARGETS)

    logger.info(f"[Session {session_num}] Starting - Country: {country}, Target: {target}")

    # Test proxy
    proxy_ok, real_ip, latency = await test_proxy(country)
    proxy_address = (
        f"{real_ip}:{PROXY_CONFIG['port']}"
        if proxy_ok and real_ip
        else f"{PROXY_CONFIG['host']}:{PROXY_CONFIG['port']}"
    )

    if proxy_ok:
        logger.info(
            f"[Session {session_num}] Proxy OK - Real IP: {real_ip} (latency: {latency:.2f}s)"
        )
    else:
        logger.warning(f"[Session {session_num}] Proxy test failed, using hostname")

    # Register session
    await api_request(
        client,
        "POST",
        "/api/sessions/register",
        json={
            "session_id": session_id,
            "profile_id": f"profile_{session_num}",
            "device": device,
            "target_url": target,
            "proxy": proxy_address,
            "country": country,
        },
    )

    start_time = asyncio.get_event_loop().time()
    success = True
    error_msg = None

    try:
        # Simulate browsing
        await api_request(
            client,
            "POST",
            "/api/events",
            json={"session_id": session_id, "event_type": "navigation", "details": {"url": target}},
        )

        browse_time = random.uniform(5, 15)
        await asyncio.sleep(browse_time * 0.3)

        await api_request(
            client,
            "POST",
            "/api/events",
            json={
                "session_id": session_id,
                "event_type": "page_load",
                "details": {"load_time_ms": random.randint(500, 3000)},
            },
        )

        await asyncio.sleep(browse_time * 0.3)

        await api_request(
            client,
            "POST",
            "/api/events",
            json={
                "session_id": session_id,
                "event_type": "scroll",
                "details": {"pixels": random.randint(100, 800)},
            },
        )

        await asyncio.sleep(browse_time * 0.4)

        # Random failure (20%)
        if random.random() < 0.2:
            success = False
            error_msg = random.choice(ERRORS)
            await api_request(
                client,
                "POST",
                "/api/events",
                json={
                    "session_id": session_id,
                    "event_type": "error",
                    "details": {"message": error_msg},
                },
            )
            logger.warning(f"[Session {session_num}] Failed: {error_msg}")
        else:
            logger.success(f"[Session {session_num}] Completed successfully")

    except Exception as e:
        success = False
        error_msg = str(e)
        logger.error(f"[Session {session_num}] Exception: {e}")

    duration = asyncio.get_event_loop().time() - start_time
    await api_request(
        client,
        "POST",
        "/api/sessions/end",
        json={
            "session_id": session_id,
            "success": success,
            "duration": duration,
            "error": error_msg,
        },
    )

    return success


async def main():
    """Run 10 simulated sessions."""
    logger.info("=" * 60)
    logger.info("RUNNING 10 BOT SESSIONS")
    logger.info("=" * 60)
    logger.info("Dashboard: http://localhost:3000")
    logger.info(f"API: {API_URL}")
    logger.info("=" * 60)

    # Check API health
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(f"{API_URL}/api/health")
            if response.status_code != 200:
                logger.error("API server not healthy")
                return
            logger.info("API server is healthy")
        except Exception as e:
            logger.error(f"Cannot connect to API: {e}")
            return

        logger.info("\nStarting sessions in 3 seconds... Watch the dashboard!")
        await asyncio.sleep(3)

        # Run sessions
        tasks = []
        for i in range(1, 11):
            tasks.append(run_session(i, client))
            await asyncio.sleep(0.5)

        results = await asyncio.gather(*tasks)

    successful = sum(results)
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info("  Total Sessions: 10")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {10 - successful}")
    logger.info(f"  Success Rate: {successful * 10}%")
    logger.info("=" * 60)
    logger.info("Check the dashboard for full details!")


if __name__ == "__main__":
    asyncio.run(main())
