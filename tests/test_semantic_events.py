import json
import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_events import (
    build_semantic_event_artifact,
    dumps_semantic_event_artifact,
)


class SemanticEventArtifactTests(unittest.TestCase):
    def setUp(self):
        self.viewports = (
            {
                "viewport_id": "front",
                "yaw_radians": 0,
                "pitch_radians": 0,
                "horizontal_fov_radians": math.radians(100),
                "width_pixels": 416,
                "height_pixels": 416,
            },
            {
                "viewport_id": "left",
                "yaw_radians": -math.pi / 2,
                "pitch_radians": 0,
                "horizontal_fov_radians": math.radians(100),
                "width_pixels": 416,
                "height_pixels": 416,
            },
        )
        self.events = (
            {"timestamp_seconds": 1, "viewport_id": "left", "detections": []},
            {
                "timestamp_seconds": 0,
                "viewport_id": "front",
                "detections": [{
                    "class_name": "bicycle",
                    "score": .75,
                    "source_index": 4,
                    "box_top_left_normalized": [.1, .2, .3, .4],
                }],
            },
        )

    def test_artifact_is_deterministic_path_free_and_keeps_score_noneditorial(self):
        document = build_semantic_event_artifact(
            source_id="synthetic-clip",
            model_id="detector-v1",
            viewports=reversed(self.viewports),
            events=reversed(self.events),
        )
        self.assertEqual(
            [row["viewport_id"] for row in document["viewports"]],
            ["front", "left"],
        )
        self.assertEqual(document["events"][0]["timestamp_seconds"], 0)
        self.assertEqual(document["viewports"][0]["width_pixels"], 416)
        detection = document["events"][0]["detections"][0]
        self.assertEqual(detection["score_role"], "perception_evidence_only")
        serialized = dumps_semantic_event_artifact(document)
        self.assertNotIn("/Users/", serialized)
        self.assertEqual(json.loads(serialized), document)

    def test_paths_duplicates_unknown_views_and_bad_boxes_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "path-free"):
            build_semantic_event_artifact(
                source_id="/private/source", model_id="detector",
                viewports=self.viewports, events=self.events,
            )
        duplicate = (self.events[0], dict(self.events[0]))
        with self.assertRaisesRegex(ValueError, "unique"):
            build_semantic_event_artifact(
                source_id="source", model_id="detector",
                viewports=self.viewports, events=duplicate,
            )
        unknown = (dict(self.events[0], viewport_id="back"),)
        with self.assertRaisesRegex(ValueError, "reference"):
            build_semantic_event_artifact(
                source_id="source", model_id="detector",
                viewports=self.viewports, events=unknown,
            )
        bad = dict(self.events[1])
        bad["detections"] = [dict(
            self.events[1]["detections"][0],
            box_top_left_normalized=[.9, .2, .3, .4],
        )]
        with self.assertRaisesRegex(ValueError, "inside"):
            build_semantic_event_artifact(
                source_id="source", model_id="detector",
                viewports=self.viewports, events=(bad,),
            )

    def test_only_person_and_bicycle_are_allowed(self):
        bad = dict(self.events[1])
        bad["detections"] = [dict(
            self.events[1]["detections"][0], class_name="bird"
        )]
        with self.assertRaisesRegex(ValueError, "person/bicycle"):
            build_semantic_event_artifact(
                source_id="source", model_id="detector",
                viewports=self.viewports, events=(bad,),
            )


if __name__ == "__main__":
    unittest.main()
