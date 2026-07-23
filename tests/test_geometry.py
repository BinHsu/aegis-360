import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.geometry import (  # noqa: E402
    angles_to_pixel,
    direction_from_angles,
    pixel_to_angles,
    spherical_distance,
    unwrap_yaw,
    wrap_yaw,
)


class PixelAngleConversionTests(unittest.TestCase):
    def test_cardinal_pixel_centers_round_trip(self):
        width, height = 1024, 512
        points = (
            (0.0, 0.0),
            (width - 1.0, 0.0),
            (width / 4 - 0.5, height / 2 - 0.5),
            (width / 2 - 0.5, height / 2 - 0.5),
            (3 * width / 4 - 0.5, height - 1.0),
        )
        for x, y in points:
            with self.subTest(x=x, y=y):
                yaw, pitch = pixel_to_angles(x, y, width, height)
                actual_x, actual_y = angles_to_pixel(yaw, pitch, width, height)
                self.assertAlmostEqual(actual_x, x, places=11)
                self.assertAlmostEqual(actual_y, y, places=11)

    def test_random_pixel_centers_round_trip(self):
        rng = random.Random(360)
        width, height = 1920, 960
        for _ in range(1000):
            x = rng.randrange(width)
            y = rng.randrange(height)
            yaw, pitch = pixel_to_angles(x, y, width, height)
            actual_x, actual_y = angles_to_pixel(yaw, pitch, width, height)
            self.assertAlmostEqual(actual_x, x, places=10)
            self.assertAlmostEqual(actual_y, y, places=10)

    def test_pitch_is_clamped_at_poles(self):
        width, height = 100, 50
        self.assertEqual(angles_to_pixel(0.0, math.pi, width, height)[1], -0.5)
        self.assertEqual(angles_to_pixel(0.0, -math.pi, width, height)[1], height - 0.5)

    def test_exact_pole_projection_edges_map_back_to_poles(self):
        width, height = 100, 50
        for pitch in (math.pi / 2, -math.pi / 2):
            x, y = angles_to_pixel(1.25, pitch, width, height)
            _, actual_pitch = pixel_to_angles(x, y, width, height)
            self.assertEqual(actual_pitch, pitch)

    def test_invalid_dimensions_and_nonfinite_values_are_rejected(self):
        with self.assertRaises(ValueError):
            pixel_to_angles(0.0, 0.0, 0, 10)
        with self.assertRaises(ValueError):
            angles_to_pixel(math.inf, 0.0, 10, 10)
        with self.assertRaises(ValueError):
            direction_from_angles(0.0, math.nan)


class SeamAndContinuityTests(unittest.TestCase):
    def test_wrap_uses_half_open_interval(self):
        self.assertEqual(wrap_yaw(math.pi), -math.pi)
        self.assertEqual(wrap_yaw(-math.pi), -math.pi)
        self.assertAlmostEqual(wrap_yaw(5 * math.pi / 2), math.pi / 2)

    def test_seam_crossing_unwrap_takes_short_path(self):
        before = math.radians(179.0)
        after_wrapped = math.radians(-179.0)
        after = unwrap_yaw(after_wrapped, before)
        self.assertAlmostEqual(math.degrees(after - before), 2.0, places=12)

    def test_repeated_unwrap_is_continuous_across_seam(self):
        wrapped = [math.radians(value) for value in (170, 175, 179, -179, -175, -170)]
        unwrapped = [wrapped[0]]
        for yaw in wrapped[1:]:
            unwrapped.append(unwrap_yaw(yaw, unwrapped[-1]))
        steps = [math.degrees(right - left) for left, right in zip(unwrapped, unwrapped[1:])]
        self.assertEqual([round(step) for step in steps], [5, 4, 2, 4, 5])
        self.assertTrue(all(abs(step) <= 5.0 for step in steps))


class SphericalDistanceTests(unittest.TestCase):
    def test_known_distances(self):
        self.assertAlmostEqual(spherical_distance((0.0, 0.0), (math.pi / 2, 0.0)), math.pi / 2)
        self.assertAlmostEqual(spherical_distance((0.0, 0.0), (math.pi, 0.0)), math.pi)
        self.assertAlmostEqual(spherical_distance((0.0, 0.0), (0.0, math.pi / 2)), math.pi / 2)

    def test_seam_neighbors_are_close(self):
        distance = spherical_distance(
            (math.radians(179.0), 0.0), (math.radians(-179.0), 0.0)
        )
        self.assertAlmostEqual(math.degrees(distance), 2.0, places=12)

    def test_yaw_does_not_change_exact_pole_direction(self):
        north_a = direction_from_angles(0.0, math.pi / 2)
        north_b = direction_from_angles(2.0, math.pi / 2)
        self.assertTrue(all(math.isfinite(value) for value in north_a + north_b))
        self.assertAlmostEqual(spherical_distance((0.0, math.pi / 2), (2.0, math.pi / 2)), 0.0)

    def test_distance_is_symmetric_and_finite_near_poles(self):
        points = [
            (math.radians(179.999), math.radians(89.999)),
            (math.radians(-179.999), math.radians(89.998)),
            (0.0, math.radians(-89.999)),
        ]
        for first in points:
            for second in points:
                forward = spherical_distance(first, second)
                reverse = spherical_distance(second, first)
                self.assertTrue(math.isfinite(forward))
                self.assertGreaterEqual(forward, 0.0)
                self.assertLessEqual(forward, math.pi)
                self.assertAlmostEqual(forward, reverse, places=15)


if __name__ == "__main__":
    unittest.main()
