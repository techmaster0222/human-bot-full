"""Behavior Module - Human-like Interaction Patterns"""

from .focus import TabFocusSimulator
from .interaction import InteractionSequencer
from .mouse import MouseMovementEngine, PathPoint, Point
from .scroll import ScrollBehaviorEngine
from .timing import TimingDistributionEngine

__all__ = [
    "TimingDistributionEngine",
    "MouseMovementEngine",
    "Point",
    "PathPoint",
    "InteractionSequencer",
    "ScrollBehaviorEngine",
    "TabFocusSimulator",
]
