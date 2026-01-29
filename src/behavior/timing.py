"""
Timing Distribution Engine
Generates human-like timing values using statistical distributions.

Uses Weibull and Pareto distributions instead of uniform random.
This makes timing patterns statistically realistic and resistant to behavioral analytics.

Why not uniform random?
- Uniform timing is trivially detectable
- Real human behavior follows power-law and Weibull distributions
- This approach creates natural clustering and rare outliers

SEED DERIVATION
===============
All randomness MUST be derived from SessionContext.
When initialized with a SessionContext, the seed is deterministic.
Same context → same timing patterns.
"""

import numpy as np
from typing import Optional, TYPE_CHECKING
from scipy import stats
from dataclasses import dataclass
from loguru import logger

from ..core.constants import (
    WEIBULL_DWELL_SHAPE,
    WEIBULL_DWELL_SCALE,
    WEIBULL_SCROLL_SHAPE,
    WEIBULL_SCROLL_SCALE,
    WEIBULL_TYPING_SHAPE,
    WEIBULL_TYPING_SCALE,
    PARETO_CLICK_ALPHA,
    PARETO_CLICK_MIN,
    PARETO_HESITATION_ALPHA,
    PARETO_HESITATION_MIN,
    PARETO_HESITATION_MAX,
)

if TYPE_CHECKING:
    from ..session.context import SessionContext


@dataclass
class TimingConfig:
    """Configuration for timing distributions"""
    # Weibull parameters
    dwell_shape: float = WEIBULL_DWELL_SHAPE
    dwell_scale: float = WEIBULL_DWELL_SCALE
    scroll_shape: float = WEIBULL_SCROLL_SHAPE
    scroll_scale: float = WEIBULL_SCROLL_SCALE
    typing_shape: float = WEIBULL_TYPING_SHAPE
    typing_scale: float = WEIBULL_TYPING_SCALE
    
    # Pareto parameters
    click_alpha: float = PARETO_CLICK_ALPHA
    click_min: float = PARETO_CLICK_MIN
    hesitation_alpha: float = PARETO_HESITATION_ALPHA
    hesitation_min: float = PARETO_HESITATION_MIN
    hesitation_max: float = PARETO_HESITATION_MAX


