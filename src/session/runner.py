"""
Bot Session Runner
Runs exactly ONE session with behavior engines and returns structured results.

This module executes a single automation session on a connected browser page.
It delegates actual behavior to behavior engines (timing, mouse, scroll, etc.).

All behavior engines derive randomness from the immutable SessionContext.

EVENT LOGGING
=============
The runner emits navigation events to the centralized EventLogger:
- NAVIGATION_START / NAVIGATION_COMPLETE / NAVIGATION_FAILED
- BEHAVIOR_EVENT (for significant interactions)
"""

import asyncio
import time
from typing import Optional, Callable, Awaitable, List, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from playwright.async_api import Page
from loguru import logger

from ..core.constants import (
    SessionSignal,
    MIN_REALISTIC_DURATION,
    MAX_REALISTIC_DURATION,
    SESSION_TIMEOUT_SECONDS,
)

if TYPE_CHECKING:
    from .context import SessionContext
    from ..events import EventLogger


class SessionStatus(Enum):
    """Status of a session run"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SessionResult:
    """
    Structured result from a session run.
    
    Contains all data needed for scoring and audit logging.
    """
    session_id: str
    profile_id: str
    status: SessionStatus
    success: bool
    duration_seconds: float
    signals: List[str] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_signal(self, signal: SessionSignal):
        """Add a signal to the result"""
        self.signals.append(signal.value)
    
    def has_signal(self, signal: SessionSignal) -> bool:
        """Check if result has a specific signal"""
        return signal.value in self.signals
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/storage"""
        return {
            "session_id": self.session_id,
            "profile_id": self.profile_id,
            "status": self.status.value,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 2),
            "signals": self.signals,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "metadata": self.metadata,
        }


# Type alias for session tasks
SessionTask = Callable[["BotSessionRunner"], Awaitable[Any]]


