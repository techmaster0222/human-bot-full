"""
Scroll Behavior Engine
Human-like scrolling with incremental movement, back-scroll corrections, and variable speed.

Key features:
- Incremental scrolling (not full page jumps)
- Variable speed using Weibull distribution
- Back-scroll corrections (10% chance)
- Never reaches perfect bottom
- Reading pauses during scrolling

SEED DERIVATION: All randomness derived from SessionContext.
"""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger
from playwright.async_api import Page

from ..core.constants import (
    SCROLL_BACK_CHANCE,
    SCROLL_BACK_RATIO,
    SCROLL_BOTTOM_MARGIN,
    SCROLL_MAX_PIXELS,
    SCROLL_MIN_PIXELS,
)
from .timing import TimingDistributionEngine

if TYPE_CHECKING:
    from ..session.context import SessionContext


@dataclass
class ScrollAction:
    """A single scroll action"""

    amount: int  # Positive = down, negative = up
    pause: float  # Pause after scroll in seconds
    is_reading_pause: bool = False  # Is this a reading/content pause?


@dataclass
class ScrollConfig:
    """Configuration for scroll behavior"""

    min_scroll: int = SCROLL_MIN_PIXELS
    max_scroll: int = SCROLL_MAX_PIXELS
    back_scroll_chance: float = SCROLL_BACK_CHANCE
    back_scroll_ratio: float = SCROLL_BACK_RATIO
    bottom_margin: int = SCROLL_BOTTOM_MARGIN
    reading_pause_chance: float = 0.15
    reading_pause_min: float = 0.5
    reading_pause_max: float = 3.0