class TimingDistributionEngine:
    """
    Generates timing values using statistical distributions.
    
    Distributions used:
    - Weibull: For dwell time, scroll pauses, typing delays
        - Shape > 1: Creates a peak (mode), most values cluster around it
        - Good for modeling "typical" durations with some variance
    
    - Pareto (power-law): For click delays, rare hesitations
        - Creates "fat tail" - most values small, rare very large values
        - Good for modeling occasional human hesitations
    
    All methods are seeded for session consistency:
    - Same session = same behavioral patterns
    - Different sessions = different distributions
    
    MUST be initialized with seed from SessionContext for determinism.
    
    Usage:
        # From SessionContext (preferred)
        engine = TimingDistributionEngine.from_context(context)
        
        # Or with explicit seed
        engine = TimingDistributionEngine(seed=12345)
        
        # Get various timing values
        dwell = engine.get_dwell_time(content_length=1500)
        click_delay = engine.get_click_delay()
        typing_delay = engine.get_typing_delay()
        scroll_pause = engine.get_scroll_pause()
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        config: Optional[TimingConfig] = None
    ):
        """
        Initialize timing engine.
        
        Args:
            seed: Random seed for reproducibility (random if None)
            config: Timing configuration (uses defaults if None)
        """
        self.seed = seed if seed is not None else np.random.randint(0, 2**31)
        self.config = config or TimingConfig()
    
    @classmethod
    def from_context(cls, context: "SessionContext", config: Optional[TimingConfig] = None) -> "TimingDistributionEngine":
        """
        Create from SessionContext with deterministic seed.
        
        Args:
            context: Immutable SessionContext
            config: Optional timing configuration
            
        Returns:
            TimingDistributionEngine with seed derived from context
        """
        # Use context's derive_subseed for component-specific seed
        seed = context.derive_subseed("timing")
        return cls(seed=seed, config=config)
        
        # Initialize seeded RNG
        self._rng = np.random.default_rng(self.seed)
        
        # Pre-compute distribution objects for efficiency
        self._weibull_dwell = stats.weibull_min(
            c=self.config.dwell_shape,
            scale=self.config.dwell_scale
        )
        self._weibull_scroll = stats.weibull_min(
            c=self.config.scroll_shape,
            scale=self.config.scroll_scale
        )
        self._weibull_typing = stats.weibull_min(
            c=self.config.typing_shape,
            scale=self.config.typing_scale
        )
        self._pareto_click = stats.pareto(b=self.config.click_alpha)
        self._pareto_hesitation = stats.pareto(b=self.config.hesitation_alpha)
        
        logger.debug(f"TimingDistributionEngine initialized (seed: {self.seed})")
    
    def get_dwell_time(self, content_length: int = 1000) -> float:
        """
        Get dwell time (time spent on page) in seconds.
        
        Uses Weibull distribution scaled by content length.
        Longer content = longer dwell time.
        
        Args:
            content_length: Approximate content length in characters
            
        Returns:
            Dwell time in seconds
        """
        # Base Weibull sample
        base = self._weibull_dwell.rvs(random_state=self._rng)
        
        # Scale by content length (assume ~200 chars/second reading)
        content_factor = max(1, content_length / 200)
        
        # Apply scaling with some variance
        dwell = base * content_factor
        
        # Ensure minimum 1 second, cap at 120 seconds
        return max(1.0, min(120.0, dwell))
    
    def get_click_delay(self) -> float:
        """
        Get delay before clicking in seconds.
        
        Uses Pareto distribution for occasional hesitations.
        Most clicks are quick, but some have longer pauses.
        
        Returns:
            Click delay in seconds (typically 0.1-2s, rarely longer)
        """
        # Pareto gives values >= 1, so we scale and shift
        raw = self._pareto_click.rvs(random_state=self._rng)
        
        # Transform: Pareto(1, alpha) → delay
        # Most values will be close to 1, occasional outliers
        delay = self.config.click_min * raw
        
        # Cap at reasonable maximum (5 seconds)
        return min(5.0, delay)
    
    def get_scroll_pause(self) -> float:
        """
        Get pause between scroll actions in seconds.
        
        Uses Weibull distribution for natural pauses.
        
        Returns:
            Pause duration in seconds
        """
        pause = self._weibull_scroll.rvs(random_state=self._rng)
        
        # Ensure minimum 0.1 seconds, cap at 5 seconds
        return max(0.1, min(5.0, pause))
    
    def get_typing_delay(self) -> float:
        """
        Get delay between keystrokes in seconds.
        
        Uses Weibull distribution for natural typing rhythm.
        
        Returns:
            Keystroke delay in seconds (typically 50-200ms)
        """
        delay = self._weibull_typing.rvs(random_state=self._rng)
        
        # Ensure minimum 30ms, cap at 500ms
        return max(0.03, min(0.5, delay))
    
    def get_typing_delays(self, text_length: int) -> list:
        """
        Get a list of typing delays for a text.
        
        Args:
            text_length: Number of characters to type
            
        Returns:
            List of delays in seconds
        """
        return [self.get_typing_delay() for _ in range(text_length)]
    
    def get_hesitation(self) -> float:
        """
        Get a rare long hesitation in seconds.
        
        Uses Pareto distribution for "fat tail" behavior.
        These should be used sparingly to simulate human distraction.
        
        Returns:
            Hesitation duration (1-10 seconds typically)
        """
        raw = self._pareto_hesitation.rvs(random_state=self._rng)
        
        # Scale to hesitation range
        hesitation = self.config.hesitation_min * raw
        
        # Cap at maximum
        return min(self.config.hesitation_max, hesitation)
    
    def get_reading_time(self, word_count: int) -> float:
        """
        Get realistic reading time for content.
        
        Based on average reading speed with Weibull variance.
        
        Args:
            word_count: Number of words to "read"
            
        Returns:
            Reading time in seconds
        """
        # Average adult reads ~200-250 words per minute
        # Use 225 wpm as base
        base_time = word_count / 225 * 60  # Convert to seconds
        
        # Apply Weibull variance (shape 2 gives moderate variance)
        variance = self._weibull_dwell.rvs(random_state=self._rng) / self.config.dwell_scale
        
        # Variance factor between 0.7 and 1.5
        factor = 0.7 + (variance * 0.8)
        
        return max(1.0, base_time * factor)
    
    def get_action_delay(self, action_type: str = "default") -> float:
        """
        Get delay for various action types.
        
        Args:
            action_type: Type of action (click, scroll, type, hover)
            
        Returns:
            Appropriate delay in seconds
        """
        if action_type == "click":
            return self.get_click_delay()
        elif action_type == "scroll":
            return self.get_scroll_pause()
        elif action_type == "type":
            return self.get_typing_delay()
        elif action_type == "hover":
            return self.get_click_delay() * 0.5  # Hover is faster than click
        else:
            # Default: short Weibull-distributed pause
            return self._weibull_scroll.rvs(random_state=self._rng) * 0.5
    
    def should_hesitate(self, probability: float = 0.05) -> bool:
        """
        Randomly decide if we should insert a hesitation.
        
        Args:
            probability: Chance of hesitation (default 5%)
            
        Returns:
            True if should hesitate
        """
        return self._rng.random() < probability
    
    def get_batch_delays(self, count: int, delay_type: str = "scroll") -> list:
        """
        Get a batch of delays for repeated actions.
        
        Args:
            count: Number of delays to generate
            delay_type: Type of delay (scroll, click, type)
            
        Returns:
            List of delays
        """
        return [self.get_action_delay(delay_type) for _ in range(count)]
    
    @property
    def timing_stats(self) -> dict:
        """Get statistics about the timing distributions"""
        return {
            "seed": self.seed,
            "dwell_mean": self._weibull_dwell.mean(),
            "scroll_mean": self._weibull_scroll.mean(),
            "typing_mean": self._weibull_typing.mean(),
            "click_mean": self._pareto_click.mean() * self.config.click_min if self.config.click_alpha > 1 else "undefined",
        }
