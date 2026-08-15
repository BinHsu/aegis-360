from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.scene_change_candidates import build_scene_change_candidates


class SceneChangeCandidateTests(unittest.TestCase):
    def test_score_floor_and_temporal_nms_keep_strongest(self):
        source = {"schema_version": "aegis360.ffmpeg-scene-events.v1", "source_id": "fixture",
                  "events": [{"timestamp_seconds": 10, "scene_score": .5},
                             {"timestamp_seconds": 11, "scene_score": .8},
                             {"timestamp_seconds": 20, "scene_score": .3}],
                  "privacy": {"contains_pixels": False}}
        value = build_scene_change_candidates(source, scene_events_sha256="a" * 64)
        self.assertEqual(value["candidates"], [
            {"event_id": "event:scene-change:0000", "timestamp_seconds": 11,
             "scene_score": .8},
        ])

    def test_invalid_policy_fails(self):
        with self.assertRaises(ValueError):
            build_scene_change_candidates(
                {"schema_version": "wrong"}, scene_events_sha256="a" * 64,
            )


if __name__ == "__main__":
    unittest.main()
