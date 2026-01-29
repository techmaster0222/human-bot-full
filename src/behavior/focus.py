"""
Tab Focus Simulator
Simulates natural tab switching and window blur/focus behavior.

Humans occasionally:
- Switch to other tabs
- Check other windows
- Get distracted briefly
- Have the window lose focus

This module simulates these behaviors to appear more human-like.
Never interrupts critical actions like form submission.

SEED DERIVATION: All randomness derived from SessionContext.
"""

import asyncio
from typing import Optional, List, Set, TYPE_CHECKING
from dataclasses import dataclass
from playwright.async_api import Page
from loguru import logger

from .timing import TimingDistributionEngine
from ..core.constants import (
    TAB_SWITCH_CHANCE,
    TAB_IDLE_MIN,
    TAB_IDLE_MAX,
    WINDOW_BLUR_CHANCE,
)

if TYPE_CHECKING:
    from ..session.context import SessionContext


@dataclass
class FocusConfig:
    """Configuration for focus simulation"""
    tab_switch_chance: float = TAB_SWITCH_CHANCE  # 5% per major action
    window_blur_chance: float = WINDOW_BLUR_CHANCE  # 3%
    idle_min: float = TAB_IDLE_MIN  # 2 seconds
    idle_max: float = TAB_IDLE_MAX  # 10 seconds
    enabled: bool = True


@dataclass
class FocusEvent:
    """Record of a focus event"""
    event_type: str  # "tab_switch", "blur", "focus", "idle"
    duration: float
    timestamp: float


