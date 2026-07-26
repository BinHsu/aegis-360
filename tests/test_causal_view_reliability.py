import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.causal_view_reliability import CausalViewReliability


def yaw(degrees):
    half = math.radians(degrees) / 2.0
    return (0.0, math.sin(half), 0.0, math.cos(half))


class CausalViewReliabilityTests(unittest.TestCase):
    IDS = ["front", "right", "back", "left", "up", "down"]

    def test_current_corruption_cannot_change_current_selection(self):
        selector = CausalViewReliability(
            self.IDS, selected_viewport_count=4, update_alpha=0.2
        )
        self.assertEqual(
            selector.select_for_current_pair(), tuple(sorted(self.IDS))
        )
        selector.observe_completed_pair({
            viewport_id: yaw(8.0 if viewport_id == "down" else 1.0)
            for viewport_id in self.IDS
        })
        self.assertNotIn("down", selector.select_for_current_pair())

    def test_reliability_updates_smoothly_and_deterministically(self):
        selector = CausalViewReliability(
            self.IDS, selected_viewport_count=4, update_alpha=0.25
        )
        first = {
            viewport_id: yaw(5.0 if viewport_id == "back" else 0.0)
            for viewport_id in self.IDS
        }
        selector.observe_completed_pair(first)
        first_score = selector.scores_radians["back"]
        selector.observe_completed_pair({
            viewport_id: yaw(0.0) for viewport_id in self.IDS
        })
        self.assertAlmostEqual(
            selector.scores_radians["back"], first_score * 0.75
        )
        self.assertNotIn("back", selector.select_for_current_pair())

    def test_invalid_configuration_fails_closed(self):
        with self.assertRaises(ValueError):
            CausalViewReliability(
                self.IDS, selected_viewport_count=0, update_alpha=0.2
            )
        with self.assertRaises(ValueError):
            CausalViewReliability(
                self.IDS, selected_viewport_count=4, update_alpha=0.0
            )


if __name__ == "__main__":
    unittest.main()
