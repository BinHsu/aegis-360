import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.relative_rotation_segments import build_relative_rotation_segments
from aegis360.so3 import rotation_distance_radians


def yaw(degrees):
    half = math.radians(degrees) / 2.0
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def step(index, state, rotation):
    return {
        "previous_pts_seconds": index * 0.04,
        "current_pts_seconds": (index + 1) * 0.04,
        "state": state,
        "rotation_xyzw": rotation,
    }


class RelativeRotationSegmentTests(unittest.TestCase):
    def test_leading_gap_starts_later_identity_anchored_segment(self):
        segments = build_relative_rotation_segments([
            step(0, "invalid", None),
            step(1, "invalid", None),
            step(2, "measured", yaw(1.0)),
            step(3, "interpolated", yaw(2.0)),
        ])
        self.assertEqual(len(segments), 1)
        segment = segments[0]
        self.assertEqual(segment["anchor_pts_seconds"], 0.08)
        self.assertEqual(segment["start_step_index"], 2)
        self.assertEqual(len(segment["samples"]), 3)
        self.assertLess(
            rotation_distance_radians(
                tuple(segment["samples"][-1][
                    "relative_orientation_xyzw"
                ]),
                tuple(yaw(3.0)),
            ),
            1e-6,
        )

    def test_internal_unfilled_gap_splits_relative_segments(self):
        segments = build_relative_rotation_segments([
            step(0, "measured", yaw(1.0)),
            step(1, "invalid", None),
            step(2, "measured", yaw(2.0)),
        ])
        self.assertEqual(len(segments), 2)
        self.assertEqual(
            [segment["anchor_pts_seconds"] for segment in segments],
            [0.0, 0.08],
        )


if __name__ == "__main__":
    unittest.main()