class TabFocusSimulator:
    """
    Simulates natural tab/window focus behavior.
    
    Key behaviors:
    - 5% chance of "tab switch" per major action
    - 3% chance of window blur event
    - Short idle pauses (2-10 seconds)
    - Never interrupts critical actions
    
    Usage:
        simulator = TabFocusSimulator(page, seed=12345)
        
        # Maybe switch tab (5% chance)
        switched = await simulator.maybe_switch_tab()
        
        # Simulate distraction
        await simulator.simulate_distraction()
        
        # Mark critical section
        async with simulator.critical_section():
            await submit_form()
    """
    
    def __init__(
        self,
        page: Page,
        seed: Optional[int] = None,
        config: Optional[FocusConfig] = None
    ):
        """
        Initialize focus simulator.
        
        Args:
            page: Playwright page
            seed: Random seed for reproducibility
            config: Focus configuration
        """
        self.page = page
        self.config = config or FocusConfig()
        self.timing = TimingDistributionEngine(seed=seed)
        
        # Track state
        self._in_critical_section = False
        self._events: List[FocusEvent] = []
        self._total_idle_time = 0
        
        logger.debug(f"TabFocusSimulator initialized (seed: {self.timing.seed})")
    
    @classmethod
    def from_context(cls, page: Page, context: "SessionContext", config: Optional[FocusConfig] = None) -> "TabFocusSimulator":
        """
        Create from SessionContext with deterministic seed.
        
        Args:
            page: Playwright page
            context: Immutable SessionContext
            config: Optional focus configuration
            
        Returns:
            TabFocusSimulator with seed derived from context
        """
        seed = context.derive_subseed("focus")
        return cls(page=page, seed=seed, config=config)
    
    async def maybe_switch_tab(self) -> bool:
        """
        Maybe simulate a tab switch (5% chance by default).
        
        Does nothing if in critical section.
        
        Returns:
            True if tab switch was simulated
        """
        if not self.config.enabled:
            return False
        
        if self._in_critical_section:
            logger.debug("Skipping tab switch - in critical section")
            return False
        
        if self.timing._rng.random() >= self.config.tab_switch_chance:
            return False
        
        # Simulate tab switch
        idle_duration = self.timing._rng.uniform(
            self.config.idle_min,
            self.config.idle_max
        )
        
        logger.debug(f"Simulating tab switch for {idle_duration:.1f}s")
        
        # Trigger blur event
        await self._trigger_blur()
        
        # Idle
        await asyncio.sleep(idle_duration)
        
        # Trigger focus event
        await self._trigger_focus()
        
        # Record event
        self._events.append(FocusEvent(
            event_type="tab_switch",
            duration=idle_duration,
            timestamp=self.timing._rng.random()  # Placeholder timestamp
        ))
        self._total_idle_time += idle_duration
        
        return True
    
    async def maybe_blur(self) -> bool:
        """
        Maybe trigger a window blur (3% chance by default).
        
        Simulates user clicking outside browser window briefly.
        
        Returns:
            True if blur was simulated
        """
        if not self.config.enabled:
            return False
        
        if self._in_critical_section:
            return False
        
        if self.timing._rng.random() >= self.config.window_blur_chance:
            return False
        
        # Short blur/focus cycle
        await self._trigger_blur()
        
        # Brief pause
        pause = self.timing._rng.uniform(0.5, 2.0)
        await asyncio.sleep(pause)
        
        await self._trigger_focus()
        
        self._events.append(FocusEvent(
            event_type="blur",
            duration=pause,
            timestamp=self.timing._rng.random()
        ))
        self._total_idle_time += pause
        
        return True
    
    async def simulate_distraction(self, duration: Optional[float] = None):
        """
        Simulate a human distraction.
        
        The page loses focus, idle period, then regains focus.
        
        Args:
            duration: Duration of distraction (random if None)
        """
        if not self.config.enabled:
            return
        
        if self._in_critical_section:
            logger.debug("Skipping distraction - in critical section")
            return
        
        if duration is None:
            duration = self.timing._rng.uniform(
                self.config.idle_min,
                self.config.idle_max
            )
        
        logger.debug(f"Simulating distraction for {duration:.1f}s")
        
        await self._trigger_blur()
        await asyncio.sleep(duration)
        await self._trigger_focus()
        
        self._events.append(FocusEvent(
            event_type="distraction",
            duration=duration,
            timestamp=self.timing._rng.random()
        ))
        self._total_idle_time += duration
    
    async def _trigger_blur(self):
        """Trigger window blur event"""
        try:
            await self.page.evaluate("""
                () => {
                    const event = new Event('blur');
                    window.dispatchEvent(event);
                    document.dispatchEvent(new Event('visibilitychange'));
                }
            """)
        except Exception as e:
            logger.debug(f"Failed to trigger blur: {e}")
    
    async def _trigger_focus(self):
        """Trigger window focus event"""
        try:
            await self.page.evaluate("""
                () => {
                    const event = new Event('focus');
                    window.dispatchEvent(event);
                    document.dispatchEvent(new Event('visibilitychange'));
                }
            """)
        except Exception as e:
            logger.debug(f"Failed to trigger focus: {e}")
    
    def enter_critical_section(self):
        """Mark start of critical section (no interruptions)"""
        self._in_critical_section = True
        logger.debug("Entered critical section")
    
    def exit_critical_section(self):
        """Mark end of critical section"""
        self._in_critical_section = False
        logger.debug("Exited critical section")
    
    class critical_section:
        """Context manager for critical sections"""
        
        def __init__(self, simulator: "TabFocusSimulator"):
            self.simulator = simulator
        
        async def __aenter__(self):
            self.simulator.enter_critical_section()
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.simulator.exit_critical_section()
            return False
    
    async def random_idle(self, min_seconds: float = 1.0, max_seconds: float = 5.0):
        """
        Insert a random idle pause.
        
        This doesn't trigger blur/focus, just a natural pause.
        
        Args:
            min_seconds: Minimum idle time
            max_seconds: Maximum idle time
        """
        duration = self.timing._rng.uniform(min_seconds, max_seconds)
        
        self._events.append(FocusEvent(
            event_type="idle",
            duration=duration,
            timestamp=self.timing._rng.random()
        ))
        
        await asyncio.sleep(duration)
        self._total_idle_time += duration
    
    def get_stats(self) -> dict:
        """Get focus simulation statistics"""
        event_counts = {}
        for event in self._events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
        
        return {
            "total_events": len(self._events),
            "event_counts": event_counts,
            "total_idle_time": round(self._total_idle_time, 2),
            "enabled": self.config.enabled,
        }
    
    def get_observability_log(self) -> dict:
        """Get debug log for observability"""
        return {
            "seed": self.timing.seed,
            "tab_switches": sum(1 for e in self._events if e.event_type == "tab_switch"),
            "blur_events": sum(1 for e in self._events if e.event_type == "blur"),
            "total_idle_seconds": round(self._total_idle_time, 2),
        }
