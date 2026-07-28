import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.pre_review import static_shot_difference
from aegis360.shot_render import StaticShot


class PreReviewGateTests(unittest.TestCase):
    def test_rejects_renderer_collapsed_near_forward_shots(self):
        shots = (
            StaticShot(0, 3, "forward", 0, 0, math.radians(110)),
            StaticShot(3, 6.5, "group", math.radians(0.9),
                       math.radians(1.4), math.radians(110)),
            StaticShot(6.5, 30, "track", math.radians(2.3),
                       math.radians(1.3), math.radians(110)),
        )
        report = static_shot_difference(
            shots, baseline_h_fov=math.radians(110)
        )
        self.assertFalse(report["passed"])
        self.assertLess(report["maximum_change_degrees"], 3)

    def test_accepts_sustained_visible_pose_difference(self):
        shots = (
            StaticShot(0, 3, "forward", 0, 0, math.radians(110)),
            StaticShot(3, 8, "subject", math.radians(20), 0,
                       math.radians(110)),
        )
        report = static_shot_difference(
            shots, baseline_h_fov=math.radians(110)
        )
        self.assertTrue(report["passed"])
        self.assertEqual(report["distinct_seconds"], 5)


if __name__ == "__main__":
    unittest.main()
