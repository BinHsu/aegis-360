import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.multi_signal_timeline import build_multi_signal_timeline, validate_multi_signal_timeline


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class MultiSignalTimelineTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=30)
        self.grid_sha = digest(self.grid)
        self.scenes = {"schema_version": "aegis360.scene-change-candidates.v1",
                       "source_id": "fixture", "candidates": [
                           {"event_id": "scene:0", "timestamp_seconds": 10, "scene_score": .8},
                           {"event_id": "scene:1", "timestamp_seconds": 13, "scene_score": .7},
                       ]}

    def build(self, reaction=None):
        return build_multi_signal_timeline(
            self.grid, self.scenes, grid_sha256=self.grid_sha,
            scene_candidates_sha256=digest(self.scenes), reaction_timeline=reaction,
            reaction_timeline_sha256=None if reaction is None else digest(reaction),
        )

    def test_overlapping_scene_windows_fuse_and_keep_neutral_scope(self):
        value = self.build()
        self.assertEqual(len(value["events"]), 1)
        event = value["events"][0]
        self.assertEqual((event["start_seconds"], event["end_seconds"]), (8.0, 15.0))
        self.assertEqual(event["review_scope"]["mode"], "all_declared_candidates")
        self.assertEqual(len(event["review_scope"]["candidate_ids"]), 4)
        validate_multi_signal_timeline(
            value, self.grid, self.scenes, grid_sha256=self.grid_sha,
            scene_candidates_sha256=digest(self.scenes),
        )

    def test_overlapping_reaction_does_not_invent_scene_role(self):
        reaction = {"schema_version": "aegis360.event-timeline.v1", "source_id": "fixture",
                    "window": self.grid["window"], "events": [{
                        "event_id": "reaction:0", "start_seconds": 9, "end_seconds": 12,
                        "audio_evidence": {"support": 3}, "view_context": {
                            "current_candidate_id": "context:cardinal:0",
                            "proposed_candidate_id": "context:cardinal:1",
                            "proposed_available_intervals": [{"start_seconds": 9, "end_seconds": 12}],
                        }}]}
        event = self.build(reaction)["events"][0]
        self.assertEqual(event["review_scope"]["mode"], "all_declared_candidates")
        self.assertEqual({signal["signal_type"] for signal in event["signals"]}, {"scene_change", "reaction_candidate"})

    def test_out_of_window_scene_fails(self):
        self.scenes["candidates"][0]["timestamp_seconds"] = 31
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
