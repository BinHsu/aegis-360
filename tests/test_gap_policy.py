from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.gap_policy import bridge_candidate_gaps, classify_gap_runs
from aegis360.so3 import rotation_distance_radians


def step(index, state):
    return {
        "previous_pts_seconds": index * 0.04,
        "current_pts_seconds": (index + 1) * 0.04,
        "state": state,
    }


def yaw(degrees):
    import math
    half = math.radians(degrees) / 2.0
    return [0.0, math.sin(half), 0.0, math.cos(half)]


class GapPolicyTests(unittest.TestCase):
    def test_boundary_gap_is_never_bridge_candidate(self):
        runs = classify_gap_runs(
            [step(0, "invalid"), step(1, "invalid"), step(2, "measured")],
            maximum_interior_gap_frames=3,
        )
        self.assertEqual(runs[0].classification, "unbridgeable")
        self.assertEqual(runs[0].frame_count, 2)

    def test_short_interior_gap_is_only_a_candidate(self):
        runs = classify_gap_runs(
            [
                step(0, "measured"), step(1, "invalid"),
                step(2, "invalid"), step(3, "measured"),
            ],
            maximum_interior_gap_frames=3,
        )
        self.assertEqual(runs[0].classification, "bridge_candidate")
        self.assertEqual(runs[0].start_pts_seconds, 0.04)
        self.assertEqual(runs[0].end_pts_seconds, 0.12)

    def test_long_or_trailing_gap_fails_closed(self):
        runs = classify_gap_runs(
            [
                step(0, "measured"), step(1, "invalid"),
                step(2, "invalid"), step(3, "invalid"),
                step(4, "invalid"), step(5, "measured"),
                step(6, "invalid"),
            ],
            maximum_interior_gap_frames=3,
        )
        self.assertEqual(
            [run.classification for run in runs],
            ["unbridgeable", "unbridgeable"],
        )

    def test_slerp_recovers_known_smooth_local_rotation_steps(self):
        steps = [
            {**step(0, "measured"), "rotation_xyzw": yaw(1.0)},
            {**step(1, "invalid"), "rotation_xyzw": None},
            {**step(2, "invalid"), "rotation_xyzw": None},
            {**step(3, "measured"), "rotation_xyzw": yaw(4.0)},
        ]
        bridged = bridge_candidate_gaps(
            steps, maximum_interior_gap_frames=3
        )
        self.assertEqual(
            [item["state"] for item in bridged],
            ["measured", "interpolated", "interpolated", "measured"],
        )
        self.assertLess(
            rotation_distance_radians(
                tuple(bridged[1]["rotation_xyzw"]), tuple(yaw(2.0))
            ),
            1e-6,
        )
        self.assertLess(
            rotation_distance_radians(
                tuple(bridged[2]["rotation_xyzw"]), tuple(yaw(3.0))
            ),
            1e-6,
        )

    def test_bridge_keeps_boundary_gap_null(self):
        steps = [
            {**step(0, "invalid"), "rotation_xyzw": None},
            {**step(1, "measured"), "rotation_xyzw": yaw(1.0)},
        ]
        bridged = bridge_candidate_gaps(
            steps, maximum_interior_gap_frames=3
        )
        self.assertEqual(bridged[0]["state"], "invalid")
        self.assertIsNone(bridged[0]["rotation_xyzw"])


if __name__ == "__main__":
    unittest.main()
