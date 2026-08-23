import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.scene_story_packet import build_scene_story_packet, validate_scene_story_packet


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def build_story_fixture():
    grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                   duration_seconds=100)
    grid_sha = digest(grid)
    ids = [item["candidate_id"] for item in grid["candidates"]]
    timeline = {
            "schema_version": "aegis360.event-timeline.v2", "source_id": "fixture",
            "window": grid["window"],
            "inputs": {"context_view_grid_sha256": grid_sha},
            "events": [
                {"event_id": "event:multi:0000", "start_seconds": 38.0,
                 "end_seconds": 42.0,
                 "signals": [{"signal_type": "scene_change", "evidence": {"timestamp_seconds": 40.0}}],
                 "review_scope": {"mode": "all_declared_candidates", "candidate_ids": ids}},
                {"event_id": "event:multi:0001", "start_seconds": 48.0,
                 "end_seconds": 52.0,
                 "signals": [{"signal_type": "scene_change", "evidence": {"timestamp_seconds": 50.0}}],
                 "review_scope": {"mode": "all_declared_candidates", "candidate_ids": ids}},
                {"event_id": "event:multi:0002", "start_seconds": 58.0,
                 "end_seconds": 62.0,
                 "signals": [{"signal_type": "scene_change", "evidence": {"timestamp_seconds": 60.0}}],
                 "review_scope": {"mode": "all_declared_candidates", "candidate_ids": ids}},
            ],
    }
    return grid, grid_sha, timeline


class SceneStoryPacketTests(unittest.TestCase):
    def setUp(self):
        self.grid, self.grid_sha, self.timeline = build_story_fixture()

    def build(self):
        return build_scene_story_packet(
            self.timeline, self.grid, event_id="event:multi:0001",
            timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_six_composites_cover_boundary_and_local_context(self):
        value = self.build()
        self.assertEqual([item["timestamp_seconds"] for item in value["samples"]],
                         [35.0, 47.0, 49.75, 50.25, 53.0, 65.0])
        self.assertEqual({item["representation"] for item in value["samples"]},
                         {"four_cardinal_contact_sheet"})
        self.assertEqual(value["whole_video_context"]["event_position_fraction"], .5)
        self.assertEqual([item["relation"] for item in value["whole_video_context"]["neighbors"]],
                         ["previous", "next"])
        validate_scene_story_packet(
            value, self.timeline, self.grid,
            timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_role_scoped_event_and_mutated_policy_fail(self):
        self.timeline["events"][1]["review_scope"] = {
            "mode": "current_and_available_proposed",
        }
        with self.assertRaises(ValueError):
            self.build()

    def test_boundary_clipping_deduplicates_samples(self):
        event = self.timeline["events"][0]
        event["start_seconds"] = 0
        event["end_seconds"] = 2
        event["signals"][0]["evidence"]["timestamp_seconds"] = .1
        value = build_scene_story_packet(
            self.timeline, self.grid, event_id="event:multi:0000",
            timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )
        self.assertLessEqual(len(value["samples"]), 6)
        self.assertEqual(value["samples"][0]["timestamp_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
