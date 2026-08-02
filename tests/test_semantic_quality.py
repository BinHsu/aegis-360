import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_events import build_semantic_event_artifact
from aegis360.semantic_quality import (
    SubjectFramingQualityPolicy, filter_subject_framing_events,
)


def document(width, height):
    return build_semantic_event_artifact(
        source_id="fixture", model_id="model",
        viewports=({
            "viewport_id": "front", "yaw_radians": 0,
            "pitch_radians": 0, "horizontal_fov_radians": math.pi / 2,
            "width_pixels": 100, "height_pixels": 100,
        },),
        events=({
            "timestamp_seconds": 0, "viewport_id": "front",
            "detections": [{
                "class_name": "person", "score": .8, "source_index": 1,
                "box_top_left_normalized": [0, 0, width, height],
            }],
        },),
    )


class SemanticQualityTests(unittest.TestCase):
    def test_boundary_is_quarantined_and_policy_is_tunable(self):
        accepted, report = filter_subject_framing_events(document(.9, .89))
        self.assertEqual(accepted["events"][0]["detections"], [])
        self.assertEqual(report["quarantined_detection_count"], 1)
        self.assertEqual(
            report["policy"]["classification"],
            "unsuitable_for_subject_framing_not_detector_false_positive",
        )
        accepted, _ = filter_subject_framing_events(
            document(.9, .89), SubjectFramingQualityPolicy(.95, .95)
        )
        self.assertEqual(len(accepted["events"][0]["detections"]), 1)

    def test_input_is_not_mutated_and_report_is_path_free(self):
        source = document(.2, .3)
        accepted, report = filter_subject_framing_events(source)
        self.assertIsNot(accepted, source)
        self.assertEqual(len(source["events"][0]["detections"]), 1)
        self.assertEqual(report["accepted_detection_count"], 1)
        self.assertFalse(report["privacy"]["contains_source_path"])

    def test_invalid_policy_and_old_schema_fail_closed(self):
        with self.assertRaises(ValueError):
            SubjectFramingQualityPolicy(0, .9)
        old = dict(document(.2, .3), schema_version="old")
        with self.assertRaisesRegex(ValueError, "schema"):
            filter_subject_framing_events(old)


if __name__ == "__main__":
    unittest.main()
