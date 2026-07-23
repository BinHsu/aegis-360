import math
import unittest

from aegis360.shot_render import greedy_trace_to_static_shots


class StaticShotTest(unittest.TestCase):
    def test_groups_ids_and_uses_seam_aware_robust_pose(self):
        def decision(time, candidate, yaw, pitch, fov):
            return {
                "timestamp": 10 + time,
                "selected_candidate_id": candidate,
                "candidates": [{
                    "candidate_id": candidate,
                    "yaw_radians": yaw,
                    "pitch_radians": pitch,
                    "h_fov_radians": fov,
                }],
            }

        trace = {"decisions": [
            decision(0, "seam", math.radians(179), 0.1, 1.5),
            decision(0.5, "seam", math.radians(-179), 0.2, 1.4),
            decision(1, "right", math.radians(90), -0.1, 1.2),
        ]}
        shots = greedy_trace_to_static_shots(trace, 2)
        self.assertEqual([(shot.start, shot.end) for shot in shots], [(0, 1), (1, 2)])
        self.assertEqual([shot.selected_candidate_id for shot in shots], ["seam", "right"])
        self.assertAlmostEqual(abs(math.degrees(shots[0].yaw)), 180, places=6)
        self.assertAlmostEqual(shots[0].pitch, 0.15)
        self.assertAlmostEqual(shots[0].h_fov, 1.45)

