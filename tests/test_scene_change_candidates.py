from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.scene_change_candidates import build_scene_change_candidates


class SceneChangeCandidateTests(unittest.TestCase):
    def test_default_removes_only_near_duplicate_and_keeps_nearby_cuts(self):
        source = {"schema_version": "aegis360.ffmpeg-scene-events.v1", "source_id": "fixture",
                  "events": [{"timestamp_seconds": 10, "scene_score": .5},
                             {"timestamp_seconds": 10.5, "scene_score": .8},
                             {"timestamp_seconds": 15.5, "scene_score": .3}],
                  "privacy": {"contains_pixels": False}}
        value = build_scene_change_candidates(source, scene_events_sha256="a" * 64)
        self.assertEqual(value["candidates"], [
            {"event_id": "event:scene-change:0000", "timestamp_seconds": 10.5,
             "scene_score": .8},
            {"event_id": "event:scene-change:0001", "timestamp_seconds": 15.5,
             "scene_score": .3},
        ])

    def test_explicit_wide_suppression_remains_available_for_diagnostics(self):
        source = {"schema_version": "aegis360.ffmpeg-scene-events.v1", "source_id": "fixture",
                  "events": [{"timestamp_seconds": 10, "scene_score": .5},
                             {"timestamp_seconds": 15, "scene_score": .8}],
                  "privacy": {"contains_pixels": False}}
        value = build_scene_change_candidates(
            source, scene_events_sha256="a" * 64, score_floor=.4,
            minimum_separation_seconds=10,
        )
        self.assertEqual([item["timestamp_seconds"] for item in value["candidates"]], [15])

    def test_multi_cadence_near_duplicate_keeps_strongest_but_retains_distant_cut(self):
        source = {"schema_version": "aegis360.ffmpeg-scene-event-pyramid.v1",
                  "source_id": "fixture",
                  "events": [{"timestamp_seconds": 10, "scene_score": .4, "sample_fps": 2},
                             {"timestamp_seconds": 10.1, "scene_score": .6, "sample_fps": 10},
                             {"timestamp_seconds": 15, "scene_score": .3, "sample_fps": 10}],
                  "privacy": {"contains_pixels": False}}
        value = build_scene_change_candidates(source, scene_events_sha256="a" * 64)
        self.assertEqual([item["timestamp_seconds"] for item in value["candidates"]],
                         [10.1, 15])

    def test_invalid_policy_fails(self):
        with self.assertRaises(ValueError):
            build_scene_change_candidates(
                {"schema_version": "wrong"}, scene_events_sha256="a" * 64,
            )


if __name__ == "__main__":
    unittest.main()
