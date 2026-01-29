"""
Mouse Movement Engine
Generates human-like mouse movement paths with Bezier curves, overshoot, and corrections.

Uses seeded RNG for session consistency and Weibull/Pareto distributions
for timing (via TimingDistributionEngine).

Key features:
- Cubic Bezier curves with random control points
- Overshoot with micro-corrections
- Variable velocity along path
- Gaussian noise for natural imprecision

SEED DERIVATION: All randomness derived from SessionContext.
"""

import math
import numpy as np
from typing import List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from loguru import logger

from .timing import TimingDistributionEngine
from ..core.constants import (
    MOUSE_OVERSHOOT_CHANCE,
    MOUSE_OVERSHOOT_MIN,
    MOUSE_OVERSHOOT_MAX,
    MOUSE_CORRECTION_STEPS,
    MOUSE_POINTS_PER_MOVE,
    MOUSE_NOISE_STDDEV,
)

if TYPE_CHECKING:
    from ..session.context import SessionContext


@dataclass
class Point:
    """A 2D point"""
    x: float
    y: float
    
    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> "Point":
        return Point(self.x * scalar, self.y * scalar)
    
    def distance_to(self, other: "Point") -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def to_tuple(self) -> Tuple[int, int]:
        return (int(round(self.x)), int(round(self.y)))
    
    @classmethod
    def from_tuple(cls, t: Tuple[int, int]) -> "Point":
        return cls(float(t[0]), float(t[1]))


@dataclass
class PathPoint:
    """A point in a mouse path with timing information"""
    point: Point
    delay: float  # Delay in seconds before moving to this point
    velocity: float  # Velocity at this point (pixels/second)
    
    def to_tuple(self) -> Tuple[int, int]:
        return self.point.to_tuple()


