"""
Bot Actions Module (Playwright)
Provides high-level actions with human-like behavior using Playwright.
"""

import asyncio
import time
import random
from typing import Optional, List, Tuple, Union, Dict, Any
from playwright.async_api import Page, Locator, ElementHandle, Response
from loguru import logger

from .human_behavior import HumanBehavior, BehaviorConfig


class BotActions:
    """
    High-level bot actions with human-like behavior using Playwright.
    
    Features:
    - Precise async timing control
    - Natural mouse movement with bezier curves
    - Human-like typing with variable delays
    - Network request visibility
    - Realistic scrolling patterns
    """
    
    def __init__(
        self,
        page: Page,
        behavior: HumanBehavior = None,
        default_timeout: int = 30000  # Playwright uses ms
    ):
        """
        Initialize bot actions.
        
        Args:
            page: Playwright Page instance
            behavior: HumanBehavior instance (creates default if not provided)
            default_timeout: Default wait timeout in milliseconds
        """
        self.page = page
        self.behavior = behavior or HumanBehavior()
        self.default_timeout = default_timeout
        
        # Network tracking
        self._network_requests: List[Dict] = []
        self._setup_network_tracking()
        
        logger.debug("BotActions initialized (Playwright)")
    
    def _setup_network_tracking(self):
        """Set up network request tracking"""
        async def on_request(request):
            self._network_requests.append({
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "timestamp": time.time()
            })
        
        self.page.on("request", on_request)
    
    # ============== Navigation ==============
    
    async def navigate_to(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout: int = None
    ) -> Optional[Response]:
        """
        Navigate to a URL with natural behavior.
        
        Args:
            url: URL to navigate to
            wait_until: Wait condition (load, domcontentloaded, networkidle)
            timeout: Navigation timeout in ms
            
        Returns:
            Response object or None
        """
        try:
            logger.info(f"Navigating to: {url}")
            
            # Small pause before navigation (like human clicking a link)
            await self._human_delay("short")
            
            response = await self.page.goto(
                url,
                wait_until=wait_until,
                timeout=timeout or self.default_timeout
            )
            
            # Brief pause after page loads (human orientation)
            await self._human_delay("medium")
            
            return response
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return None
    
    async def refresh_page(self, wait_until: str = "domcontentloaded"):
        """Refresh the current page"""
        await self._human_delay("short")
        await self.page.reload(wait_until=wait_until)
        await self._human_delay("medium")
    
    async def go_back(self, wait_until: str = "domcontentloaded"):
        """Go back in browser history"""
        await self._human_delay("short")
        await self.page.go_back(wait_until=wait_until)
    
    async def go_forward(self, wait_until: str = "domcontentloaded"):
        """Go forward in browser history"""
        await self._human_delay("short")
        await self.page.go_forward(wait_until=wait_until)
    
    # ============== Element Interaction ==============
    
    async def click(
        self,
        selector: str,
        natural_movement: bool = True,
        timeout: int = None,
        force: bool = False
    ) -> bool:
        """
        Click an element with human-like behavior.
        
        Args:
            selector: CSS selector or text selector
            natural_movement: Use natural mouse movement
            timeout: Wait timeout
            force: Force click even if not visible
            
        Returns:
            True if successful
        """
        try:
            locator = self.page.locator(selector).first
            
            # Wait for element
            await locator.wait_for(
                state="visible",
                timeout=timeout or self.default_timeout
            )
            
            if natural_movement:
                # Get element bounding box
                box = await locator.bounding_box()
                if box:
                    # Calculate target point with slight randomness
                    target_x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
                    target_y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
                    
                    # Move mouse naturally
                    await self._natural_mouse_move(target_x, target_y)
                    
                    # Hover pause
                    await self._human_delay("hover")
            
            # Click
            await locator.click(force=force)
            logger.debug(f"Clicked: {selector}")
            
            # Post-click pause
            await self._human_delay("short")
            
            return True
            
        except Exception as e:
            logger.warning(f"Click failed for '{selector}': {e}")
            return False
    
    async def double_click(self, selector: str, natural_movement: bool = True) -> bool:
        """Double-click an element"""
        try:
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=self.default_timeout)
            
            if natural_movement:
                box = await locator.bounding_box()
                if box:
                    target_x = box["x"] + box["width"] / 2
                    target_y = box["y"] + box["height"] / 2
                    await self._natural_mouse_move(target_x, target_y)
                    await self._human_delay("hover")
            
            await locator.dblclick()
            return True
            
        except Exception as e:
            logger.warning(f"Double-click failed: {e}")
            return False
    
    async def right_click(self, selector: str) -> bool:
        """Right-click (context menu) an element"""
        try:
            locator = self.page.locator(selector).first
            await locator.click(button="right")
            return True
        except Exception as e:
            logger.warning(f"Right-click failed: {e}")
            return False
    
    async def hover(self, selector: str, duration: float = None) -> bool:
        """Hover over an element"""
        try:
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=self.default_timeout)
            
            box = await locator.bounding_box()
            if box:
                target_x = box["x"] + box["width"] / 2
                target_y = box["y"] + box["height"] / 2
                await self._natural_mouse_move(target_x, target_y)
            else:
                await locator.hover()
            
            duration = duration or self.behavior.random_medium_pause()
            await asyncio.sleep(duration)
            
            return True
            
        except Exception as e:
            logger.warning(f"Hover failed: {e}")
            return False
    
    # ============== Typing ==============
    
    async def type_text(
        self,
        selector: str,
        text: str,
        clear_first: bool = True,
        submit: bool = False,
        human_like: bool = True
    ) -> bool:
        """
        Type text with human-like behavior.
        
        Args:
            selector: Input element selector
            text: Text to type
            clear_first: Clear existing text first
            submit: Press Enter after typing
            human_like: Use human-like typing delays
            
        Returns:
            True if successful
        """
        try:
            locator = self.page.locator(selector).first
            await locator.wait_for(state="visible", timeout=self.default_timeout)
            
            # Click to focus
            await self.click(selector, natural_movement=True)
            
            # Clear if requested
            if clear_first:
                await locator.clear()
                await self._human_delay("short")
            
            if human_like:
                # Type with human-like delays
                typing_sequence = self.behavior.get_typing_delays(text)
                
                for char, delay in typing_sequence:
                    if char == "BACKSPACE":
                        await self.page.keyboard.press("Backspace")
                    else:
                        await self.page.keyboard.type(char, delay=0)
                    await asyncio.sleep(delay)
            else:
                # Fast typing
                await locator.fill(text)
            
            # Submit if requested
            if submit:
                await self._human_delay("short")
                await self.page.keyboard.press("Enter")
            
            logger.debug(f"Typed {len(text)} chars")
            return True
            
        except Exception as e:
            logger.warning(f"Typing failed: {e}")
            return False
    
    async def type_fast(self, selector: str, text: str, clear_first: bool = True) -> bool:
        """Type text quickly using fill()"""
        try:
            locator = self.page.locator(selector).first
            if clear_first:
                await locator.clear()
            await locator.fill(text)
            return True
        except Exception as e:
            logger.warning(f"Fast typing failed: {e}")
            return False
    
    async def press_key(self, key: str):
        """Press a keyboard key"""
        await self.page.keyboard.press(key)
    
    async def key_combo(self, *keys: str):
        """Press key combination (e.g., Ctrl+A)"""
        for key in keys[:-1]:
            await self.page.keyboard.down(key)
        await self.page.keyboard.press(keys[-1])
        for key in reversed(keys[:-1]):
            await self.page.keyboard.up(key)
    
    # ============== Scrolling ==============
    
    async def scroll_down(self, pixels: int = None, smooth: bool = True) -> bool:
        """
        Scroll down the page.
        
        Args:
            pixels: Pixels to scroll (random if not provided)
            smooth: Use smooth scrolling
        """
        try:
            amount = pixels or self.behavior.get_scroll_amount()
            
            if smooth:
                await self.page.evaluate(
                    f"window.scrollBy({{top: {amount}, behavior: 'smooth'}})"
                )
            else:
                await self.page.evaluate(f"window.scrollBy(0, {amount})")
            
            await asyncio.sleep(self.behavior.config.scroll_pause)
            return True
            
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")
            return False
    
    async def scroll_up(self, pixels: int = None, smooth: bool = True) -> bool:
        """Scroll up the page"""
        amount = pixels or self.behavior.get_scroll_amount()
        return await self.scroll_down(-amount, smooth)
    
    async def scroll_to_element(self, selector: str) -> bool:
        """Scroll element into view"""
        try:
            locator = self.page.locator(selector).first
            await locator.scroll_into_view_if_needed()
            await self._human_delay("medium")
            return True
        except Exception as e:
            logger.warning(f"Scroll to element failed: {e}")
            return False
    
    async def scroll_to_bottom(self) -> bool:
        """Scroll to the bottom of the page naturally"""
        try:
            total_height = await self.page.evaluate("document.body.scrollHeight")
            
            sequence = self.behavior.get_scroll_sequence(total_height, direction="down")
            
            for amount, delay in sequence:
                if amount != 0:
                    await self.page.evaluate(
                        f"window.scrollBy({{top: {amount}, behavior: 'smooth'}})"
                    )
                await asyncio.sleep(delay)
            
            return True
        except Exception as e:
            logger.warning(f"Scroll to bottom failed: {e}")
            return False
    
    async def scroll_to_top(self) -> bool:
        """Scroll to the top of the page"""
        try:
            await self.page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await self._human_delay("medium")
            return True
        except Exception as e:
            logger.warning(f"Scroll to top failed: {e}")
            return False
    
    # ============== Mouse Movement ==============
    
    async def _natural_mouse_move(self, target_x: float, target_y: float):
        """
        Move mouse naturally using bezier curve path.
        
        Args:
            target_x: Target X coordinate
            target_y: Target Y coordinate
        """
        try:
            # Get current mouse position (approximate from center if unknown)
            viewport = self.page.viewport_size
            if viewport:
                current_x = viewport["width"] / 2
                current_y = viewport["height"] / 2
            else:
                current_x, current_y = 500, 300
            
            # Generate bezier path
            path = self.behavior.generate_mouse_path(
                (int(current_x), int(current_y)),
                (int(target_x), int(target_y))
            )
            
            delays = self.behavior.get_movement_delays(len(path))
            
            # Execute path
            for i, (x, y) in enumerate(path):
                await self.page.mouse.move(x, y)
                if i < len(delays):
                    await asyncio.sleep(delays[i])
                    
        except Exception as e:
            # Fallback to direct movement
            logger.debug(f"Natural mouse move fallback: {e}")
            await self.page.mouse.move(target_x, target_y)
    
    async def random_mouse_movement(self):
        """Perform random mouse movement on the page"""
        try:
            viewport = self.page.viewport_size
            if viewport:
                target_x = random.randint(50, viewport["width"] - 50)
                target_y = random.randint(50, viewport["height"] - 50)
                await self._natural_mouse_move(target_x, target_y)
        except Exception as e:
            logger.debug(f"Random mouse movement failed: {e}")
    
    # ============== Waiting & Timing ==============
    
    async def _human_delay(self, delay_type: str):
        """Add human-like delay"""
        if delay_type == "short":
            await asyncio.sleep(self.behavior.random_short_pause())
        elif delay_type == "medium":
            await asyncio.sleep(self.behavior.random_medium_pause())
        elif delay_type == "long":
            await asyncio.sleep(self.behavior.random_long_pause())
        elif delay_type == "hover":
            await asyncio.sleep(self.behavior.get_click_delay())
        elif delay_type == "thinking":
            await asyncio.sleep(self.behavior.random_thinking_pause())
    
    async def wait(self, seconds: float):
        """Wait for specified duration"""
        await asyncio.sleep(seconds)
    
    async def wait_random(self, min_seconds: float = 1, max_seconds: float = 5):
        """Wait for random duration within range"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
    
    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: int = None
    ) -> bool:
        """Wait for element with specified state"""
        try:
            await self.page.locator(selector).wait_for(
                state=state,
                timeout=timeout or self.default_timeout
            )
            return True
        except:
            return False
    
    async def wait_for_navigation(self, wait_until: str = "domcontentloaded"):
        """Wait for navigation to complete"""
        await self.page.wait_for_load_state(wait_until)
    
    async def wait_for_network_idle(self, timeout: int = None):
        """Wait for network to become idle"""
        await self.page.wait_for_load_state(
            "networkidle",
            timeout=timeout or self.default_timeout
        )
    
    # ============== Idle Behavior ==============
    
    async def idle_behavior(self, duration: float = None):
        """
        Simulate idle/reading behavior.
        
        Args:
            duration: How long to idle (random if not provided)
        """
        duration = duration or self.behavior.random_thinking_pause()
        end_time = time.time() + duration
        
        while time.time() < end_time:
            action = random.random()
            
            if action < 0.1:
                await self.random_mouse_movement()
            elif action < 0.15:
                if random.random() < 0.5:
                    await self.scroll_down()
                else:
                    await self.scroll_up()
            
            await asyncio.sleep(random.uniform(0.5, 2.0))
    
    async def simulate_reading(self, content_length: int = 1000):
        """Simulate reading page content"""
        duration = self.behavior.get_page_view_time(content_length)
        await self.idle_behavior(duration)
    
    # ============== Element Queries ==============
    
    async def is_visible(self, selector: str) -> bool:
        """Check if element is visible"""
        try:
            return await self.page.locator(selector).first.is_visible()
        except:
            return False
    
    async def is_enabled(self, selector: str) -> bool:
        """Check if element is enabled"""
        try:
            return await self.page.locator(selector).first.is_enabled()
        except:
            return False
    
    async def get_text(self, selector: str) -> str:
        """Get text content from element"""
        try:
            return await self.page.locator(selector).first.text_content() or ""
        except:
            return ""
    
    async def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get attribute value from element"""
        try:
            return await self.page.locator(selector).first.get_attribute(attribute)
        except:
            return None
    
    async def get_element_count(self, selector: str) -> int:
        """Get count of matching elements"""
        return await self.page.locator(selector).count()
    
    # ============== Screenshots & Network ==============
    
    async def take_screenshot(self, path: str, full_page: bool = False) -> bool:
        """Take a screenshot"""
        try:
            await self.page.screenshot(path=path, full_page=full_page)
            logger.info(f"Screenshot saved: {path}")
            return True
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False
    
    def get_network_requests(self) -> List[Dict]:
        """Get tracked network requests"""
        return self._network_requests.copy()
    
    def clear_network_requests(self):
        """Clear tracked network requests"""
        self._network_requests.clear()
    
    # ============== Page Info ==============
    
    @property
    def url(self) -> str:
        """Get current page URL"""
        return self.page.url
    
    @property
    def title(self) -> str:
        """Get current page title"""
        return asyncio.get_event_loop().run_until_complete(self.page.title())
    
    async def get_title(self) -> str:
        """Get current page title (async)"""
        return await self.page.title()
    
    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript expression"""
        return await self.page.evaluate(expression)
