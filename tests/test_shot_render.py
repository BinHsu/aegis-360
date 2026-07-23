import math
import unittest

from aegis360.shot_render import greedy_trace_to_static_shots
from aegis360.framing import FramingSafetyConfig


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

    def test_framing_guards_apply_padding_minimum_and_per_shot_zoom_limit(self):
        def decision(time, candidate, fov):
            return {
                "timestamp": time,
                "selected_candidate_id": candidate,
                "candidates": [{
                    "candidate_id": candidate,
                    "yaw_radians": 0,
                    "pitch_radians": 0,
                    "h_fov_radians": math.radians(fov),
                }],
            }

        trace = {"decisions": [
            decision(0, "wide", 130),
            decision(1, "tight", 60),
            decision(2, "tightest", 20),
        ]}
        config = FramingSafetyConfig(
            minimum_h_fov=math.radians(100),
            candidate_extent_padding=math.radians(5),
            max_zoom_in_change=math.radians(15),
        )
        shots = greedy_trace_to_static_shots(trace, 3, config)
        self.assertEqual(
            [round(math.degrees(shot.h_fov)) for shot in shots],
            [140, 125, 110],
        )