class BotSessionRunner:
    """
    Runs a single automation session.
    
    Responsibilities:
    - Execute exactly ONE session
    - Delegate behavior to behavior engines
    - Detect captchas and blocks
    - Return structured SessionResult
    
    The runner uses SessionContext for all session-wide state.
    All behavior engines derive randomness from context.seed.
    
    Usage:
        # With SessionContext (preferred)
        context = SessionContext.create(...)
        runner = BotSessionRunner(page, context=context)
        result = await runner.run(my_task_function)
        
        # Legacy mode (backward compatibility)
        runner = BotSessionRunner(page, session_id="...", profile_id="...")
    """
    
    def __init__(
        self,
        page: Page,
        context: Optional["SessionContext"] = None,
        # Legacy parameters for backward compatibility
        session_id: Optional[str] = None,
        profile_id: Optional[str] = None,
        behavior_seed: Optional[int] = None,
        timeout_seconds: int = SESSION_TIMEOUT_SECONDS,
        event_logger: Optional["EventLogger"] = None
    ):
        """
        Initialize session runner.
        
        Args:
            page: Playwright Page to control
            context: Immutable SessionContext (preferred)
            session_id: [Legacy] Unique session ID
            profile_id: [Legacy] AdsPower profile ID
            behavior_seed: [Legacy] Seed for deterministic behavior
            timeout_seconds: Maximum session duration
            event_logger: Optional EventLogger for navigation/behavior events
        """
        self.page = page
        self.timeout_seconds = timeout_seconds
        self._event_logger = event_logger
        
        # Use context if provided, otherwise create from legacy params
        if context is not None:
            self._context = context
            self.session_id = context.session_id
            self.profile_id = context.profile_id
            self.behavior_seed = context.seed
            self._os = context.os_type
            self._vps_id = context.vps_id
        else:
            # Legacy mode - create minimal context internally
            self._context = None
            self.session_id = session_id or f"legacy_{int(time.time())}"
            self.profile_id = profile_id or "unknown"
            self.behavior_seed = behavior_seed or int(time.time() * 1000) % (2**31)
            self._os = "unknown"
            self._vps_id = "unknown"
        
        # Status tracking
        self._status = SessionStatus.PENDING
        self._started_at: Optional[datetime] = None
        self._ended_at: Optional[datetime] = None
        self._signals: List[str] = []
        self._error: Optional[str] = None
        
        # Initialize behavior engines with session seed
        self._init_behavior_engines()
        
        logger.info(f"BotSessionRunner initialized (session: {self.session_id}, seed: {self.behavior_seed})")
    
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
    
    def _init_behavior_engines(self):
        """
        Initialize all behavior engines.
        
        If SessionContext is available, engines derive seeds from context.
        Otherwise, all engines share the same behavior_seed.
        """
        from ..behavior.timing import TimingDistributionEngine
        from ..behavior.mouse import MouseMovementEngine
        from ..behavior.interaction import InteractionSequencer
        from ..behavior.scroll import ScrollBehaviorEngine
        from ..behavior.focus import TabFocusSimulator
        
        if self._context is not None:
            # Preferred: derive from SessionContext
            self.timing = TimingDistributionEngine.from_context(self._context)
            self.mouse = MouseMovementEngine.from_context(self._context, timing_engine=self.timing)
            self.interaction = InteractionSequencer.from_context(self.page, self._context)
            self.scroll = ScrollBehaviorEngine.from_context(self.page, self._context)
            self.focus = TabFocusSimulator.from_context(self.page, self._context)
        else:
            # Legacy: all engines share same seed
            self.timing = TimingDistributionEngine(seed=self.behavior_seed)
            self.mouse = MouseMovementEngine(seed=self.behavior_seed, timing_engine=self.timing)
            self.interaction = InteractionSequencer(self.page, seed=self.behavior_seed)
            self.scroll = ScrollBehaviorEngine(self.page, seed=self.behavior_seed)
            self.focus = TabFocusSimulator(self.page, seed=self.behavior_seed)
    
    @property
    def context(self) -> Optional["SessionContext"]:
        """Get the session context (None if using legacy mode)"""
        return self._context
    
    async def run(
        self,
        task: SessionTask,
        **task_kwargs
    ) -> SessionResult:
        """
        Run a session task.
        
        Args:
            task: Async function that takes this runner as argument
            **task_kwargs: Additional kwargs passed to task
            
        Returns:
            SessionResult with outcome and signals
        """
        self._status = SessionStatus.RUNNING
        self._started_at = datetime.now(timezone.utc)
        
        try:
            # Run task with timeout
            await asyncio.wait_for(
                self._execute_task(task, **task_kwargs),
                timeout=self.timeout_seconds
            )
            
            self._status = SessionStatus.COMPLETED
            
        except asyncio.TimeoutError:
            logger.warning(f"Session {self.session_id} timed out after {self.timeout_seconds}s")
            self._status = SessionStatus.TIMEOUT
            self._error = f"Timeout after {self.timeout_seconds}s"
            self._signals.append(SessionSignal.TIMEOUT.value)
            
        except Exception as e:
            logger.error(f"Session {self.session_id} failed: {e}")
            self._status = SessionStatus.FAILED
            self._error = str(e)
            self._signals.append(SessionSignal.ERROR.value)
            self._signals.append(SessionSignal.ABNORMAL_TERMINATION.value)
        
        self._ended_at = datetime.now(timezone.utc)
        
        return self._build_result()
    
    async def _execute_task(self, task: SessionTask, **kwargs):
        """Execute the task and detect issues"""
        try:
            await task(self, **kwargs)
            
            # If we get here without errors, mark as successful
            self._signals.append(SessionSignal.SUCCESSFUL_COMPLETION.value)
            
            # Check duration for realism
            duration = self._get_duration()
            if MIN_REALISTIC_DURATION <= duration <= MAX_REALISTIC_DURATION:
                self._signals.append(SessionSignal.REALISTIC_DURATION.value)
            
            # Assume normal navigation unless detected otherwise
            if not self._has_suspicious_signals():
                self._signals.append(SessionSignal.NORMAL_NAVIGATION.value)
                
        except Exception as e:
            # Check if it's a detection-related error
            error_msg = str(e).lower()
            if "captcha" in error_msg or "challenge" in error_msg:
                self._signals.append(SessionSignal.CAPTCHA_DETECTED.value)
            elif "blocked" in error_msg or "denied" in error_msg or "forbidden" in error_msg:
                self._signals.append(SessionSignal.BLOCK_DETECTED.value)
            raise
    
    def _has_suspicious_signals(self) -> bool:
        """Check if session has any suspicious signals"""
        suspicious = {
            SessionSignal.CAPTCHA_DETECTED.value,
            SessionSignal.BLOCK_DETECTED.value,
        }
        return bool(set(self._signals) & suspicious)
    
    def _get_duration(self) -> float:
        """Get current session duration in seconds"""
        if not self._started_at:
            return 0
        end = self._ended_at or datetime.now(timezone.utc)
        return (end - self._started_at).total_seconds()
    
    def _build_result(self) -> SessionResult:
        """Build the final session result"""
        return SessionResult(
            session_id=self.session_id,
            profile_id=self.profile_id,
            status=self._status,
            success=self._status == SessionStatus.COMPLETED,
            duration_seconds=self._get_duration(),
            signals=self._signals.copy(),
            error=self._error,
            started_at=self._started_at,
            ended_at=self._ended_at,
            metadata={
                "behavior_seed": self.behavior_seed,
                "timeout_seconds": self.timeout_seconds,
            }
        )
    
    # ============== Convenience Methods for Tasks ==============
    # These wrap Playwright operations and will be enhanced with behavior engines
    
    async def navigate(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (domcontentloaded, networkidle, load)
            timeout: Timeout in milliseconds
            
        Returns:
            True if successful
        """
        start_time = time.time()
        
        # Log navigation start
        self._log_event(
            "log_navigation_start",
            session_id=self.session_id,
            profile_id=self.profile_id,
            os=self._os,
            vps_id=self._vps_id,
            url=url
        )
        
        try:
            await self.page.goto(url, wait_until=wait_until, timeout=timeout)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log navigation complete
            self._log_event(
                "log_navigation_complete",
                session_id=self.session_id,
                profile_id=self.profile_id,
                os=self._os,
                vps_id=self._vps_id,
                url=url,
                latency_ms=latency_ms
            )
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            
            # Log navigation failed
            self._log_event(
                "log_navigation_failed",
                session_id=self.session_id,
                profile_id=self.profile_id,
                os=self._os,
                vps_id=self._vps_id,
                url=url,
                error=str(e)
            )
            return False
    
    async def click(self, selector: str, timeout: int = 5000) -> bool:
        """
        Click an element.
        
        Note: Will be enhanced with InteractionSequencer when available.
        
        Args:
            selector: CSS selector
            timeout: Timeout in milliseconds
            
        Returns:
            True if successful
        """
        try:
            await self.page.click(selector, timeout=timeout)
            
            # Log behavior event
            self._log_event(
                "log_behavior_event",
                session_id=self.session_id,
                profile_id=self.profile_id,
                os=self._os,
                vps_id=self._vps_id,
                behavior_type="click",
                selector=selector
            )
            return True
        except Exception as e:
            logger.error(f"Click failed on {selector}: {e}")
            return False
    
    async def type_text(self, selector: str, text: str, delay: float = 100) -> bool:
        """
        Type text into an element.
        
        Note: Will be enhanced with TimingDistributionEngine when available.
        
        Args:
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes in milliseconds
            
        Returns:
            True if successful
        """
        try:
            await self.page.fill(selector, "")  # Clear first
            await self.page.type(selector, text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Type failed on {selector}: {e}")
            return False
    
    async def wait(self, seconds: float):
        """Wait for specified duration"""
        await asyncio.sleep(seconds)
    
    async def wait_for_selector(self, selector: str, timeout: int = 5000) -> bool:
        """Wait for an element to appear"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except Exception:
            return False
    
    async def screenshot(self, path: str, full_page: bool = False):
        """Take a screenshot"""
        await self.page.screenshot(path=path, full_page=full_page)
    
    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression"""
        return await self.page.evaluate(expression)
    
    def check_captcha_detected(self) -> bool:
        """Check if captcha has been detected in this session"""
        return SessionSignal.CAPTCHA_DETECTED.value in self._signals
    
    def check_block_detected(self) -> bool:
        """Check if block has been detected in this session"""
        return SessionSignal.BLOCK_DETECTED.value in self._signals
    
    def add_signal(self, signal: SessionSignal):
        """Manually add a signal to the session"""
        if signal.value not in self._signals:
            self._signals.append(signal.value)
    
    @property
    def status(self) -> SessionStatus:
        """Get current session status"""
        return self._status
    
    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time since session started"""
        return self._get_duration()
