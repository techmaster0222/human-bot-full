"""
Bot Session Manager (Playwright)
Manages complete browser sessions with lifecycle and state tracking.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger
from playwright.async_api import Page

from .actions import BotActions
from .human_behavior import BehaviorConfig, HumanBehavior


class SessionState(Enum):
    """Session states"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SessionStats:
    """Session statistics"""

    pages_visited: int = 0
    clicks_made: int = 0
    forms_filled: int = 0
    scrolls_made: int = 0
    time_active: float = 0
    errors_encountered: int = 0
    network_requests: int = 0

    def to_dict(self) -> dict:
        return {
            "pages_visited": self.pages_visited,
            "clicks_made": self.clicks_made,
            "forms_filled": self.forms_filled,
            "scrolls_made": self.scrolls_made,
            "time_active": round(self.time_active, 2),
            "errors_encountered": self.errors_encountered,
            "network_requests": self.network_requests,
        }


@dataclass
class SessionConfig:
    """Configuration for a bot session"""

    min_duration: int = 300  # 5 minutes minimum
    max_duration: int = 1800  # 30 minutes maximum
    break_chance: float = 0.1
    break_min_duration: int = 10
    break_max_duration: int = 60
    random_actions: bool = True
    random_action_chance: float = 0.05


class BotSession:
    """
    Manages a complete browser automation session with Playwright.

    Features:
    - Automatic session timing
    - Break simulation
    - Statistics tracking
    - Error handling
    - Task queue support
    - Network visibility
    """

    def __init__(
        self,
        profile_id: str,
        page: Page,
        behavior_config: BehaviorConfig = None,
        session_config: SessionConfig = None,
    ):
        """
        Initialize bot session.

        Args:
            profile_id: AdsPower profile ID
            page: Playwright Page
            behavior_config: Behavior configuration
            session_config: Session configuration
        """
        self.profile_id = profile_id
        self.page = page
        self.session_config = session_config or SessionConfig()

        # Initialize behavior and actions
        self.behavior = HumanBehavior(behavior_config)
        self.actions = BotActions(page, self.behavior)

        # Session state
        self.state = SessionState.IDLE
        self.started_at: datetime | None = None
        self.ended_at: datetime | None = None
        self.target_duration: int = 0

        # Statistics
        self.stats = SessionStats()

        # Task management
        self._tasks: list[Callable[[BotSession], Awaitable[Any]]] = []
        self._current_task_index: int = 0

        # Session metadata
        self.metadata: dict[str, Any] = {}

        logger.info(f"BotSession created for profile: {profile_id}")

    # ============== Session Lifecycle ==============

    def start(self, duration: int = None) -> bool:
        """
        Start the session.

        Args:
            duration: Session duration in seconds (random within config if None)

        Returns:
            True if started successfully
        """
        if self.state == SessionState.RUNNING:
            logger.warning("Session already running")
            return False

        # Set target duration
        if duration:
            self.target_duration = duration
        else:
            self.target_duration = random.randint(
                self.session_config.min_duration, self.session_config.max_duration
            )

        self.started_at = datetime.now()
        self.state = SessionState.RUNNING

        logger.info(f"Session started. Target duration: {self.target_duration}s")
        return True

    def stop(self):
        """Stop the session"""
        if self.state != SessionState.RUNNING:
            return

        self.ended_at = datetime.now()
        self.state = SessionState.COMPLETED
        self._calculate_final_stats()

        logger.info(f"Session stopped. Stats: {self.stats.to_dict()}")

    def pause(self):
        """Pause the session"""
        if self.state == SessionState.RUNNING:
            self.state = SessionState.PAUSED
            logger.info("Session paused")

    def resume(self):
        """Resume the session"""
        if self.state == SessionState.PAUSED:
            self.state = SessionState.RUNNING
            logger.info("Session resumed")

    @property
    def is_running(self) -> bool:
        return self.state == SessionState.RUNNING

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if not self.started_at:
            return 0

        end = self.ended_at or datetime.now()
        return (end - self.started_at).total_seconds()

    @property
    def remaining_time(self) -> float:
        """Get remaining session time"""
        return max(0, self.target_duration - self.elapsed_time)

    @property
    def should_end(self) -> bool:
        """Check if session should end"""
        return self.elapsed_time >= self.target_duration

    # ============== Task Management ==============

    def add_task(self, task: Callable[["BotSession"], Awaitable[Any]]):
        """
        Add an async task to the session queue.

        Task should be an async callable that takes BotSession as argument.
        """
        self._tasks.append(task)

    def add_tasks(self, tasks: list[Callable[["BotSession"], Awaitable[Any]]]):
        """Add multiple async tasks"""
        self._tasks.extend(tasks)

    async def run_tasks(self) -> bool:
        """
        Run all queued tasks.

        Returns:
            True if all tasks completed successfully
        """
        if not self._tasks:
            logger.warning("No tasks to run")
            return True

        if not self.is_running:
            self.start()

        success = True

        for i, task in enumerate(self._tasks):
            if not self.is_running or self.should_end:
                logger.info("Session ending, stopping tasks")
                break

            self._current_task_index = i

            try:
                logger.info(f"Running task {i + 1}/{len(self._tasks)}")

                # Run the async task
                await task(self)

                # Maybe take a break between tasks
                await self._maybe_take_break()

                # Maybe do random action
                await self._maybe_random_action()

            except Exception as e:
                logger.error(f"Task {i + 1} failed: {e}")
                self.stats.errors_encountered += 1
                success = False

        self.stop()
        return success

    async def run_single_task(self, task: Callable[["BotSession"], Awaitable[Any]]) -> bool:
        """Run a single async task immediately"""
        if not self.is_running:
            self.start()

        try:
            await task(self)
            return True
        except Exception as e:
            logger.error(f"Task failed: {e}")
            self.stats.errors_encountered += 1
            return False

    # ============== Convenience Methods (Tracked) ==============

    async def visit_page(self, url: str, wait_until: str = "domcontentloaded") -> bool:
        """Visit a page (tracked)"""
        result = await self.actions.navigate_to(url, wait_until=wait_until)
        if result:
            self.stats.pages_visited += 1
        return result is not None

    async def click_element(self, selector: str, natural: bool = True) -> bool:
        """Click an element (tracked)"""
        result = await self.actions.click(selector, natural_movement=natural)
        if result:
            self.stats.clicks_made += 1
        return result

    async def type_in_field(
        self, selector: str, text: str, clear: bool = True, submit: bool = False
    ) -> bool:
        """Type in a field (tracked)"""
        result = await self.actions.type_text(selector, text, clear_first=clear, submit=submit)
        if result:
            self.stats.forms_filled += 1
        return result

    async def scroll(self, direction: str = "down", amount: int = None) -> bool:
        """Scroll the page (tracked)"""
        if direction == "down":
            result = await self.actions.scroll_down(amount)
        else:
            result = await self.actions.scroll_up(amount)

        if result:
            self.stats.scrolls_made += 1
        return result

    async def wait(self, seconds: float = None):
        """Wait/pause for specified time or random duration"""
        duration = seconds or self.behavior.random_medium_pause()
        await asyncio.sleep(duration)

    async def wait_random(self, min_seconds: float = 1, max_seconds: float = 5):
        """Wait for random duration within range"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))

    async def simulate_reading(self, content_length: int = 1000):
        """Simulate reading page content"""
        await self.actions.simulate_reading(content_length)

    # ============== Network Visibility ==============

    def get_network_requests(self) -> list[dict]:
        """Get all tracked network requests"""
        return self.actions.get_network_requests()

    def get_requests_by_type(self, resource_type: str) -> list[dict]:
        """Get network requests filtered by type (xhr, fetch, document, etc.)"""
        return [
            r
            for r in self.actions.get_network_requests()
            if r.get("resource_type") == resource_type
        ]

    async def wait_for_request(self, url_pattern: str, timeout: int = 30000):
        """Wait for a specific network request"""
        return await self.page.wait_for_request(url_pattern, timeout=timeout)

    async def wait_for_response(self, url_pattern: str, timeout: int = 30000):
        """Wait for a specific network response"""
        return await self.page.wait_for_response(url_pattern, timeout=timeout)

    # ============== Routing Decisions ==============

    async def get_page_content(self) -> str:
        """Get current page HTML content"""
        return await self.page.content()

    async def get_visible_text(self) -> str:
        """Get visible text on the page"""
        return await self.page.evaluate("document.body.innerText")

    async def check_element_exists(self, selector: str) -> bool:
        """Check if an element exists"""
        count = await self.actions.get_element_count(selector)
        return count > 0

    async def get_all_links(self) -> list[str]:
        """Get all links on the page"""
        return await self.page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                       .map(a => a.href)
                       .filter(href => href.startsWith('http'))
        """)

    # ============== Internal Methods ==============

    async def _maybe_take_break(self):
        """Maybe take a break based on configuration"""
        if not self.session_config.break_chance:
            return

        if random.random() < self.session_config.break_chance:
            break_duration = random.randint(
                self.session_config.break_min_duration, self.session_config.break_max_duration
            )

            logger.info(f"Taking a break for {break_duration}s")
            await asyncio.sleep(break_duration)

    async def _maybe_random_action(self):
        """Maybe perform a random action"""
        if not self.session_config.random_actions:
            return

        if random.random() < self.session_config.random_action_chance:
            action = random.choice(["scroll", "mouse", "idle"])

            if action == "scroll":
                await self.scroll(random.choice(["up", "down"]))
            elif action == "mouse":
                await self.actions.random_mouse_movement()
            else:
                await self.actions.idle_behavior(random.uniform(1, 3))

    def _calculate_final_stats(self):
        """Calculate final session statistics"""
        self.stats.time_active = self.elapsed_time
        self.stats.network_requests = len(self.actions.get_network_requests())

    def get_summary(self) -> dict:
        """Get session summary"""
        return {
            "profile_id": self.profile_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "elapsed_time": round(self.elapsed_time, 2),
            "target_duration": self.target_duration,
            "stats": self.stats.to_dict(),
            "metadata": self.metadata,
        }


