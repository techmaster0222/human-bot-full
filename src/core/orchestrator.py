"""
Bot Orchestrator (Async Playwright)
Main coordinator that ties together AdsPower, IPRoyal proxies, and the human bot.
"""

import asyncio
import time
import random
from typing import Optional, Dict, List, Any, Callable, Awaitable
from dataclasses import dataclass
from loguru import logger

from ..adspower import AdsPowerClient, ProfileManager, BrowserController
from ..proxy import IPRoyalProxy, ProxyRotator
from ..bot import HumanBehavior, BotActions, BotSession, SessionManager
from ..bot.human_behavior import BehaviorConfig
from ..bot.session import SessionConfig


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    # AdsPower
    adspower_url: str = "http://local.adspower.net:50325"
    adspower_api_key: str = None
    
    # IPRoyal
    iproyal_username: str = ""
    iproyal_password: str = ""
    iproyal_host: str = "geo.iproyal.com"
    iproyal_port: int = 12321
    
    # Proxy settings
    proxy_countries: List[str] = None
    sticky_session_duration: int = 600
    
    # Concurrency
    max_concurrent_profiles: int = 5
    
    # Session defaults
    min_session_duration: int = 300
    max_session_duration: int = 1800
    
    def __post_init__(self):
        if self.proxy_countries is None:
            self.proxy_countries = ["US"]


