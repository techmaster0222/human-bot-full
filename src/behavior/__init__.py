"""Behavior Module - Human-like Interaction Patterns"""

from .timing import TimingDistributionEngine
from .mouse import MouseMovementEngine, Point, PathPoint
from .interaction import InteractionSequencer
from .scroll import ScrollBehaviorEngine
from .focus import TabFocusSimulator

__all__ = [
    "TimingDistributionEngine",
    "MouseMovementEngine",
    "Point",
    "PathPoint",
    "InteractionSequencer",
    "ScrollBehaviorEngine",
    "TabFocusSimulator",
]
