"""
Session Orchestrator
Coordinates running sessions in waves with proper lifecycle management.

This is the main entry point for running automation at scale.
It coordinates all components: profiles, browsers, sessions, and scoring.

PROFILE OWNERSHIP
=================
- This orchestrator ONLY manages profiles it creates via ProfileFactory
- Existing/legacy AdsPower profiles are IGNORED
- Each session gets a fresh disposable profile
- Profile reuse is controlled by reputation policy, not by finding existing profiles

EVENT LOGGING
=============
The orchestrator emits events to the centralized EventLogger:
- WAVE_STARTED / WAVE_COMPLETED
- SESSION_CREATED / SESSION_STARTED / SESSION_COMPLETED / SESSION_FAILED
- PROFILE_CREATED / PROFILE_STARTED / PROFILE_STOPPED / PROFILE_DESTROYED
- PROXY_ASSIGNED / PROXY_RESULT
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from ..adspower import AdsPowerClient, AdsPowerController, ProfileFactory
from ..browser import BrowserConnector
from ..core.config import Config, get_os_name
from ..core.constants import (
    PROFILE_STARTUP_DELAY_MAX,
    PROFILE_STARTUP_DELAY_MIN,
)
from ..proxy import ProxyCredentials, ProxySessionManager, ProxyStatsManager
from .context import SessionContext
from .runner import BotSessionRunner, SessionResult, SessionTask

# Event logging (optional - gracefully handles if not available)
try:
    from ..events import EventLogger

    HAS_EVENT_LOGGER = True
except ImportError:
    HAS_EVENT_LOGGER = False
    EventLogger = None

# Proxy stats (optional - gracefully handles if not available)
try:
    from ..proxy import ProxyStatsManager

    HAS_PROXY_STATS = True
except ImportError:
    HAS_PROXY_STATS = False
    ProxyStatsManager = None


@dataclass
class OrchestratorStats:
    """Statistics for an orchestrator run"""

    sessions_started: int = 0
    sessions_completed: int = 0
    sessions_failed: int = 0
    profiles_created: int = 0
    profiles_destroyed: int = 0
    profiles_reused: int = 0
    total_duration_seconds: float = 0

    def to_dict(self) -> dict:
        return {
            "sessions_started": self.sessions_started,
            "sessions_completed": self.sessions_completed,
            "sessions_failed": self.sessions_failed,
            "profiles_created": self.profiles_created,
            "profiles_destroyed": self.profiles_destroyed,
            "profiles_reused": self.profiles_reused,
            "total_duration_seconds": round(self.total_duration_seconds, 2),
        }


@dataclass
class WaveResult:
    """Result of running a wave of sessions"""

    wave_number: int
    session_results: list[SessionResult]
    started_at: datetime
    ended_at: datetime

    @property
    def duration_seconds(self) -> float:
        return (self.ended_at - self.started_at).total_seconds()

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.session_results if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.session_results if not r.success)


class SessionOrchestrator:
    """
    Orchestrates running automation sessions at scale.

    Responsibilities:
    - Create profiles via ProfileFactory
    - Start browsers via AdsPowerController
    - Connect via BrowserConnector
    - Run tasks via BotSessionRunner
    - Score and log results
    - Apply reuse policy
    - Guarantee clean teardown

    Usage:
        orchestrator = SessionOrchestrator(config)

        # Run a wave of sessions
        results = await orchestrator.run_wave(my_task, count=10)

        # Or run multiple waves
        results = await orchestrator.run_waves(my_task, waves=3, sessions_per_wave=10)

        # Always cleanup
        await orchestrator.cleanup()
    """

    def __init__(
        self,
        config: Config,
        vps_id: str | None = None,
        max_profiles_per_wave: int | None = None,
        max_total_profiles: int | None = None,
        event_logger: Optional["EventLogger"] = None,
        proxy_stats_manager: Optional["ProxyStatsManager"] = None,
    ):
        """
        Initialize orchestrator.

        Args:
            config: Application configuration
            vps_id: VPS identifier for logging (auto-detected if None)
            max_profiles_per_wave: Max concurrent profiles per wave
            max_total_profiles: Max total profiles to create
            event_logger: Optional EventLogger for centralized event tracking
            proxy_stats_manager: Optional ProxyStatsManager for proxy performance tracking
        """
        self.config = config
        self.vps_id = vps_id or config.orchestrator.vps_id
        self.max_profiles_per_wave = (
            max_profiles_per_wave or config.orchestrator.max_profiles_per_wave
        )
        self.max_total_profiles = max_total_profiles or config.orchestrator.max_total_profiles
        self.os_name = get_os_name()

        # Event logger (optional)
        self._event_logger = event_logger
        if HAS_EVENT_LOGGER and self._event_logger is None:
            # Try to get singleton instance
            try:
                self._event_logger = EventLogger.get_instance()
            except Exception:
                pass

        # Proxy stats manager (optional)
        self._proxy_stats = proxy_stats_manager
        if HAS_PROXY_STATS and self._proxy_stats is None:
            # Create a new instance
            try:
                self._proxy_stats = ProxyStatsManager()
            except Exception:
                pass

        # Initialize components
        self._adspower_client = AdsPowerClient(
            api_url=config.adspower.api_url, api_key=config.adspower.api_key
        )

        self._proxy_credentials = ProxyCredentials(
            username=config.proxy.username,
            password=config.proxy.password,
            host=config.proxy.host,
            port=config.proxy.port,
        )

        self._proxy_manager = ProxySessionManager(
            credentials=self._proxy_credentials, sticky_duration=config.proxy.sticky_duration
        )

        self._profile_factory = ProfileFactory(
            adspower_client=self._adspower_client, proxy_manager=self._proxy_manager
        )

        self._controller = AdsPowerController(self._adspower_client)
        self._connector = BrowserConnector()

        # Statistics
        self._stats = OrchestratorStats()
        self._wave_results: list[WaveResult] = []
        self._current_wave = 0

        # Countries to rotate through
        self._countries = config.proxy.countries or ["US"]
        self._country_index = 0

        logger.info(f"SessionOrchestrator initialized (vps: {self.vps_id}, os: {self.os_name})")

    def _log_event(self, method_name: str, **kwargs):
        """Helper to log events if EventLogger is available."""
        if self._event_logger is None:
            return
        try:
            method = getattr(self._event_logger, method_name, None)
            if method:
                method(**kwargs)
        except Exception as e:
            logger.debug(f"Event logging failed: {e}")

    def _record_proxy_result(
        self,
        proxy_id: str,
        country: str,
        success: bool,
        latency_ms: int | None = None,
        error: str | None = None,
        session_id: str | None = None,
    ):
        """Helper to record proxy results if ProxyStatsManager is available."""
        if self._proxy_stats is None:
            return
        try:
            if success:
                self._proxy_stats.record_success(
                    proxy_id=proxy_id, country=country, latency_ms=latency_ms, session_id=session_id
                )
            else:
                self._proxy_stats.record_failure(
                    proxy_id=proxy_id, country=country, error=error, session_id=session_id
                )
        except Exception as e:
            logger.debug(f"Proxy stats recording failed: {e}")

    def _get_next_country(self) -> str:
        """Get next country in rotation"""
        country = self._countries[self._country_index]
        self._country_index = (self._country_index + 1) % len(self._countries)
        return country

    async def run_wave(
        self, task: SessionTask, count: int, countries: list[str] | None = None
    ) -> WaveResult:
        """
        Run a wave of sessions.

        Each session:
        1. Creates a new profile with proxy
        2. Starts the browser
        3. Connects via CDP
        4. Runs the task
        5. Disconnects and stops browser
        6. Destroys profile (unless reuse allowed)

        Args:
            task: Async function to run on each session
            count: Number of sessions in this wave
            countries: Countries for profiles (rotates through default if None)

        Returns:
            WaveResult with all session outcomes
        """
        self._current_wave += 1
        wave_number = self._current_wave
        started_at = datetime.now(timezone.utc)

        logger.info(f"Starting wave {wave_number} with {count} sessions")

        # Log wave started event
        self._log_event(
            "log_wave_started",
            wave_number=wave_number,
            session_count=count,
            os=self.os_name,
            vps_id=self.vps_id,
        )

        # Limit to max per wave
        count = min(count, self.max_profiles_per_wave)

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_profiles_per_wave)

        # Create tasks for all sessions
        tasks = []
        for i in range(count):
            country = countries[i % len(countries)] if countries else self._get_next_country()
            tasks.append(self._run_single_session(task, country, semaphore, wave_number, i + 1))

        # Run all sessions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        session_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Session exception: {result}")
                # Create error result
                session_results.append(
                    SessionResult(
                        session_id="error",
                        profile_id="error",
                        status="failed",
                        success=False,
                        duration_seconds=0,
                        error=str(result),
                    )
                )
                self._stats.sessions_failed += 1
            elif isinstance(result, SessionResult):
                session_results.append(result)
                if result.success:
                    self._stats.sessions_completed += 1
                else:
                    self._stats.sessions_failed += 1

        ended_at = datetime.now(timezone.utc)

        wave_result = WaveResult(
            wave_number=wave_number,
            session_results=session_results,
            started_at=started_at,
            ended_at=ended_at,
        )

        self._wave_results.append(wave_result)
        self._stats.total_duration_seconds += wave_result.duration_seconds

        logger.info(
            f"Wave {wave_number} completed: {wave_result.success_count} success, "
            f"{wave_result.failure_count} failed in {wave_result.duration_seconds:.1f}s"
        )

        # Log wave completed event
        self._log_event(
            "log_wave_completed",
            wave_number=wave_number,
            success_count=wave_result.success_count,
            failure_count=wave_result.failure_count,
            duration_seconds=wave_result.duration_seconds,
            os=self.os_name,
            vps_id=self.vps_id,
        )

        return wave_result

    async def _run_single_session(
        self,
        task: SessionTask,
        country: str,
        semaphore: asyncio.Semaphore,
        wave_number: int,
        session_number: int,
    ) -> SessionResult:
        """
        Run a single session with full lifecycle.

        Creates a fresh profile (never reuses existing profiles),
        builds an immutable SessionContext, and runs the task.
        """

        async with semaphore:
            profile_info = None
            context = None
            proxy_id = None

            try:
                # Stagger profile startup
                if session_number > 1:
                    delay = random.uniform(PROFILE_STARTUP_DELAY_MIN, PROFILE_STARTUP_DELAY_MAX)
                    await asyncio.sleep(delay)

                # Step 1: Create NEW profile with proxy (never reuse existing)
                profile_info = self._profile_factory.create_profile(
                    country=country,
                    name_prefix=f"wave{wave_number}",
                    sticky_duration=self.config.proxy.sticky_duration,
                )

                if not profile_info:
                    raise Exception("Failed to create profile")

                self._stats.profiles_created += 1
                self._stats.sessions_started += 1
                proxy_id = profile_info.session_id  # Proxy session ID

                # Log session created event
                self._log_event(
                    "log_session_created",
                    session_id=profile_info.session_id,
                    profile_id=profile_info.profile_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    proxy_id=proxy_id,
                    country=country,
                    wave_number=wave_number,
                )

                # Log profile created event
                self._log_event(
                    "log_profile_created",
                    session_id=profile_info.session_id,
                    profile_id=profile_info.profile_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    profile_name=profile_info.profile_name,
                    country=country,
                )

                # Log proxy assigned event
                self._log_event(
                    "log_proxy_assigned",
                    session_id=profile_info.session_id,
                    profile_id=profile_info.profile_id,
                    proxy_id=proxy_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    country=country,
                )

                # Step 2: Create immutable SessionContext
                context = SessionContext.create(
                    session_id=profile_info.session_id,
                    profile_id=profile_info.profile_id,
                    proxy_session=profile_info.proxy_session.proxy_username,
                    os_type=self.os_name,
                    vps_id=self.vps_id,
                    country=country,
                )

                # Step 3: Start browser
                cdp_endpoint = await self._controller.start_profile(profile_info.profile_id)

                if not cdp_endpoint:
                    raise Exception("Failed to start browser")

                # Log profile started event
                self._log_event(
                    "log_profile_started",
                    session_id=context.session_id,
                    profile_id=context.profile_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    cdp_url=cdp_endpoint.cdp_url,
                )

                # Step 4: Connect via CDP
                page = await self._connector.connect(cdp_endpoint.cdp_url, profile_info.profile_id)

                if not page:
                    raise Exception("Failed to connect to browser")

                # Log browser connected event
                self._log_event(
                    "log_browser_connected",
                    session_id=context.session_id,
                    profile_id=context.profile_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    cdp_url=cdp_endpoint.cdp_url,
                )

                # Log session started event
                self._log_event(
                    "log_session_started",
                    session_id=context.session_id,
                    profile_id=context.profile_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    proxy_id=proxy_id,
                )

                # Step 5: Run task with SessionContext
                runner = BotSessionRunner(
                    page=page,
                    context=context,  # All behavior engines derive from context.seed
                    event_logger=self._event_logger,
                )

                result = await runner.run(task)

                # Add metadata from context
                result.metadata["country"] = context.country
                result.metadata["wave_number"] = wave_number
                result.metadata["os"] = context.os_type
                result.metadata["vps_id"] = context.vps_id
                result.metadata["seed"] = context.seed

                # Log session completion event
                if result.success:
                    self._log_event(
                        "log_session_completed",
                        session_id=context.session_id,
                        profile_id=context.profile_id,
                        os=self.os_name,
                        vps_id=self.vps_id,
                        proxy_id=proxy_id,
                        duration_seconds=result.duration_seconds,
                        signals=result.signals,
                    )
                    # Log proxy result (success)
                    self._log_event(
                        "log_proxy_result",
                        session_id=context.session_id,
                        profile_id=context.profile_id,
                        proxy_id=proxy_id,
                        os=self.os_name,
                        vps_id=self.vps_id,
                        success=True,
                    )
                    # Record proxy stats
                    latency_ms = (
                        int(result.duration_seconds * 1000) if result.duration_seconds else None
                    )
                    self._record_proxy_result(
                        proxy_id=proxy_id,
                        country=context.country,
                        success=True,
                        latency_ms=latency_ms,
                        session_id=context.session_id,
                    )
                else:
                    self._log_event(
                        "log_session_failed",
                        session_id=context.session_id,
                        profile_id=context.profile_id,
                        os=self.os_name,
                        vps_id=self.vps_id,
                        proxy_id=proxy_id,
                        error=result.error or "Unknown error",
                    )
                    # Log proxy result (failure)
                    self._log_event(
                        "log_proxy_result",
                        session_id=context.session_id,
                        profile_id=context.profile_id,
                        proxy_id=proxy_id,
                        os=self.os_name,
                        vps_id=self.vps_id,
                        success=False,
                        error=result.error,
                    )
                    # Record proxy stats
                    self._record_proxy_result(
                        proxy_id=proxy_id,
                        country=context.country,
                        success=False,
                        error=result.error,
                        session_id=context.session_id,
                    )

                return result

            except Exception as e:
                logger.error(f"Session failed: {e}")
                from .runner import SessionStatus

                session_id = (
                    context.session_id
                    if context
                    else (profile_info.session_id if profile_info else "error")
                )
                profile_id = (
                    context.profile_id
                    if context
                    else (profile_info.profile_id if profile_info else "error")
                )

                # Log session failed event
                self._log_event(
                    "log_session_failed",
                    session_id=session_id,
                    profile_id=profile_id,
                    os=self.os_name,
                    vps_id=self.vps_id,
                    proxy_id=proxy_id,
                    error=str(e),
                )

                # Log proxy result (failure)
                if proxy_id:
                    self._log_event(
                        "log_proxy_result",
                        session_id=session_id,
                        profile_id=profile_id,
                        proxy_id=proxy_id,
                        os=self.os_name,
                        vps_id=self.vps_id,
                        success=False,
                        error=str(e),
                    )
                    # Record proxy stats
                    self._record_proxy_result(
                        proxy_id=proxy_id,
                        country=country,
                        success=False,
                        error=str(e),
                        session_id=session_id,
                    )

                return SessionResult(
                    session_id=session_id,
                    profile_id=profile_id,
                    status=SessionStatus.FAILED,
                    success=False,
                    duration_seconds=0,
                    error=str(e),
                )

            finally:
                # Step 6 & 7: Cleanup (always destroy profiles we created)
                if profile_info:
                    session_id = context.session_id if context else profile_info.session_id
                    profile_id_val = context.profile_id if context else profile_info.profile_id

                    # Disconnect from browser
                    await self._connector.disconnect(profile_info.profile_id)

                    # Log browser disconnected
                    self._log_event(
                        "log_browser_disconnected",
                        session_id=session_id,
                        profile_id=profile_id_val,
                        os=self.os_name,
                        vps_id=self.vps_id,
                    )

                    # Stop browser
                    await self._controller.stop_profile(profile_info.profile_id)

                    # Log profile stopped
                    self._log_event(
                        "log_profile_stopped",
                        session_id=session_id,
                        profile_id=profile_id_val,
                        os=self.os_name,
                        vps_id=self.vps_id,
                    )

                    # Destroy profile (disposable by default)
                    # Reuse policy can be applied before this in production
                    self._profile_factory.destroy_profile(profile_info.profile_id)
                    self._stats.profiles_destroyed += 1

                    # Log profile destroyed
                    self._log_event(
                        "log_profile_destroyed",
                        session_id=session_id,
                        profile_id=profile_id_val,
                        os=self.os_name,
                        vps_id=self.vps_id,
                    )

    async def run_waves(
        self,
        task: SessionTask,
        waves: int,
        sessions_per_wave: int,
        delay_between_waves: float = 5.0,
    ) -> list[WaveResult]:
        """
        Run multiple waves of sessions.

        Args:
            task: Async function to run on each session
            waves: Number of waves to run
            sessions_per_wave: Sessions per wave
            delay_between_waves: Delay between waves in seconds

        Returns:
            List of WaveResults
        """
        results = []

        for i in range(waves):
            result = await self.run_wave(task, sessions_per_wave)
            results.append(result)

            if i < waves - 1:  # Don't delay after last wave
                await asyncio.sleep(delay_between_waves)

        return results

    async def check_adspower_status(self) -> bool:
        """Check if AdsPower is running"""
        return self._adspower_client.check_status()

    def get_stats(self) -> OrchestratorStats:
        """Get current statistics"""
        return self._stats

    def get_wave_results(self) -> list[WaveResult]:
        """Get all wave results"""
        return self._wave_results.copy()

    async def cleanup(self):
        """
        Clean up all resources.

        MUST be called when done to ensure:
        - All browsers are stopped
        - All profiles are cleaned up
        - All connections are closed
        """
        logger.info("Cleaning up SessionOrchestrator...")

        # Stop all browsers
        await self._controller.stop_all()

        # Disconnect all
        await self._connector.cleanup()

        # Destroy remaining profiles
        remaining = self._profile_factory.destroy_all_profiles()
        if remaining > 0:
            self._stats.profiles_destroyed += remaining

        # Clean up proxy sessions
        self._proxy_manager.cleanup()

        # Clean up controller
        await self._controller.cleanup()

        logger.info(f"Cleanup complete. Final stats: {self._stats.to_dict()}")

    def print_summary(self):
        """Print a summary of the orchestrator run"""
        stats = self._stats.to_dict()

        print("\n" + "=" * 60)
        print("SESSION ORCHESTRATOR SUMMARY")
        print("=" * 60)
        print(f"VPS ID: {self.vps_id}")
        print(f"OS: {self.os_name}")
        print("-" * 60)
        print(f"Sessions Started:   {stats['sessions_started']}")
        print(f"Sessions Completed: {stats['sessions_completed']}")
        print(f"Sessions Failed:    {stats['sessions_failed']}")
        print("-" * 60)
        print(f"Profiles Created:   {stats['profiles_created']}")
        print(f"Profiles Destroyed: {stats['profiles_destroyed']}")
        print(f"Profiles Reused:    {stats['profiles_reused']}")
        print("-" * 60)
        print(f"Total Duration:     {stats['total_duration_seconds']:.2f}s")
        print("=" * 60 + "\n")