class ScrollBehaviorEngine:
    """
    Generates human-like scroll patterns.

    Key behaviors:
    - Incremental scrolling (50-400px at a time)
    - Variable speed (Weibull distributed pauses)
    - 10% chance of back-scroll correction
    - Reading pauses (15% chance during scroll)
    - Never scrolls perfectly to bottom

    Usage:
        engine = ScrollBehaviorEngine(page, seed=12345)

        # Scroll down the page
        await engine.scroll_page(direction="down")

        # Scroll to a percentage of page
        await engine.scroll_to_percent(50)

        # Scroll to element
        await engine.scroll_to_element("div.content")
    """

    def __init__(self, page: Page, seed: int | None = None, config: ScrollConfig | None = None):
        """
        Initialize scroll behavior engine.

        Args:
            page: Playwright page
            seed: Random seed for reproducibility
            config: Scroll configuration
        """
        self.page = page
        self.config = config or ScrollConfig()
        self.timing = TimingDistributionEngine(seed=seed)

        self._total_scrolled = 0
        self._back_scroll_count = 0

        logger.debug(f"ScrollBehaviorEngine initialized (seed: {self.timing.seed})")

    @classmethod
    def from_context(
        cls, page: Page, context: "SessionContext", config: ScrollConfig | None = None
    ) -> "ScrollBehaviorEngine":
        """
        Create from SessionContext with deterministic seed.

        Args:
            page: Playwright page
            context: Immutable SessionContext
            config: Optional scroll configuration

        Returns:
            ScrollBehaviorEngine with seed derived from context
        """
        seed = context.derive_subseed("scroll")
        return cls(page=page, seed=seed, config=config)

    async def scroll_page(
        self, direction: str = "down", distance: int | None = None, smooth: bool = True
    ) -> int:
        """
        Scroll the page with human-like behavior.

        Args:
            direction: "down" or "up"
            distance: Total distance to scroll (auto if None)
            smooth: Use incremental smooth scrolling

        Returns:
            Total pixels scrolled
        """
        # Get page dimensions
        page_height = await self._get_page_height()
        viewport_height = await self._get_viewport_height()
        current_scroll = await self._get_scroll_position()

        if distance is None:
            # Calculate reasonable scroll distance
            if direction == "down":
                max_scroll = page_height - viewport_height - self.config.bottom_margin
                distance = max_scroll - current_scroll
            else:
                distance = current_scroll

        if distance <= 0:
            return 0

        # Generate scroll actions
        actions = self._generate_scroll_sequence(distance, direction)

        # Execute actions
        total_scrolled = 0
        for action in actions:
            if smooth:
                # Smooth scroll animation
                await self._smooth_scroll(action.amount)
            else:
                # Instant scroll
                await self.page.evaluate(f"window.scrollBy(0, {action.amount})")

            total_scrolled += abs(action.amount)

            # Apply pause
            await asyncio.sleep(action.pause)

        self._total_scrolled += total_scrolled
        return total_scrolled

    async def scroll_to_percent(self, percent: float, smooth: bool = True) -> int:
        """
        Scroll to a percentage of the page.

        Args:
            percent: Target percentage (0-100)
            smooth: Use smooth scrolling

        Returns:
            Pixels scrolled
        """
        page_height = await self._get_page_height()
        viewport_height = await self._get_viewport_height()
        current_scroll = await self._get_scroll_position()

        # Calculate target position
        max_scroll = page_height - viewport_height
        target = max_scroll * (percent / 100)

        # Calculate distance
        distance = target - current_scroll
        direction = "down" if distance > 0 else "up"

        return await self.scroll_page(
            direction=direction, distance=abs(int(distance)), smooth=smooth
        )

    async def scroll_to_element(self, selector: str, timeout: int = 5000) -> bool:
        """
        Scroll to bring an element into view.

        Args:
            selector: CSS selector for element
            timeout: Timeout in milliseconds

        Returns:
            True if element is now in view
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                return False

            # Get element position
            box = await element.bounding_box()
            if not box:
                return False

            viewport_height = await self._get_viewport_height()
            current_scroll = await self._get_scroll_position()

            # Calculate scroll needed
            element_top = box["y"] + current_scroll
            target_scroll = element_top - viewport_height / 3  # Position 1/3 from top

            distance = target_scroll - current_scroll
            direction = "down" if distance > 0 else "up"

            if abs(distance) > 50:  # Only scroll if more than 50px away
                await self.scroll_page(
                    direction=direction, distance=abs(int(distance)), smooth=True
                )

            return True

        except Exception as e:
            logger.error(f"Failed to scroll to {selector}: {e}")
            return False

    def _generate_scroll_sequence(self, total_distance: int, direction: str) -> list[ScrollAction]:
        """Generate a sequence of scroll actions"""
        actions = []
        remaining = total_distance
        multiplier = 1 if direction == "down" else -1
        last_scroll = 0

        while remaining > 0:
            # Get scroll amount with Weibull-like variance
            base_amount = self._get_scroll_amount()

            if base_amount > remaining:
                base_amount = remaining

            # Decide on back-scroll
            if last_scroll > 0 and self.timing._rng.random() < self.config.back_scroll_chance:
                # Back-scroll correction
                back_amount = int(last_scroll * self.config.back_scroll_ratio)
                actions.append(
                    ScrollAction(
                        amount=-back_amount * multiplier,
                        pause=self.timing.get_scroll_pause(),
                        is_reading_pause=False,
                    )
                )
                self._back_scroll_count += 1

                # Re-scroll forward
                forward_amount = back_amount + base_amount
                if forward_amount > remaining:
                    forward_amount = remaining

                actions.append(
                    ScrollAction(
                        amount=forward_amount * multiplier, pause=self.timing.get_scroll_pause()
                    )
                )
                remaining -= forward_amount - back_amount
                last_scroll = forward_amount
            else:
                # Normal scroll
                actions.append(
                    ScrollAction(
                        amount=base_amount * multiplier, pause=self.timing.get_scroll_pause()
                    )
                )
                remaining -= base_amount
                last_scroll = base_amount

            # Maybe add reading pause
            if self.timing._rng.random() < self.config.reading_pause_chance:
                pause_duration = self.timing._rng.uniform(
                    self.config.reading_pause_min, self.config.reading_pause_max
                )
                actions.append(ScrollAction(amount=0, pause=pause_duration, is_reading_pause=True))

        # Never end exactly at bottom
        if direction == "down" and actions:
            last_action = actions[-1]
            if last_action.amount > 0:
                # Slightly reduce last scroll
                reduction = self.timing._rng.integers(10, 50)
                last_action.amount = max(10, last_action.amount - reduction)

        return actions

    def _get_scroll_amount(self) -> int:
        """Get a variable scroll amount using Weibull distribution"""
        # Base amount with variance
        base = self.timing._rng.uniform(self.config.min_scroll, self.config.max_scroll)

        # Apply Weibull-like variance
        variance = self.timing.get_scroll_pause()  # Reuse for variance
        factor = 0.7 + (variance * 0.6)  # Factor between 0.7 and 1.3

        return int(base * factor)

    async def _smooth_scroll(self, amount: int, steps: int = 5):
        """Perform smooth incremental scroll"""
        step_amount = amount / steps

        for _ in range(steps):
            await self.page.evaluate(f"window.scrollBy(0, {step_amount})")
            await asyncio.sleep(0.016)  # ~60fps

    async def _get_page_height(self) -> int:
        """Get total page height"""
        return await self.page.evaluate("document.documentElement.scrollHeight")

    async def _get_viewport_height(self) -> int:
        """Get viewport height"""
        viewport = self.page.viewport_size
        return viewport["height"] if viewport else 720

    async def _get_scroll_position(self) -> int:
        """Get current scroll position"""
        return await self.page.evaluate("window.scrollY")

    async def scroll_up(self, distance: int | None = None) -> int:
        """Convenience method to scroll up"""
        return await self.scroll_page("up", distance)

    async def scroll_down(self, distance: int | None = None) -> int:
        """Convenience method to scroll down"""
        return await self.scroll_page("down", distance)

    def get_stats(self) -> dict:
        """Get scrolling statistics"""
        return {
            "total_scrolled": self._total_scrolled,
            "back_scroll_count": self._back_scroll_count,
            "seed": self.timing.seed,
        }
