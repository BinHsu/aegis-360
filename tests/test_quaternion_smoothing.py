import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.quaternion_smoothing import smooth_quaternion_path
from aegis360.so3 import rotation_distance_radians


def yaw(degrees):
    half = math.radians(degrees) / 2.0
    return (0.0, math.sin(half), 0.0, math.cos(half))


class QuaternionSmoothingTests(unittest.TestCase):
    def test_static_and_sign_flipped_path_remains_static(self):
        timestamps = [index * 0.04 for index in range(20)]
        path = [
            yaw(0.0) if index % 2 == 0
            else tuple(-value for value in yaw(0.0))
            for index in range(20)
        ]
        result = smooth_quaternion_path(
            timestamps, path,
            radius_seconds=0.35,
            maximum_correction_radians=math.radians(25),
        )
        self.assertTrue(all(
            rotation_distance_radians(item, yaw(0.0)) < 1e-12
            for item in result
        ))
        self.assertTrue(all(
            sum(a * b for a, b in zip(left, right)) >= 0.0
            for left, right in zip(result, result[1:])
        ))

    def test_slow_turn_is_retained_away_from_boundaries(self):
        timestamps = [index * 0.04 for index in range(51)]
        path = [yaw(index * 0.4) for index in range(51)]
        result = smooth_quaternion_path(
            timestamps, path,
            radius_seconds=0.35,
            maximum_correction_radians=math.radians(25),
        )
        self.assertLess(
            math.degrees(rotation_distance_radians(result[25], path[25])),
            0.01,
        )

    def test_high_frequency_jitter_is_reduced(self):
        timestamps = [index * 0.04 for index in range(51)]
        trend = [yaw(index * 0.4) for index in range(51)]
        noisy = [
            yaw(index * 0.4 + (2.0 if index % 2 else -2.0))
            for index in range(51)
        ]
        result = smooth_quaternion_path(
            timestamps, noisy,
            radius_seconds=0.35,
            maximum_correction_radians=math.radians(25),
        )
        raw_rms = math.sqrt(sum(
            rotation_distance_radians(a, b) ** 2
            for a, b in zip(noisy[9:-9], trend[9:-9])
        ) / len(trend[9:-9]))
        smooth_rms = math.sqrt(sum(
            rotation_distance_radians(a, b) ** 2
            for a, b in zip(result[9:-9], trend[9:-9])
        ) / len(trend[9:-9]))
        self.assertLess(smooth_rms, raw_rms * 0.2)

    def test_maximum_correction_is_enforced(self):
        timestamps = [0.0, 0.04, 0.08]
        path = [yaw(0.0), yaw(90.0), yaw(0.0)]
        result = smooth_quaternion_path(
            timestamps, path,
            radius_seconds=0.35,
            maximum_correction_radians=math.radians(10),
        )
        self.assertLessEqual(
            math.degrees(rotation_distance_radians(path[1], result[1])),
            10.000001,
        )


if __name__ == "__main__":
    unittest.main()
