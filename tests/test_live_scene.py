import copy
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.live_scene import build_live_scene_intervals, validate_live_scene_intervals
from aegis360.semantic_events import build_semantic_event_artifact


def semantic(person_timestamps):
    return build_semantic_event_artifact(
        source_id="fixture", model_id="fixture-model",
        viewports=[{"viewport_id":"front","yaw_radians":0,"pitch_radians":0,
                    "horizontal_fov_radians":math.pi/2,"width_pixels":100,"height_pixels":100}],
        events=[{"timestamp_seconds":timestamp,"viewport_id":"front","detections":([
            {"class_name":"person","score":.8,"source_index":0,
             "box_top_left_normalized":[.1,.1,.2,.3]}
        ] if timestamp in person_timestamps else [])} for timestamp in (0,.25,.5,.75,1,1.25,1.5,1.75,2)],
    )


class LiveSceneTests(unittest.TestCase):
    def test_merges_bounded_detector_gaps_without_role_claim(self):
        result = build_live_scene_intervals(semantic({.25,.5,1.75,2}), maximum_gap_seconds=1.5)
        validate_live_scene_intervals(result)
        self.assertEqual(result["intervals"], [{"start_seconds":.25,"end_seconds":2.25,"supporting_timestamp_count":4}])
        self.assertEqual(result["policy"]["status"], "broad_person_presence_not_role_or_identity")

    def test_requires_canonical_semantic_input(self):
        value = semantic({0,.25}); value["invented"] = True
        with self.assertRaises(ValueError): build_live_scene_intervals(value)

    def test_sparse_singletons_fail_closed(self):
        result = build_live_scene_intervals(semantic({0,2}), maximum_gap_seconds=.5)
        self.assertEqual(result["intervals"], [])


if __name__ == "__main__": unittest.main()
