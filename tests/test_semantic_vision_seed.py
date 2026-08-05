import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_events import build_semantic_event_artifact
from aegis360.semantic_vision_seed import build_vision_seed_manifest


class SemanticVisionSeedTests(unittest.TestCase):
    def setUp(self):
        self.events = build_semantic_event_artifact(
            source_id="fixture", model_id="model",
            viewports=({
                "viewport_id": "up", "yaw_radians": .1,
                "pitch_radians": math.radians(60),
                "horizontal_fov_radians": math.radians(100),
                "width_pixels": 416, "height_pixels": 416,
            },), events=(),
        )
        provenance = (
            '{"box_top_left_normalized":[0.2,0.3,0.2,0.4],'
            '"class_name":"person","source_index":3,"viewport_id":"up"}'
        )
        self.tracklets = {
            "schema_version": "aegis360.semantic-tracklet-report.v1",
            "tracklets": {"acquisitions": [{
                "track_id": "semantic-track:000001", "class_name": "person",
                "acquired_at": 2.5,
                "acquisition_observation_provenance": [provenance],
            }]},
        }

    def test_manifest_converts_box_and_preserves_nonzero_pitch(self):
        result = build_vision_seed_manifest(
            self.events, self.tracklets, track_id="semantic-track:000001",
            duration_seconds=4, sample_fps=4,
        )
        self.assertAlmostEqual(result["viewport"]["pitch_degrees"], 60)
        self.assertAlmostEqual(
            result["initial_box_vision_bottom_left_normalized"]["y"], .3
        )
        self.assertFalse(result["selection"]["identity_verified"])
        self.assertFalse(result["privacy"]["contains_source_path"])

    def test_duplicate_views_choose_smallest_box_deterministically(self):
        acquisition = self.tracklets["tracklets"]["acquisitions"][0]
        acquisition["acquisition_observation_provenance"] = [
            acquisition["acquisition_observation_provenance"][0],
            '{"box_top_left_normalized":[0.1,0.1,0.1,0.2],'
            '"class_name":"person","source_index":2,"viewport_id":"up"}',
        ]
        result = build_vision_seed_manifest(
            self.events, self.tracklets, track_id="semantic-track:000001",
            duration_seconds=1, sample_fps=2,
        )
        self.assertEqual(result["selection"]["selected_source_index"], 2)
        self.assertEqual(result["selection"]["eligible_observation_count"], 2)

    def test_missing_track_and_old_schema_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "exactly one"):
            build_vision_seed_manifest(
                self.events, self.tracklets, track_id="missing",
                duration_seconds=1, sample_fps=1,
            )
        old = dict(self.events, schema_version="old")
        with self.assertRaisesRegex(ValueError, "event schema"):
            build_vision_seed_manifest(
                old, self.tracklets, track_id="semantic-track:000001",
                duration_seconds=1, sample_fps=1,
            )


if __name__ == "__main__":
    unittest.main()
