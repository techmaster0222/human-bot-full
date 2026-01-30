"""
Human-like Behavior Simulator
Generates natural mouse movements, typing patterns, and browsing behavior.
"""

import math
import random
from dataclasses import dataclass

import numpy as np
from loguru import logger


@dataclass
class BehaviorConfig:
    """Configuration for human-like behavior"""

    # Typing
    typing_min_delay: float = 0.05  # 50ms
    typing_max_delay: float = 0.20  # 200ms
    typo_chance: float = 0.02
    typo_correction_delay: float = 0.5

    # Mouse movement
    mouse_speed: str = "human"  # slow, human, fast
    curve_intensity: float = 0.7
    random_pauses: bool = True

    # Scrolling
    smooth_scroll: bool = True
    min_scroll: int = 100
    max_scroll: int = 500
    scroll_pause: float = 0.3

    # Click behavior
    hover_before_click: bool = True
    hover_duration: float = 0.2

    # Reading simulation
    read_speed_wpm: int = 250  # words per minute


class HumanBehavior:
    """
    Simulates human-like behavior patterns for browser automation.

    Features:
    - Natural mouse movement curves (Bezier curves)
    - Variable typing speeds with occasional typos
    - Random pauses and "thinking" moments
    - Realistic scroll patterns
    - Natural click timing
    """

    def __init__(self, config: BehaviorConfig = None):
        """
        Initialize human behavior simulator.

        Args:
            config: BehaviorConfig instance (uses defaults if not provided)
        """
        self.config = config or BehaviorConfig()

        # Speed multipliers based on config
        self._speed_multipliers = {"slow": 1.5, "human": 1.0, "fast": 0.5}

        logger.debug("HumanBehavior simulator initialized")

    # ============== Mouse Movement ==============

    def generate_mouse_path(
        self, start: tuple[int, int], end: tuple[int, int], num_points: int = None
    ) -> list[tuple[int, int]]:
        """
        Generate a human-like mouse movement path using Bezier curves.

        Args:
            start: Starting (x, y) coordinates
            end: Ending (x, y) coordinates
            num_points: Number of points in the path (auto-calculated if None)

        Returns:
            List of (x, y) coordinates forming the path
        """
        # Calculate distance
        distance = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)

        # Auto-calculate number of points based on distance
        if num_points is None:
            num_points = max(int(distance / 10), 10)

        # Generate control points for Bezier curve
        control_points = self._generate_control_points(start, end)

        # Generate path using cubic Bezier
        path = []
        for i in range(num_points + 1):
            t = i / num_points
            point = self._cubic_bezier(t, control_points)

            # Add small random noise for more natural movement
            noise_x = random.gauss(0, 1)
            noise_y = random.gauss(0, 1)

            path.append((int(point[0] + noise_x), int(point[1] + noise_y)))

        return path

    def _generate_control_points(
        self, start: tuple[int, int], end: tuple[int, int]
    ) -> list[tuple[float, float]]:
        """Generate control points for Bezier curve"""
        # Midpoint
        mid_x = (start[0] + end[0]) / 2
        mid_y = (start[1] + end[1]) / 2

        # Distance for control point offset
        distance = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
        offset = distance * self.config.curve_intensity * 0.3

        # Random offsets for control points (creates curve)
        cp1 = (
            start[0] + (mid_x - start[0]) * 0.5 + random.uniform(-offset, offset),
            start[1] + (mid_y - start[1]) * 0.5 + random.uniform(-offset, offset),
        )

        cp2 = (
            mid_x + (end[0] - mid_x) * 0.5 + random.uniform(-offset, offset),
            mid_y + (end[1] - mid_y) * 0.5 + random.uniform(-offset, offset),
        )

        return [start, cp1, cp2, end]

    def _cubic_bezier(self, t: float, points: list[tuple[float, float]]) -> tuple[float, float]:
        """Calculate point on cubic Bezier curve"""
        p0, p1, p2, p3 = points

        x = (
            (1 - t) ** 3 * p0[0]
            + 3 * (1 - t) ** 2 * t * p1[0]
            + 3 * (1 - t) * t**2 * p2[0]
            + t**3 * p3[0]
        )
        y = (
            (1 - t) ** 3 * p0[1]
            + 3 * (1 - t) ** 2 * t * p1[1]
            + 3 * (1 - t) * t**2 * p2[1]
            + t**3 * p3[1]
        )

        return (x, y)

    def get_movement_delays(self, path_length: int) -> list[float]:
        """
        Generate delays between mouse movements.

        Args:
            path_length: Number of points in path

        Returns:
            List of delays in seconds
        """
        delays = []
        speed_mult = self._speed_multipliers.get(self.config.mouse_speed, 1.0)

        for _ in range(path_length):
            # Base delay
            base_delay = random.uniform(0.001, 0.005) * speed_mult

            # Occasionally add micro-pauses (human hesitation)
            if self.config.random_pauses and random.random() < 0.05:
                base_delay += random.uniform(0.01, 0.05)

            delays.append(base_delay)

        return delays

    # ============== Typing Simulation ==============

    def get_typing_delays(self, text: str) -> list[tuple[str, float]]:
        """
        Generate typing sequence with human-like delays.

        Args:
            text: Text to type

        Returns:
            List of (character, delay) tuples
        """
        result = []

        for i, char in enumerate(text):
            # Base delay
            delay = random.uniform(self.config.typing_min_delay, self.config.typing_max_delay)

            # Adjust for special characters (slower)
            if char in "!@#$%^&*()_+-=[]{}|;':\",./<>?":
                delay *= 1.3

            # Adjust for same-hand consecutive keys (slightly faster)
            if i > 0 and self._same_hand_keys(text[i - 1], char):
                delay *= 0.9

            # Add occasional longer pauses (thinking)
            if random.random() < 0.02:
                delay += random.uniform(0.3, 0.8)

            # Simulate typo
            if self.config.typo_chance > 0 and random.random() < self.config.typo_chance:
                # Add wrong character
                wrong_char = self._get_nearby_key(char)
                result.append((wrong_char, delay))

                # Pause, then backspace
                result.append(("BACKSPACE", self.config.typo_correction_delay))

                # Type correct character
                result.append(
                    (
                        char,
                        random.uniform(self.config.typing_min_delay, self.config.typing_max_delay),
                    )
                )
            else:
                result.append((char, delay))

        return result

    def _same_hand_keys(self, key1: str, key2: str) -> bool:
        """Check if two keys are typed with the same hand"""
        left_hand = set("qwertasdfgzxcvb12345`~!@#$%")
        right_hand = set("yuiophjklnm67890-=[]\\;',./^&*()_+{}|:\"<>?")

        k1, k2 = key1.lower(), key2.lower()
        return (k1 in left_hand and k2 in left_hand) or (k1 in right_hand and k2 in right_hand)

    def _get_nearby_key(self, char: str) -> str:
        """Get a nearby key for typo simulation"""
        keyboard_neighbors = {
            "a": "sqwz",
            "b": "vghn",
            "c": "xdfv",
            "d": "serfcx",
            "e": "wrsdf",
            "f": "drtgvc",
            "g": "ftyhbv",
            "h": "gyujnb",
            "i": "ujklo",
            "j": "huiknm",
            "k": "jiolm",
            "l": "kop",
            "m": "njk",
            "n": "bhjm",
            "o": "iklp",
            "p": "ol",
            "q": "wa",
            "r": "edft",
            "s": "awedxz",
            "t": "rfgy",
            "u": "yhji",
            "v": "cfgb",
            "w": "qase",
            "x": "zsdc",
            "y": "tghu",
            "z": "asx",
        }

        lower = char.lower()
        if lower in keyboard_neighbors:
            typo = random.choice(keyboard_neighbors[lower])
            return typo.upper() if char.isupper() else typo
        return char

    # ============== Scrolling ==============

    def get_scroll_amount(self) -> int:
        """Get a natural scroll amount"""
        # Use normal distribution centered around middle of range
        mean = (self.config.min_scroll + self.config.max_scroll) / 2
        std = (self.config.max_scroll - self.config.min_scroll) / 4

        amount = int(np.random.normal(mean, std))
        return max(self.config.min_scroll, min(self.config.max_scroll, amount))

    def get_scroll_sequence(
        self, total_distance: int, direction: str = "down"
    ) -> list[tuple[int, float]]:
        """
        Generate a sequence of scroll actions.

        Args:
            total_distance: Total pixels to scroll
            direction: "up" or "down"

        Returns:
            List of (scroll_amount, delay) tuples
        """
        sequence = []
        scrolled = 0
        multiplier = -1 if direction == "up" else 1

        while scrolled < total_distance:
            amount = self.get_scroll_amount()
            remaining = total_distance - scrolled

            if amount > remaining:
                amount = remaining

            # Add scroll action
            delay = random.uniform(self.config.scroll_pause * 0.5, self.config.scroll_pause * 1.5)

            sequence.append((amount * multiplier, delay))
            scrolled += amount

            # Occasionally add reading pause
            if random.random() < 0.15:
                sequence.append((0, random.uniform(0.5, 2.0)))

        return sequence

    # ============== Click Behavior ==============

    def get_click_delay(self) -> float:
        """Get delay before clicking (after hover)"""
        if self.config.hover_before_click:
            return random.uniform(
                self.config.hover_duration * 0.7, self.config.hover_duration * 1.3
            )
        return 0.01

    def get_double_click_delay(self) -> float:
        """Get delay between double-click clicks"""
        return random.uniform(0.05, 0.15)

    # ============== Reading Simulation ==============

    def estimate_read_time(self, text: str) -> float:
        """
        Estimate time needed to read text.

        Args:
            text: Text to read

        Returns:
            Estimated read time in seconds
        """
        word_count = len(text.split())
        base_time = (word_count / self.config.read_speed_wpm) * 60

        # Add variability
        variability = random.uniform(0.8, 1.2)

        return base_time * variability

    def get_page_view_time(self, content_length: int = 1000, has_images: bool = False) -> float:
        """
        Get realistic time to spend viewing a page.

        Args:
            content_length: Approximate character count
            has_images: Whether page has images (adds viewing time)

        Returns:
            Suggested view time in seconds
        """
        # Base reading time
        word_estimate = content_length / 5  # Rough words estimate
        read_time = self.estimate_read_time(" " * int(word_estimate))

        # Add image viewing time
        if has_images:
            read_time += random.uniform(2, 8)

        # Add general browsing behavior variance
        read_time *= random.uniform(0.6, 1.4)

        # Minimum 3 seconds, maximum 5 minutes
        return max(3, min(300, read_time))

    # ============== Random Delays ==============

    def random_short_pause(self) -> float:
        """Get a random short pause (100-500ms)"""
        return random.uniform(0.1, 0.5)

    def random_medium_pause(self) -> float:
        """Get a random medium pause (500ms-2s)"""
        return random.uniform(0.5, 2.0)

    def random_long_pause(self) -> float:
        """Get a random long pause (2-5s)"""
        return random.uniform(2.0, 5.0)

    def random_thinking_pause(self) -> float:
        """Get a random 'thinking' pause (1-10s)"""
        return random.uniform(1.0, 10.0)

    def should_take_break(self, session_duration: float) -> bool:
        """
        Determine if bot should take a break.

        Args:
            session_duration: How long session has been running (seconds)

        Returns:
            True if should take a break
        """
        # More likely to take break as session goes on
        break_probability = min(0.3, session_duration / 3600 * 0.1)
        return random.random() < break_probability

    def get_break_duration(self) -> float:
        """Get duration for a break (5-60 seconds)"""
        return random.uniform(5, 60)
