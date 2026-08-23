import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.scene_boundary_story_packet import (build_scene_boundary_story_packet,
                                                   validate_scene_boundary_story_packet)
from aegis360.review_media import build_story_review_render_jobs
from tests.test_scene_story_packet import build_story_fixture, digest


class SceneBoundaryStoryPacketTests(unittest.TestCase):
    def setUp(self):
        self.grid, self.grid_sha, self.timeline = build_story_fixture()
        event = self.timeline["events"][0]
        event["signals"][0]["signal_id"] = "scene:s0"
        second = copy.deepcopy(event["signals"][0])
        second["signal_id"] = "scene:s1"
        second["evidence"]["timestamp_seconds"] = 12.0
        event["signals"].append(second)
        self.timeline_sha = digest(self.timeline)

    def build(self, signal_id="scene:s1"):
        return build_scene_boundary_story_packet(
            self.timeline, self.grid, event_id=self.timeline["events"][0]["event_id"],
            signal_id=signal_id, timeline_sha256=self.timeline_sha,
            grid_sha256=self.grid_sha,
        )

    def test_fused_event_is_scoped_to_one_exact_signal(self):
        value = self.build()
        self.assertEqual(value["signal_id"], "scene:s1")
        self.assertEqual(value["boundary"]["timestamp_seconds"], 12.0)
        self.assertEqual(len(value["samples"]), 6)
        self.assertEqual(value["samples"][2]["timestamp_seconds"], 11.75)
        self.assertEqual(value["samples"][3]["timestamp_seconds"], 12.25)
        self.assertEqual(len(build_story_review_render_jobs(value, self.grid)), 6)
        validate_scene_boundary_story_packet(
            value, self.timeline, self.grid, timeline_sha256=self.timeline_sha,
            grid_sha256=self.grid_sha,
        )

    def test_missing_wrong_type_and_mutation_fail(self):
        with self.assertRaises(ValueError):
            self.build("missing")
        broken = self.build()
        broken["signal_id"] = "scene:s0"
        with self.assertRaises(ValueError):
            validate_scene_boundary_story_packet(
                broken, self.timeline, self.grid, timeline_sha256=self.timeline_sha,
                grid_sha256=self.grid_sha,
            )


if __name__ == "__main__":
    unittest.main()
