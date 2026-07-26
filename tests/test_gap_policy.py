from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.gap_policy import classify_gap_runs


def step(index, state):
    return {
        "previous_pts_seconds": index * 0.04,
        "current_pts_seconds": (index + 1) * 0.04,
        "state": state,
    }


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


if __name__ == "__main__":
    unittest.main()