class BotOrchestrator:
    """
    Main orchestrator for the AdsPower + IPRoyal + Human Bot system.
    
    Architecture:
    ┌────────────────────────────┐
    │     Human Bot (Python)     │  ← logic, timing, behavior
    │  - session planning        │
    │  - dwell / scroll models   │
    │  - routing decisions       │
    │  - outcome scoring         │
    └───────────┬────────────────┘
                │
                ▼
    ┌────────────────────────────┐
    │        Playwright          │  ← precise browser control
    │  - input realism           │
    │  - async timing            │
    │  - network visibility      │
    └───────────┬────────────────┘
                │
                ▼
    ┌────────────────────────────┐
    │        AdsPower            │  ← browser + fingerprint host
    │  - profile isolation       │
    │  - OS / device persona     │
    │  - proxy binding           │
    └───────────┬────────────────┘
                │
                ▼
    ┌────────────────────────────┐
    │  IPRoyal Residential Proxy │  ← IP & ASN layer
    │  - geo diversity           │
    │  - ISP realism             │
    └────────────────────────────┘
    
    Usage:
        orchestrator = BotOrchestrator(config)
        
        # Create profiles with proxies
        profiles = orchestrator.create_profiles(count=3, country="US")
        
        # Run async tasks on all profiles
        await orchestrator.run_on_all_profiles(my_async_task)
    """
    
    def __init__(self, config: OrchestratorConfig):
        """
        Initialize the orchestrator.
        
        Args:
            config: OrchestratorConfig instance
        """
        self.config = config
        
        # Initialize AdsPower components
        self.adspower_client = AdsPowerClient(
            api_url=config.adspower_url,
            api_key=config.adspower_api_key
        )
        self.profile_manager = ProfileManager(self.adspower_client)
        self.browser_controller = BrowserController(
            self.adspower_client,
            self.profile_manager
        )
        
        # Initialize IPRoyal proxy manager
        self.proxy_manager = IPRoyalProxy(
            username=config.iproyal_username,
            password=config.iproyal_password,
            host=config.iproyal_host,
            port=config.iproyal_port,
            sticky_duration=config.sticky_session_duration
        )
        self.proxy_rotator = ProxyRotator(
            self.proxy_manager,
            countries=config.proxy_countries
        )
        
        # Initialize session manager
        self.session_manager = SessionManager(
            max_concurrent=config.max_concurrent_profiles
        )
        
        # Track active work
        self._active_profiles: Dict[str, Any] = {}
        
        logger.info("BotOrchestrator initialized (Async Playwright)")
    
    # ============== Profile Management ==============
    
    def create_profile(
        self,
        name: str,
        country: str = None,
        domain: str = None,
        with_proxy: bool = True
    ) -> Optional[Any]:
        """
        Create a single browser profile with proxy.
        
        Args:
            name: Profile name
            country: Proxy country code
            domain: Primary domain for profile
            with_proxy: Assign proxy to profile
            
        Returns:
            Profile instance or None
        """
        proxy_config = None
        
        if with_proxy:
            # Get proxy from IPRoyal
            country = country or random.choice(self.config.proxy_countries)
            proxy, session_id = self.proxy_manager.get_sticky_proxy(
                country=country,
                duration=self.config.sticky_session_duration
            )
            proxy_config = proxy
            
            logger.info(f"Assigned {country} proxy to profile '{name}'")
        
        # Create AdsPower profile
        profile = self.profile_manager.create_profile(
            name=name,
            proxy_host=proxy_config.host if proxy_config else None,
            proxy_port=proxy_config.port if proxy_config else None,
            proxy_user=proxy_config.username if proxy_config else None,
            proxy_pass=proxy_config.password if proxy_config else None,
            country=country,
            domain=domain
        )
        
        if profile:
            self._active_profiles[profile.id] = {
                "profile": profile,
                "proxy": proxy_config,
                "country": country
            }
        
        return profile
    
    def create_profiles(
        self,
        count: int,
        name_prefix: str = "bot_profile",
        countries: List[str] = None,
        domain: str = None
    ) -> List[Any]:
        """
        Create multiple browser profiles.
        
        Args:
            count: Number of profiles to create
            name_prefix: Prefix for profile names
            countries: Countries to rotate through
            domain: Primary domain for profiles
            
        Returns:
            List of created profiles
        """
        countries = countries or self.config.proxy_countries
        profiles = []
        
        for i in range(count):
            country = countries[i % len(countries)]
            name = f"{name_prefix}_{i + 1}"
            
            profile = self.create_profile(
                name=name,
                country=country,
                domain=domain
            )
            
            if profile:
                profiles.append(profile)
            
            time.sleep(0.5)
        
        logger.info(f"Created {len(profiles)}/{count} profiles")
        return profiles
    
    def get_or_create_profile(
        self,
        name: str,
        country: str = None,
        **kwargs
    ) -> Optional[Any]:
        """Find existing profile or create new one"""
        profile = self.profile_manager.find_or_create_profile(
            name=name,
            **kwargs
        )
        
        if profile and profile.id not in self._active_profiles:
            if country:
                proxy_config = self.proxy_rotator.get_proxy_for_profile(
                    profile.id,
                    country=country
                )
                self._active_profiles[profile.id] = {
                    "profile": profile,
                    "proxy": proxy_config,
                    "country": country
                }
        
        return profile
    
    # ============== Browser & Session Management ==============
    
    async def start_session(
        self,
        profile,
        headless: bool = False,
        open_url: str = None,
        session_duration: int = None
    ) -> Optional[BotSession]:
        """
        Start a browser session for a profile.
        
        Args:
            profile: Profile to start
            headless: Run in headless mode
            open_url: URL to open on start
            session_duration: Session duration (random within config if None)
            
        Returns:
            BotSession instance or None
        """
        # Start browser via AdsPower and get Playwright page
        page = await self.browser_controller.start_browser(
            profile=profile,
            headless=headless,
            open_url=open_url
        )
        
        if not page:
            logger.error(f"Failed to start browser for profile: {profile.name}")
            return None
        
        # Create session
        session_config = SessionConfig(
            min_duration=self.config.min_session_duration,
            max_duration=self.config.max_session_duration
        )
        
        session = self.session_manager.create_session(
            profile_id=profile.id,
            page=page,
            session_config=session_config
        )
        
        if session:
            duration = session_duration or random.randint(
                self.config.min_session_duration,
                self.config.max_session_duration
            )
            session.start(duration=duration)
            logger.success(f"Session started for profile: {profile.name}")
        
        return session
    
    async def stop_session(self, profile_id: str):
        """Stop a session and close browser"""
        session = self.session_manager.get_session(profile_id)
        if session:
            session.stop()
        
        await self.browser_controller.stop_browser(profile_id)
        self.session_manager.remove_session(profile_id)
    
    async def stop_all_sessions(self):
        """Stop all active sessions"""
        self.session_manager.stop_all()
        await self.browser_controller.stop_all_browsers()
    
    # ============== Task Execution ==============
    
    async def run_task(
        self,
        profile,
        task: Callable[[BotSession], Awaitable[Any]],
        headless: bool = False,
        open_url: str = None
    ) -> Optional[Any]:
        """
        Run an async task on a single profile.
        
        Args:
            profile: Profile to run task on
            task: Async callable that takes BotSession as argument
            headless: Run in headless mode
            open_url: URL to open first
            
        Returns:
            Task result or None
        """
        session = await self.start_session(
            profile=profile,
            headless=headless,
            open_url=open_url
        )
        
        if not session:
            return None
        
        try:
            result = await task(session)
            return result
            
        except Exception as e:
            logger.error(f"Task failed for {profile.name}: {e}")
            return None
            
        finally:
            await self.stop_session(profile.id)
    
    async def run_on_all_profiles(
        self,
        task: Callable[[BotSession], Awaitable[Any]],
        profiles: List = None,
        headless: bool = False,
        parallel: bool = False,
        max_concurrent: int = None
    ) -> Dict[str, Any]:
        """
        Run an async task on multiple profiles.
        
        Args:
            task: Async callable that takes BotSession as argument
            profiles: Profiles to run on (uses tracked profiles if None)
            headless: Run in headless mode
            parallel: Run profiles in parallel
            max_concurrent: Max parallel tasks
            
        Returns:
            Dict mapping profile_id to task result
        """
        if profiles is None:
            profiles = [p["profile"] for p in self._active_profiles.values()]
        
        results = {}
        
        if parallel:
            max_concurrent = max_concurrent or self.config.max_concurrent_profiles
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def run_with_semaphore(profile):
                async with semaphore:
                    return await self.run_task(profile, task, headless)
            
            tasks = [run_with_semaphore(p) for p in profiles]
            task_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for profile, result in zip(profiles, task_results):
                if isinstance(result, Exception):
                    logger.error(f"Task failed for {profile.name}: {result}")
                    results[profile.id] = None
                else:
                    results[profile.id] = result
        else:
            for profile in profiles:
                results[profile.id] = await self.run_task(
                    profile=profile,
                    task=task,
                    headless=headless
                )
                
                # Delay between profiles
                await asyncio.sleep(random.uniform(2, 5))
        
        return results
    
    # ============== Proxy Management ==============
    
    def rotate_proxy(self, profile_id: str, new_country: str = None) -> bool:
        """
        Rotate proxy for a profile.
        
        Args:
            profile_id: Profile to rotate proxy for
            new_country: New country for proxy
            
        Returns:
            True if successful
        """
        new_proxy = self.proxy_rotator.refresh_proxy_for_profile(profile_id)
        
        if not new_proxy:
            return False
        
        success = self.profile_manager.update_proxy(
            profile_id=profile_id,
            proxy_host=new_proxy.host,
            proxy_port=new_proxy.port,
            proxy_user=new_proxy.username,
            proxy_pass=new_proxy.password
        )
        
        if success and profile_id in self._active_profiles:
            self._active_profiles[profile_id]["proxy"] = new_proxy
        
        return success
    
    def test_profile_proxy(self, profile_id: str) -> bool:
        """Test if proxy is working for a profile"""
        if profile_id not in self._active_profiles:
            return False
        
        proxy_config = self._active_profiles[profile_id].get("proxy")
        if not proxy_config:
            return False
        
        return self.proxy_manager.test_proxy(proxy_config)
    
    # ============== Cleanup ==============
    
    async def cleanup(self):
        """Clean up all resources"""
        logger.info("Cleaning up orchestrator resources...")
        
        await self.stop_all_sessions()
        self.proxy_rotator.cleanup()
        self._active_profiles.clear()
        await self.browser_controller.cleanup()
        
        logger.info("Cleanup complete")
    
    def delete_all_profiles(self, confirm: bool = False):
        """Delete all tracked profiles (use with caution!)"""
        if not confirm:
            logger.warning("delete_all_profiles called without confirmation")
            return
        
        profile_ids = list(self._active_profiles.keys())
        
        if profile_ids:
            self.profile_manager.delete_profiles(profile_ids)
            self._active_profiles.clear()
            logger.warning(f"Deleted {len(profile_ids)} profiles")
    
    # ============== Status & Info ==============
    
    def get_status(self) -> Dict:
        """Get orchestrator status"""
        return {
            "adspower_connected": self.adspower_client.check_status(),
            "active_profiles": len(self._active_profiles),
            "active_sessions": len(self.session_manager.active_sessions),
            "running_browsers": self.browser_controller.get_running_count(),
            "proxy_sessions": len(self.proxy_rotator.get_all_sessions()),
            "session_stats": self.session_manager.get_aggregate_stats()
        }
    
    def print_status(self):
        """Print formatted status"""
        status = self.get_status()
        
        print("\n" + "=" * 50)
        print("BOT ORCHESTRATOR STATUS (Playwright)")
        print("=" * 50)
        print(f"AdsPower Connected: {'YES' if status['adspower_connected'] else 'NO'}")
        print(f"Active Profiles: {status['active_profiles']}")
        print(f"Active Sessions: {status['active_sessions']}")
        print(f"Running Browsers: {status['running_browsers']}")
        print(f"Proxy Sessions: {status['proxy_sessions']}")
        print("-" * 50)
        print("Session Statistics:")
        for key, value in status['session_stats'].items():
            print(f"  {key}: {value}")
        print("=" * 50 + "\n")
