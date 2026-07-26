import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.view_consensus import select_rotation_consensus


def yaw(degrees):
    half = math.radians(degrees) / 2.0
    return (0.0, math.sin(half), 0.0, math.cos(half))


class ViewConsensusTests(unittest.TestCase):
    def test_rejects_one_corrupted_view_without_outcome_oracle(self):
        result = select_rotation_consensus(
            {
                "front": yaw(1.00),
                "right": yaw(1.03),
                "back": yaw(0.98),
                "left": yaw(1.01),
                "up": yaw(0.97),
                "down": yaw(8.0),
            },
            maximum_disagreement_radians=math.radians(0.25),
            minimum_viewports=4,
        )
        self.assertEqual(result.state, "selected")
        self.assertEqual(result.selected_viewport_ids, (
            "back", "front", "left", "right", "up"
        ))
        self.assertEqual(result.rejected_viewport_ids, ("down",))

    def test_split_evidence_fails_closed(self):
        result = select_rotation_consensus(
            {
                "a": yaw(0.0), "b": yaw(0.1), "c": yaw(0.2),
                "d": yaw(5.0), "e": yaw(5.1), "f": yaw(5.2),
            },
            maximum_disagreement_radians=math.radians(0.5),
            minimum_viewports=4,
        )
        self.assertEqual(result.state, "invalid")
        self.assertEqual(
            result.failure_reason, "insufficient_view_consensus"
        )

    def test_tie_break_and_validation_are_deterministic(self):
        result = select_rotation_consensus(
            {"z": yaw(1.0), "a": yaw(-1.0)},
            maximum_disagreement_radians=math.radians(3.0),
            minimum_viewports=2,
        )
        self.assertEqual(result.medoid_viewport_id, "a")
        with self.assertRaises(ValueError):
            select_rotation_consensus(
                {}, maximum_disagreement_radians=1.0, minimum_viewports=1
            )


if __name__ == "__main__":
    unittest.main()
