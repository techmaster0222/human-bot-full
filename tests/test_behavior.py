"""Behavior module tests."""

import math

import pytest

try:
    import numpy as np
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    from src.behavior import Point
    BEHAVIOR_AVAILABLE = True
except ImportError:
    BEHAVIOR_AVAILABLE = False


@pytest.mark.skipif(not BEHAVIOR_AVAILABLE, reason="Behavior module not available")
class TestPoint:
    """Point class tests."""

    def test_creation(self):
        from src.behavior import Point
        p = Point(100.0, 200.0)
        assert p.x == 100.0
        assert p.y == 200.0

    def test_addition(self):
        from src.behavior import Point
        result = Point(100, 100) + Point(50, 50)
        assert result.x == 150
        assert result.y == 150

    def test_subtraction(self):
        from src.behavior import Point
        result = Point(100, 100) - Point(30, 20)
        assert result.x == 70
        assert result.y == 80

    def test_multiplication(self):
        from src.behavior import Point
        result = Point(100, 50) * 2.0
        assert result.x == 200
        assert result.y == 100

    def test_distance(self):
        from src.behavior import Point
        distance = Point(0, 0).distance_to(Point(3, 4))
        assert distance == pytest.approx(5.0, abs=0.001)


@pytest.mark.skipif(not SCIPY_AVAILABLE, reason="scipy not available")
class TestStatisticalDistributions:
    """Statistical distribution tests."""

    def test_weibull(self):
        values = stats.weibull_min.rvs(2.0, scale=1.0, size=100)
        assert len(values) == 100
        assert all(v > 0 for v in values)

    def test_pareto(self):
        values = stats.pareto.rvs(2.0, size=100)
        assert len(values) == 100
        assert all(v > 0 for v in values)

    def test_gaussian(self):
        values = np.random.normal(1.0, 0.2, 100)
        assert np.mean(values) == pytest.approx(1.0, abs=0.2)


class TestBezierMath:
    """Bezier curve math tests."""

    def test_linear_interpolation(self):
        start, end = (0, 0), (100, 100)

        # t=0 -> start
        x = start[0] + 0 * (end[0] - start[0])
        assert x == 0

        # t=1 -> end
        x = start[0] + 1 * (end[0] - start[0])
        assert x == 100

        # t=0.5 -> midpoint
        x = start[0] + 0.5 * (end[0] - start[0])
        assert x == 50

    def test_quadratic_bezier(self):
        p0, p1, p2 = (0, 0), (50, 100), (100, 0)

        def bezier(t):
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            return x, y

        assert bezier(0) == (0, 0)
        assert bezier(1) == (100, 0)
        assert bezier(0.5)[1] > 0

    def test_distance(self):
        def dist(p1, p2):
            return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

        assert dist((0, 0), (3, 4)) == pytest.approx(5.0, abs=0.001)


class TestTimingLogic:
    """Timing logic tests."""

    def test_delay_bounds(self):
        import random
        for _ in range(100):
            delay = random.uniform(0.5, 2.0)
            assert 0.5 <= delay <= 2.0

    def test_gaussian_clamping(self):
        import random

        def clamped_gaussian(mean, std, min_val, max_val):
            return max(min_val, min(max_val, random.gauss(mean, std)))

        for _ in range(100):
            value = clamped_gaussian(1.0, 0.5, 0.5, 2.0)
            assert 0.5 <= value <= 2.0

    def test_typing_delay(self):
        base_wpm = 60
        chars_per_word = 5
        delay = 60 / (base_wpm * chars_per_word)
        assert delay == pytest.approx(0.2, abs=0.01)
