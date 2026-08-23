from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.scene_event_pyramid import build_scene_event_pyramid


def source(fps, timestamp, score=.5):
    return {
        "schema_version": "aegis360.ffmpeg-scene-events.v1",
        "source_id": "fixture", "source_sha256": "f" * 64,
        "config": {"sample_fps": fps, "threshold": .25, "proxy_width": 320},
        "events": [{"timestamp_seconds": timestamp, "scene_score": score}],
        "privacy": {"contains_pixels": False},
    }


class SceneEventPyramidTests(unittest.TestCase):
    def test_preserves_distinct_cadence_evidence_and_provenance(self):
        value = build_scene_event_pyramid(
            [source(10, 168.4, .27), source(2, 222, .64)],
            sha256s=["a" * 64, "b" * 64],
        )
        self.assertEqual([event["timestamp_seconds"] for event in value["events"]],
                         [168.4, 222])
        self.assertEqual([item["sample_fps"] for item in value["inputs"]], [2, 10])

    def test_rejects_mismatched_source_and_duplicate_cadence(self):
        mismatch = source(2, 1)
        mismatch["source_id"] = "other"
        with self.assertRaises(ValueError):
            build_scene_event_pyramid([source(10, 1), mismatch],
                                      sha256s=["a" * 64, "b" * 64])
        with self.assertRaises(ValueError):
            build_scene_event_pyramid([source(2, 1), source(2, 2)],
                                      sha256s=["a" * 64, "b" * 64])


if __name__ == "__main__":
    unittest.main()
