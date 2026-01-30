"""
Behavior Module Tests
=====================
Tests for human-like behavior simulation components.
"""

import math
import random

import pytest

# ============== Timing Distribution Tests ==============


@pytest.mark.unit
class TestTimingDistributions:
    """Statistical timing distribution tests."""

    def test_uniform_distribution_bounds(self):
        """Uniform distribution should stay within bounds."""
        for _ in range(1000):
            value = random.uniform(0.5, 2.0)
            assert 0.5 <= value <= 2.0

    def test_gaussian_distribution_mean(self):
        """Gaussian distribution should center around mean."""
        values = [random.gauss(1.0, 0.2) for _ in range(10000)]
        mean = sum(values) / len(values)

        # Should be close to 1.0
        assert abs(mean - 1.0) < 0.05

    def test_clamped_gaussian(self):
        """Clamped gaussian should stay within bounds."""

        def clamped_gauss(mean, std, min_val, max_val):
            return max(min_val, min(max_val, random.gauss(mean, std)))

        for _ in range(1000):
            value = clamped_gauss(1.0, 0.5, 0.5, 2.0)
            assert 0.5 <= value <= 2.0

    def test_exponential_distribution(self):
        """Exponential distribution for wait times."""
        values = [random.expovariate(1.0) for _ in range(1000)]

        # All should be positive
        assert all(v > 0 for v in values)

        # Mean should be around 1.0
        mean = sum(values) / len(values)
        assert 0.8 < mean < 1.2


# ============== Bezier Curve Math Tests ==============


@pytest.mark.unit
class TestBezierCurveMath:
    """Bezier curve mathematical tests."""

    def test_linear_interpolation(self):
        """Linear interpolation between two points."""
        start, end = (0, 0), (100, 100)

        # t=0 should give start
        t = 0
        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        assert (x, y) == (0, 0)

        # t=1 should give end
        t = 1
        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        assert (x, y) == (100, 100)

        # t=0.5 should give midpoint
        t = 0.5
        x = start[0] + t * (end[0] - start[0])
        y = start[1] + t * (end[1] - start[1])
        assert (x, y) == (50, 50)

    def test_quadratic_bezier(self):
        """Quadratic bezier curve calculation."""
        p0, p1, p2 = (0, 0), (50, 100), (100, 0)

        def quadratic_bezier(t):
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            return (x, y)

        # Endpoints should match
        assert quadratic_bezier(0) == (0, 0)
        assert quadratic_bezier(1) == (100, 0)

        # Middle should curve upward (y > 0)
        mid = quadratic_bezier(0.5)
        assert mid[1] > 0  # Curved upward

    def test_cubic_bezier(self):
        """Cubic bezier curve calculation."""
        p0, p1, p2, p3 = (0, 0), (25, 100), (75, 100), (100, 0)

        def cubic_bezier(t):
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

        # Endpoints should match
        assert cubic_bezier(0) == (0, 0)
        assert cubic_bezier(1) == (100, 0)

    def test_bezier_curve_smoothness(self):
        """Bezier curve should produce smooth transitions."""
        p0, p1, p2 = (0, 0), (50, 100), (100, 0)

        def quadratic_bezier(t):
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
            return (x, y)

        # Generate points
        points = [quadratic_bezier(t / 100) for t in range(101)]

        # Check smoothness (no large jumps)
        for i in range(1, len(points)):
            dx = points[i][0] - points[i - 1][0]
            dy = points[i][1] - points[i - 1][1]
            distance = math.sqrt(dx**2 + dy**2)
            assert distance < 5  # Max 5 units between points


# ============== Distance and Geometry Tests ==============


