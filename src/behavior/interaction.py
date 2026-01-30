"""
Interaction Sequencer
Enforces natural human interaction patterns for clicks, typing, and hovering.

Core rule: Clicks NEVER occur without preceding mouse motion.
Sequence: hover → move → pause → click

This prevents "teleporting" clicks that are easily detected by bot detection systems.

SEED DERIVATION: All randomness derived from SessionContext.
"""

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger
from playwright.async_api import Page

from .mouse import MouseMovementEngine, Point
from .timing import TimingDistributionEngine

if TYPE_CHECKING:
    from ..session.context import SessionContext


@dataclass
class InteractionConfig:
    """Configuration for interaction patterns"""

    always_hover_before_click: bool = True
    min_hover_duration: float = 0.1  # Minimum hover time before click
    max_hover_duration: float = 0.5  # Maximum hover time
    typing_warmup_delay: float = 0.2  # Delay before starting to type
    click_hold_duration: float = 0.05  # How long to hold click down


class InteractionSequencer:
    """
    Enforces natural interaction patterns.

    Core principles:
    - Clicks NEVER occur without preceding motion
    - Hover states are triggered before clicks
    - Pauses between actions are Weibull/Pareto distributed
    - Typing follows natural warmup patterns

    Usage:
        sequencer = InteractionSequencer(page, seed=12345)

        # Click with natural pattern
        await sequencer.click("button.submit")

        # Type with natural delays
        await sequencer.type_in_field("input#email", "user@example.com")

        # Hover over element
        await sequencer.hover("a.link")
    """

    def __init__(
        self, page: Page, seed: int | None = None, config: InteractionConfig | None = None
    ):
        """
        Initialize interaction sequencer.

        Args:
            page: Playwright page to interact with
            seed: Random seed for reproducibility
            config: Interaction configuration
        """
        self.page = page
        self.config = config or InteractionConfig()

        # Initialize behavior engines with same seed
        self.timing = TimingDistributionEngine(seed=seed)
        self.mouse = MouseMovementEngine(seed=seed, timing_engine=self.timing)

        # Track current mouse position
        self._mouse_pos: Point = Point(0, 0)

        logger.debug(f"InteractionSequencer initialized (seed: {self.timing.seed})")

    @classmethod
    def from_context(
        cls, page: Page, context: "SessionContext", config: InteractionConfig | None = None
    ) -> "InteractionSequencer":
        """
        Create from SessionContext with deterministic seed.

        Args:
            page: Playwright page
            context: Immutable SessionContext
            config: Optional interaction configuration

        Returns:
            InteractionSequencer with seed derived from context
        """
        seed = context.derive_subseed("interaction")
        return cls(page=page, seed=seed, config=config)

    async def click(
        self, selector: str, button: str = "left", click_count: int = 1, timeout: int = 5000
    ) -> bool:
        """
        Click an element with natural mouse movement.

        Sequence:
        1. Move mouse near element
        2. Hover (trigger hover state)
        3. Pause (natural hesitation)
        4. Click

        Args:
            selector: CSS selector for element
            button: Mouse button (left, right, middle)
            click_count: Number of clicks
            timeout: Timeout in milliseconds

        Returns:
            True if click succeeded
        """
        try:
            # Wait for and get element
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                logger.warning(f"Element not found: {selector}")
                return False

            # Get element position
            box = await element.bounding_box()
            if not box:
                logger.warning(f"Element has no bounding box: {selector}")
                return False

            # Calculate target (center of element with small random offset)
            target_x = box["x"] + box["width"] / 2
            target_y = box["y"] + box["height"] / 2

            # Add small random offset within element
            offset_x = self.timing._rng.uniform(-box["width"] * 0.2, box["width"] * 0.2)
            offset_y = self.timing._rng.uniform(-box["height"] * 0.2, box["height"] * 0.2)

            target = Point(target_x + offset_x, target_y + offset_y)

            # Step 1: Move to element
            await self._move_to(target)

            # Step 2: Hover (trigger hover state)
            hover_duration = self.timing._rng.uniform(
                self.config.min_hover_duration, self.config.max_hover_duration
            )
            await asyncio.sleep(hover_duration)

            # Step 3: Pause (click delay)
            click_delay = self.timing.get_click_delay()
            await asyncio.sleep(click_delay)

            # Step 4: Click
            await self.page.mouse.click(
                target.x,
                target.y,
                button=button,
                click_count=click_count,
                delay=self.config.click_hold_duration * 1000,  # Convert to ms
            )

            logger.debug(f"Clicked {selector} at ({target.x:.0f}, {target.y:.0f})")
            return True

        except Exception as e:
            logger.error(f"Click failed on {selector}: {e}")
            return False

    async def hover(
        self, selector: str, duration: float | None = None, timeout: int = 5000
    ) -> bool:
        """
        Hover over an element with natural movement.

        Args:
            selector: CSS selector for element
            duration: How long to hover (uses random if None)
            timeout: Timeout in milliseconds

        Returns:
            True if hover succeeded
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                return False

            box = await element.bounding_box()
            if not box:
                return False

            # Target center of element
            target = Point(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

            # Move to element
            await self._move_to(target)

            # Hover duration
            if duration is None:
                duration = self.timing._rng.uniform(0.3, 1.5)

            await asyncio.sleep(duration)

            logger.debug(f"Hovered over {selector} for {duration:.2f}s")
            return True

        except Exception as e:
            logger.error(f"Hover failed on {selector}: {e}")
            return False

    async def type_in_field(
        self, selector: str, text: str, clear_first: bool = True, timeout: int = 5000
    ) -> bool:
        """
        Type text into a field with natural patterns.

        Sequence:
        1. Move to field
        2. Click to focus
        3. Pause before typing
        4. Type with variable delays

        Args:
            selector: CSS selector for input field
            text: Text to type
            clear_first: Clear field before typing
            timeout: Timeout in milliseconds

        Returns:
            True if typing succeeded
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                return False

            box = await element.bounding_box()
            if not box:
                return False

            # Move and click to focus
            target = Point(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

            await self._move_to(target)
            await asyncio.sleep(self.timing.get_click_delay())
            await self.page.mouse.click(target.x, target.y)

            # Clear if requested
            if clear_first:
                await self.page.keyboard.press("Control+a")
                await asyncio.sleep(0.1)
                await self.page.keyboard.press("Delete")

            # Warmup pause before typing
            await asyncio.sleep(self.config.typing_warmup_delay)

            # Type character by character with variable delays
            for char in text:
                delay = self.timing.get_typing_delay()
                await self.page.keyboard.type(char, delay=0)
                await asyncio.sleep(delay)

            logger.debug(f"Typed {len(text)} chars into {selector}")
            return True

        except Exception as e:
            logger.error(f"Typing failed in {selector}: {e}")
            return False

    async def double_click(self, selector: str, timeout: int = 5000) -> bool:
        """Double-click an element with natural pattern"""
        return await self.click(selector, click_count=2, timeout=timeout)

    async def right_click(self, selector: str, timeout: int = 5000) -> bool:
        """Right-click an element with natural pattern"""
        return await self.click(selector, button="right", timeout=timeout)

    async def _move_to(self, target: Point):
        """Move mouse to target with natural path"""
        # Generate path
        path = self.mouse.generate_path(self._mouse_pos, target)

        # Execute path
        for path_point in path:
            await self.page.mouse.move(path_point.point.x, path_point.point.y)
            if path_point.delay > 0:
                await asyncio.sleep(path_point.delay)

        # Update position
        self._mouse_pos = target

    async def move_to_element(self, selector: str, timeout: int = 5000) -> bool:
        """Move mouse to element without clicking"""
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            if not element:
                return False

            box = await element.bounding_box()
            if not box:
                return False

            target = Point(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)

            await self._move_to(target)
            return True

        except Exception as e:
            logger.error(f"Move failed for {selector}: {e}")
            return False

    async def move_random(self):
        """Move mouse to a random position on the page"""
        viewport = self.page.viewport_size
        if not viewport:
            viewport = {"width": 1280, "height": 720}

        target = Point(
            self.timing._rng.uniform(50, viewport["width"] - 50),
            self.timing._rng.uniform(50, viewport["height"] - 50),
        )

        await self._move_to(target)

    def get_current_position(self) -> tuple[float, float]:
        """Get current mouse position"""
        return (self._mouse_pos.x, self._mouse_pos.y)

    def set_position(self, x: float, y: float):
        """Set current mouse position (for tracking external moves)"""
        self._mouse_pos = Point(x, y)