class MouseMovementEngine:
    """
    Generates human-like mouse movement paths.
    
    Key features:
    - Cubic Bezier curves (not straight lines)
    - Random control points for natural curvature
    - Overshoot with micro-corrections (5-15% past target)
    - Variable velocity (slows at start/end)
    - Gaussian noise for imprecision
    
    All randomness is seeded for session consistency.
    
    Usage:
        engine = MouseMovementEngine(seed=12345)
        
        # Generate path from (100, 200) to (500, 400)
        path = engine.generate_path(
            start=Point(100, 200),
            end=Point(500, 400)
        )
        
        # Execute path
        for pp in path:
            await page.mouse.move(pp.point.x, pp.point.y)
            await asyncio.sleep(pp.delay)
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        timing_engine: Optional[TimingDistributionEngine] = None
    ):
        """
        Initialize mouse movement engine.
        
        Args:
            seed: Random seed for reproducibility
            timing_engine: Timing engine for delays (creates new one if None)
        """
        self.seed = seed if seed is not None else np.random.randint(0, 2**31)
        self._rng = np.random.default_rng(self.seed)
        
        # Use provided timing engine or create new one with same seed
        self.timing = timing_engine or TimingDistributionEngine(seed=self.seed)
        
        logger.debug(f"MouseMovementEngine initialized (seed: {self.seed})")
    
    @classmethod
    def from_context(cls, context: "SessionContext", timing_engine: Optional[TimingDistributionEngine] = None) -> "MouseMovementEngine":
        """
        Create from SessionContext with deterministic seed.
        
        Args:
            context: Immutable SessionContext
            timing_engine: Optional timing engine (created from context if None)
            
        Returns:
            MouseMovementEngine with seed derived from context
        """
        seed = context.derive_subseed("mouse")
        if timing_engine is None:
            timing_engine = TimingDistributionEngine.from_context(context)
        return cls(seed=seed, timing_engine=timing_engine)
    
    def generate_path(
        self,
        start: Point,
        end: Point,
        num_points: Optional[int] = None,
        include_overshoot: bool = True
    ) -> List[PathPoint]:
        """
        Generate a human-like mouse movement path.
        
        Args:
            start: Starting point
            end: Ending point (target)
            num_points: Number of points (auto-calculated if None)
            include_overshoot: Include overshoot and correction
            
        Returns:
            List of PathPoints with positions and timing
        """
        distance = start.distance_to(end)
        
        # Auto-calculate points based on distance
        if num_points is None:
            num_points = max(MOUSE_POINTS_PER_MOVE, int(distance / 15))
        
        # Decide if we overshoot
        should_overshoot = (
            include_overshoot and 
            distance > 50 and  # Only overshoot for longer moves
            self._rng.random() < MOUSE_OVERSHOOT_CHANCE
        )
        
        if should_overshoot:
            # Generate path to overshoot point, then correction to target
            overshoot_target = self._calculate_overshoot(start, end)
            
            # Path to overshoot point (most of the movement)
            main_path = self._generate_bezier_path(
                start, overshoot_target, 
                num_points=int(num_points * 0.8)
            )
            
            # Correction path back to target
            correction_path = self._generate_correction_path(
                overshoot_target, end,
                num_points=MOUSE_CORRECTION_STEPS
            )
            
            path = main_path + correction_path
        else:
            # Simple path to target
            path = self._generate_bezier_path(start, end, num_points)
        
        # Add noise to all points
        path = self._add_noise(path)
        
        # Calculate delays and velocities
        path = self._calculate_timing(path, distance)
        
        return path
    
    def _generate_bezier_path(
        self,
        start: Point,
        end: Point,
        num_points: int
    ) -> List[PathPoint]:
        """Generate a cubic Bezier curve path"""
        # Generate control points
        control_points = self._generate_control_points(start, end)
        
        path = []
        for i in range(num_points + 1):
            t = i / num_points
            point = self._cubic_bezier(t, control_points)
            path.append(PathPoint(point=point, delay=0, velocity=0))
        
        return path
    
    def _generate_control_points(
        self,
        start: Point,
        end: Point
    ) -> List[Point]:
        """Generate random control points for Bezier curve"""
        # Midpoint
        mid = Point(
            (start.x + end.x) / 2,
            (start.y + end.y) / 2
        )
        
        # Distance for offset calculation
        distance = start.distance_to(end)
        max_offset = distance * 0.4  # Up to 40% of distance
        
        # Random offsets for control points
        # This creates the natural curve
        cp1_offset = Point(
            self._rng.uniform(-max_offset, max_offset),
            self._rng.uniform(-max_offset, max_offset)
        )
        cp2_offset = Point(
            self._rng.uniform(-max_offset, max_offset),
            self._rng.uniform(-max_offset, max_offset)
        )
        
        # Position control points
        cp1 = Point(
            start.x + (mid.x - start.x) * 0.3 + cp1_offset.x,
            start.y + (mid.y - start.y) * 0.3 + cp1_offset.y
        )
        cp2 = Point(
            mid.x + (end.x - mid.x) * 0.7 + cp2_offset.x,
            mid.y + (end.y - mid.y) * 0.7 + cp2_offset.y
        )
        
        return [start, cp1, cp2, end]
    
    def _cubic_bezier(self, t: float, points: List[Point]) -> Point:
        """Calculate point on cubic Bezier curve at parameter t"""
        p0, p1, p2, p3 = points
        
        # Cubic Bezier formula
        x = ((1-t)**3 * p0.x + 
             3 * (1-t)**2 * t * p1.x + 
             3 * (1-t) * t**2 * p2.x + 
             t**3 * p3.x)
        y = ((1-t)**3 * p0.y + 
             3 * (1-t)**2 * t * p1.y + 
             3 * (1-t) * t**2 * p2.y + 
             t**3 * p3.y)
        
        return Point(x, y)
    
    def _calculate_overshoot(self, start: Point, end: Point) -> Point:
        """Calculate overshoot point past target"""
        # Direction vector
        direction = end - start
        distance = start.distance_to(end)
        
        if distance == 0:
            return end
        
        # Normalize direction
        norm_dir = Point(direction.x / distance, direction.y / distance)
        
        # Overshoot amount (5-15% of distance)
        overshoot_ratio = self._rng.uniform(MOUSE_OVERSHOOT_MIN, MOUSE_OVERSHOOT_MAX)
        overshoot_distance = distance * overshoot_ratio
        
        # Add slight randomness to overshoot direction
        angle_offset = self._rng.uniform(-0.2, 0.2)  # Small angle variation
        cos_a, sin_a = math.cos(angle_offset), math.sin(angle_offset)
        
        rotated_dir = Point(
            norm_dir.x * cos_a - norm_dir.y * sin_a,
            norm_dir.x * sin_a + norm_dir.y * cos_a
        )
        
        return Point(
            end.x + rotated_dir.x * overshoot_distance,
            end.y + rotated_dir.y * overshoot_distance
        )
    
    def _generate_correction_path(
        self,
        overshoot: Point,
        target: Point,
        num_points: int
    ) -> List[PathPoint]:
        """Generate a correction path back to target"""
        path = []
        
        for i in range(1, num_points + 1):
            t = i / num_points
            # Linear interpolation with slight ease-out
            ease_t = 1 - (1 - t) ** 2
            
            point = Point(
                overshoot.x + (target.x - overshoot.x) * ease_t,
                overshoot.y + (target.y - overshoot.y) * ease_t
            )
            path.append(PathPoint(point=point, delay=0, velocity=0))
        
        return path
    
    def _add_noise(self, path: List[PathPoint]) -> List[PathPoint]:
        """Add Gaussian noise to path points"""
        noisy_path = []
        
        for i, pp in enumerate(path):
            # Don't add noise to first and last points
            if i == 0 or i == len(path) - 1:
                noisy_path.append(pp)
                continue
            
            noise_x = self._rng.normal(0, MOUSE_NOISE_STDDEV)
            noise_y = self._rng.normal(0, MOUSE_NOISE_STDDEV)
            
            noisy_point = Point(
                pp.point.x + noise_x,
                pp.point.y + noise_y
            )
            noisy_path.append(PathPoint(
                point=noisy_point,
                delay=pp.delay,
                velocity=pp.velocity
            ))
        
        return noisy_path
    
    def _calculate_timing(
        self,
        path: List[PathPoint],
        total_distance: float
    ) -> List[PathPoint]:
        """Calculate delays and velocities for path points"""
        if len(path) < 2:
            return path
        
        # Base time for movement (scaled by distance)
        # Humans move at roughly 200-800 pixels/second
        base_velocity = self._rng.uniform(200, 600)
        total_time = total_distance / base_velocity
        
        timed_path = [path[0]]  # First point has no delay
        
        for i in range(1, len(path)):
            prev_point = path[i-1].point
            curr_point = path[i].point
            
            segment_dist = prev_point.distance_to(curr_point)
            
            # Velocity varies along path (slow at ends, faster in middle)
            progress = i / len(path)
            velocity_factor = 4 * progress * (1 - progress) + 0.5  # Parabola, peaks at 0.5
            
            segment_velocity = base_velocity * velocity_factor
            
            # Calculate delay
            if segment_velocity > 0:
                delay = segment_dist / segment_velocity
            else:
                delay = 0.001
            
            # Add small random variation
            delay *= self._rng.uniform(0.9, 1.1)
            
            timed_path.append(PathPoint(
                point=curr_point,
                delay=max(0.001, delay),  # Minimum 1ms
                velocity=segment_velocity
            ))
        
        return timed_path
    
    def add_overshoot(
        self,
        path: List[PathPoint],
        target: Point
    ) -> List[PathPoint]:
        """
        Add overshoot and correction to an existing path.
        
        This is for cases where you want to add overshoot after generating
        a basic path.
        
        Args:
            path: Existing path
            target: Target point
            
        Returns:
            Path with overshoot and correction added
        """
        if len(path) < 2:
            return path
        
        # Get last point as overshoot location
        last_point = path[-1].point
        
        # Generate correction back to target
        correction = self._generate_correction_path(
            last_point, target,
            num_points=MOUSE_CORRECTION_STEPS
        )
        
        return path + correction
    
    def get_movement_time(
        self,
        start: Point,
        end: Point
    ) -> float:
        """
        Estimate total movement time in seconds.
        
        Args:
            start: Starting point
            end: Target point
            
        Returns:
            Estimated time in seconds
        """
        distance = start.distance_to(end)
        
        # Fitts's Law approximation: time ∝ log2(distance/target_size)
        # Simplified to: time = a + b * distance
        a = 0.1  # Base time
        b = 0.001  # Time per pixel
        
        estimated = a + b * distance
        
        # Add variance
        return estimated * self._rng.uniform(0.8, 1.2)
