import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.renderer_orientation import (
    quaternion_to_v360_yaw_pitch_roll,
    stabilization_correction,
    v360_yaw_pitch_roll_to_quaternion,
)
from aegis360.so3 import rotation_distance_radians


class RendererOrientationTests(unittest.TestCase):
    def test_yaw_pitch_roll_round_trip_and_signs(self):
        for degrees in (
            (37.0, 0.0, 0.0),
            (0.0, 23.0, 0.0),
            (0.0, 0.0, 31.0),
            (28.0, -17.0, 12.0),
        ):
            wanted = tuple(math.radians(value) for value in degrees)
            quaternion = v360_yaw_pitch_roll_to_quaternion(*wanted)
            actual = quaternion_to_v360_yaw_pitch_roll(quaternion)
            for observed, expected in zip(actual, wanted):
                self.assertAlmostEqual(observed, expected, places=12)

    def test_no_stabilization_has_identity_correction(self):
        raw = v360_yaw_pitch_roll_to_quaternion(
            math.radians(10), math.radians(-5), math.radians(3)
        )
        correction = stabilization_correction(raw, raw)
        self.assertLess(
            rotation_distance_radians(correction, (0.0, 0.0, 0.0, 1.0)),
            1e-12,
        )

    def test_fixed_world_correction_inverts_pure_source_yaw(self):
        raw = v360_yaw_pitch_roll_to_quaternion(math.radians(9), 0.0, 0.0)
        correction = stabilization_correction(
            raw, (0.0, 0.0, 0.0, 1.0)
        )
        yaw, pitch, roll = quaternion_to_v360_yaw_pitch_roll(correction)
        self.assertAlmostEqual(math.degrees(yaw), -9.0, places=10)
        self.assertAlmostEqual(pitch, 0.0, places=12)
        self.assertAlmostEqual(roll, 0.0, places=12)


if __name__ == "__main__":
    unittest.main()
