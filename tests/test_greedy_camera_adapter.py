import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.camera_path import (  # noqa: E402
    camera_path_document_to_keyframes,
    greedy_trace_to_camera_path,
    greedy_trace_to_keyframes,
    interpolate_path,
)
from aegis360.framing import FramingSafetyConfig  # noqa: E402


def decision(timestamp, candidate_id, yaw, pitch=0.0, h_fov=90.0):
    return {
        "timestamp": timestamp,
        "selected_candidate_id": candidate_id,
        "candidates": [
            {
                "candidate_id": candidate_id,
                "yaw_radians": math.radians(yaw),
                "pitch_radians": math.radians(pitch),
                "h_fov_radians": math.radians(h_fov),
            }
        ],
    }


class GreedyCameraAdapterTests(unittest.TestCase):
    def test_rebases_time_and_fills_clip_endpoints(self):
        trace = {
            "decisions": [
                decision(12.5, "a", 10),
                decision(13.0, "a", 11),
                decision(14.0, "a", 12),
            ]
        }
        path = greedy_trace_to_keyframes(
            trace, duration=3.0, direction_threshold=math.radians(5)
        )
        self.assertEqual([frame.time for frame in path], [0.0, 3.0])
        self.assertAlmostEqual(math.degrees(path[0].yaw), 10)
        self.assertAlmostEqual(math.degrees(path[-1].yaw), 12)

    def test_emits_only_id_switches_or_direction_threshold_crossings(self):
        trace = {
            "decisions": [
                decision(0.0, "a", 0),
                decision(0.5, "a", 2),
                decision(1.0, "a", 6),
                decision(1.5, "b", 6),
                decision(2.0, "b", 7),
            ]
        }
        path = greedy_trace_to_keyframes(
            trace, duration=3.0, direction_threshold=math.radians(5)
        )
        self.assertEqual([frame.time for frame in path], [0.0, 1.0, 1.5, 3.0])

    def test_last_decision_switch_is_not_delayed_to_clip_endpoint(self):
        trace = {
            "decisions": [
                decision(4.0, "a", 0),
                decision(5.0, "b", 30),
            ]
        }
        path = greedy_trace_to_keyframes(trace, duration=2.0)
        self.assertEqual([frame.time for frame in path], [0.0, 1.0, 2.0])
        self.assertAlmostEqual(path[1].yaw, path[2].yaw)

    def test_existing_interpolator_takes_short_seam_path(self):
        trace = {
            "decisions": [
                decision(20.0, "a", 179),
                decision(21.0, "b", -179),
            ]
        }
        samples = interpolate_path(greedy_trace_to_keyframes(trace, 1.0), fps=4)
        yaws = [math.degrees(sample.yaw) for sample in samples]
        self.assertEqual(len(samples), 5)
        self.assertTrue(all(179 <= yaw <= 181 for yaw in yaws))
        self.assertTrue(all(a <= b for a, b in zip(yaws, yaws[1:])))

    def test_framing_safety_is_applied_before_sparse_keyframe_selection(self):
        trace = {"decisions": [
            decision(0.0, "a", 0, h_fov=130),
            decision(0.5, "a", 1, h_fov=50),
            decision(1.0, "b", 20, h_fov=50),
        ]}
        safety = FramingSafetyConfig(
            minimum_h_fov=math.radians(100),
            candidate_extent_padding=math.radians(5),
            max_zoom_in_change=math.radians(15),
        )
        path = greedy_trace_to_keyframes(
            trace, duration=1.0, framing_safety=safety
        )
        self.assertEqual(
            [round(math.degrees(frame.h_fov)) for frame in path],
            [140, 110],
        )

    def test_json_contract_round_trips_to_existing_camera_path(self):
        trace = {"decisions": [decision(8.0, "subject-1", 15)]}
        document = greedy_trace_to_camera_path(trace, duration=2.0)
        self.assertEqual(document["schema_version"], "aegis360.camera-path.v1")
        self.assertEqual(document["coordinate_units"], "radians")
        self.assertEqual(
            [row["timestamp"] for row in document["keyframes"]], [0.0, 2.0]
        )
        self.assertEqual(
            document["keyframes"][0]["selected_candidate_id"], "subject-1"
        )
        loaded = camera_path_document_to_keyframes(document)
        self.assertEqual([frame.time for frame in loaded], [0.0, 2.0])

    def test_rejects_decisions_beyond_duration_and_missing_geometry(self):
        with self.assertRaises(ValueError):
            greedy_trace_to_keyframes(
                {"decisions": [decision(0, "a", 0), decision(2, "a", 0)]},
                duration=1,
            )
        bad = decision(0, "a", 0)
        bad["candidates"] = []
        with self.assertRaises(ValueError):
            greedy_trace_to_keyframes({"decisions": [bad]}, duration=1)


if __name__ == "__main__":
    unittest.main()