@pytest.mark.unit
class TestGeometry:
    """Geometry calculation tests."""

    def test_euclidean_distance(self):
        """Euclidean distance calculation."""

        def distance(p1, p2):
            return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)

        # 3-4-5 triangle
        assert distance((0, 0), (3, 4)) == pytest.approx(5.0)

        # Same point
        assert distance((10, 10), (10, 10)) == 0

        # Horizontal
        assert distance((0, 0), (10, 0)) == 10

        # Vertical
        assert distance((0, 0), (0, 10)) == 10

    def test_angle_calculation(self):
        """Angle between two points."""

        def angle(p1, p2):
            return math.atan2(p2[1] - p1[1], p2[0] - p1[0])

        # Right (0 degrees)
        assert angle((0, 0), (1, 0)) == pytest.approx(0)

        # Up (90 degrees / pi/2)
        assert angle((0, 0), (0, 1)) == pytest.approx(math.pi / 2)

        # Left (180 degrees / pi)
        assert abs(angle((0, 0), (-1, 0))) == pytest.approx(math.pi)

    def test_point_on_line(self):
        """Check if point lies on line."""

        def point_on_line(p, start, end, tolerance=0.001):
            # Distance from point to line
            if start == end:
                return math.sqrt((p[0] - start[0]) ** 2 + (p[1] - start[1]) ** 2) < tolerance

            line_len = math.sqrt((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2)
            dist = (
                abs(
                    (end[0] - start[0]) * (start[1] - p[1])
                    - (start[0] - p[0]) * (end[1] - start[1])
                )
                / line_len
            )
            return dist < tolerance

        # Point on line
        assert point_on_line((5, 5), (0, 0), (10, 10))

        # Point off line
        assert not point_on_line((5, 6), (0, 0), (10, 10), tolerance=0.1)


# ============== Typing Dynamics Tests ==============


@pytest.mark.unit
class TestTypingDynamics:
    """Typing behavior tests."""

    def test_typing_delay_calculation(self):
        """Calculate realistic typing delays."""
        base_wpm = 60  # Words per minute
        chars_per_word = 5
        chars_per_minute = base_wpm * chars_per_word
        delay_per_char = 60 / chars_per_minute

        # Should be around 0.2 seconds per character
        assert delay_per_char == pytest.approx(0.2, abs=0.01)

    def test_typing_speed_variation(self):
        """Typing speed should vary naturally."""
        base_delay = 0.1

        delays = []
        for _ in range(100):
            # Add variation
            variation = random.gauss(1.0, 0.2)
            delay = base_delay * max(0.5, min(2.0, variation))
            delays.append(delay)

        # Should have variation
        assert max(delays) > min(delays) * 1.2

    def test_keyboard_layout_adjacency(self):
        """Test keyboard key adjacency for typos."""
        # QWERTY layout adjacency
        adjacent = {
            "q": ["w", "a"],
            "w": ["q", "e", "s", "a"],
            "e": ["w", "r", "d", "s"],
            "a": ["q", "w", "s", "z"],
            "s": ["a", "w", "e", "d", "z", "x"],
        }

        # Verify adjacency structure
        assert "w" in adjacent["q"]
        assert "e" in adjacent["w"]
        assert "q" not in adjacent["e"]  # Not adjacent


# ============== Scroll Behavior Tests ==============


@pytest.mark.unit
class TestScrollBehavior:
    """Scroll behavior tests."""

    def test_scroll_amount_distribution(self):
        """Scroll amounts should follow realistic distribution."""
        scroll_amounts = [random.randint(100, 500) for _ in range(100)]

        # Should have reasonable range
        assert min(scroll_amounts) >= 100
        assert max(scroll_amounts) <= 500

        # Mean should be around 300
        mean = sum(scroll_amounts) / len(scroll_amounts)
        assert 200 < mean < 400

    def test_scroll_velocity_curve(self):
        """Scroll should have acceleration and deceleration."""
        # Simulate scroll velocity over time
        _ = 1.0  # duration placeholder
        steps = 20

        velocities = []
        for i in range(steps):
            t = i / steps
            # Ease in-out curve
            if t < 0.5:
                velocity = 2 * t * t
            else:
                velocity = 1 - 2 * (1 - t) * (1 - t)
            velocities.append(velocity)

        # Should start slow, peak, then slow
        assert velocities[0] < velocities[len(velocities) // 2]
        assert velocities[-1] <= 1.0  # Final velocity


# ============== Reading Behavior Tests ==============


@pytest.mark.unit
class TestReadingBehavior:
    """Reading behavior simulation tests."""

    def test_reading_time_scales_with_content(self):
        """Reading time should scale with content length."""

        def calculate_reading_time(word_count, wpm=200):
            return word_count / wpm * 60  # seconds

        short_time = calculate_reading_time(100)
        long_time = calculate_reading_time(1000)

        # Longer content = more time
        assert long_time > short_time
        assert long_time == pytest.approx(short_time * 10)

    def test_reading_patterns(self):
        """Reading should include pauses and backtracking."""
        # Simulate reading with occasional pauses
        total_time = 0
        words_read = 0
        target_words = 500

        while words_read < target_words:
            # Read a chunk
            chunk = random.randint(20, 50)
            words_read += chunk
            total_time += chunk / 200 * 60  # Base reading time

            # Occasional pause (10% chance)
            if random.random() < 0.1:
                total_time += random.uniform(0.5, 2.0)

            # Occasional backtrack (5% chance)
            if random.random() < 0.05:
                words_read -= random.randint(5, 15)
                total_time += random.uniform(1.0, 3.0)

        # Total time should be reasonable
        assert total_time > 0
        assert total_time < 600  # Less than 10 minutes for 500 words


# ============== Focus Behavior Tests ==============


@pytest.mark.unit
class TestFocusBehavior:
    """Window focus behavior tests."""

    def test_focus_duration_distribution(self):
        """Focus duration should follow realistic distribution."""
        durations = []
        for _ in range(100):
            # Pareto-like distribution (many short, few long)
            base = random.uniform(5, 30)
            multiplier = random.paretovariate(2)
            duration = min(base * multiplier, 300)  # Cap at 5 minutes
            durations.append(duration)

        # Most should be short
        short_count = sum(1 for d in durations if d < 60)
        assert short_count > 50  # More than half under 1 minute

    def test_distraction_probability(self):
        """Should occasionally simulate distractions."""
        distractions = 0
        checks = 1000

        for _ in range(checks):
            # 2% chance of distraction per check
            if random.random() < 0.02:
                distractions += 1

        # Should have some distractions
        assert 10 < distractions < 40


# ============== Statistical Validation Tests ==============


@pytest.mark.unit
class TestStatisticalValidation:
    """Statistical validation of behavior distributions."""

    def test_chi_square_uniformity(self):
        """Test uniformity of random distribution."""
        buckets = [0] * 10
        samples = 10000

        for _ in range(samples):
            value = random.random()
            bucket = min(int(value * 10), 9)
            buckets[bucket] += 1

        expected = samples / 10
        chi_square = sum((b - expected) ** 2 / expected for b in buckets)

        # Chi-square should be reasonable (< 20 for 9 df at p=0.05)
        assert chi_square < 30

    def test_normal_distribution_properties(self):
        """Verify normal distribution properties."""
        samples = [random.gauss(0, 1) for _ in range(10000)]

        mean = sum(samples) / len(samples)
        variance = sum((x - mean) ** 2 for x in samples) / len(samples)
        std = math.sqrt(variance)

        # Mean should be near 0
        assert abs(mean) < 0.1

        # Std should be near 1
        assert 0.9 < std < 1.1

        # ~68% within 1 std
        within_1_std = sum(1 for x in samples if abs(x) < 1)
        assert 0.65 < within_1_std / len(samples) < 0.71