class SessionManager:
    """
    Manages multiple bot sessions.

    Provides:
    - Concurrent session management
    - Session lifecycle tracking
    - Aggregate statistics
    """

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize session manager.

        Args:
            max_concurrent: Maximum concurrent sessions
        """
        self.max_concurrent = max_concurrent
        self._sessions: dict[str, BotSession] = {}

        logger.info(f"SessionManager initialized (max concurrent: {max_concurrent})")

    def create_session(
        self,
        profile_id: str,
        page: Page,
        behavior_config: BehaviorConfig = None,
        session_config: SessionConfig = None,
    ) -> BotSession | None:
        """Create a new session"""
        if len(self.active_sessions) >= self.max_concurrent:
            logger.warning("Maximum concurrent sessions reached")
            return None

        if profile_id in self._sessions:
            logger.warning(f"Session already exists for profile: {profile_id}")
            return self._sessions[profile_id]

        session = BotSession(
            profile_id=profile_id,
            page=page,
            behavior_config=behavior_config,
            session_config=session_config,
        )

        self._sessions[profile_id] = session
        return session

    def get_session(self, profile_id: str) -> BotSession | None:
        """Get session by profile ID"""
        return self._sessions.get(profile_id)

    def remove_session(self, profile_id: str):
        """Remove a session"""
        if profile_id in self._sessions:
            session = self._sessions[profile_id]
            if session.is_running:
                session.stop()
            del self._sessions[profile_id]

    @property
    def active_sessions(self) -> list[BotSession]:
        """Get all active sessions"""
        return [s for s in self._sessions.values() if s.is_running]

    @property
    def all_sessions(self) -> list[BotSession]:
        """Get all sessions"""
        return list(self._sessions.values())

    def stop_all(self):
        """Stop all sessions"""
        for session in self.active_sessions:
            session.stop()

    def get_aggregate_stats(self) -> dict:
        """Get aggregate statistics across all sessions"""
        total_stats = {
            "total_sessions": len(self._sessions),
            "active_sessions": len(self.active_sessions),
            "total_pages_visited": 0,
            "total_clicks": 0,
            "total_forms_filled": 0,
            "total_time_active": 0,
            "total_errors": 0,
            "total_network_requests": 0,
        }

        for session in self._sessions.values():
            total_stats["total_pages_visited"] += session.stats.pages_visited
            total_stats["total_clicks"] += session.stats.clicks_made
            total_stats["total_forms_filled"] += session.stats.forms_filled
            total_stats["total_time_active"] += session.stats.time_active
            total_stats["total_errors"] += session.stats.errors_encountered
            total_stats["total_network_requests"] += session.stats.network_requests

        return total_stats
