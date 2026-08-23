import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.story_segment_review_packet import build_story_segment_review_packet, validate_story_segment_review_packet


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def build_segment_packet_fixture():
    grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                   duration_seconds=30)
    grid_sha = digest(grid)
    timeline = {"schema_version": "aegis360.story-segment-timeline.v1",
                         "source_id": "fixture", "window": grid["window"],
                         "segments": [{"segment_id": "segment:story:0000",
                                       "start_seconds": 10.0, "end_seconds": 11.4,
                                       "left_boundary": None, "right_boundary": None}]}
    return grid, grid_sha, timeline


class StorySegmentReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.grid, self.grid_sha, self.timeline = build_segment_packet_fixture()

    def build(self):
        return build_story_segment_review_packet(
            self.timeline, self.grid, segment_id="segment:story:0000",
            segment_timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_short_segment_samples_remain_strictly_inside(self):
        value = self.build()
        timestamps = [item["timestamp_seconds"] for item in value["samples"]]
        self.assertEqual(timestamps, [10.28, 10.7, 11.12])
        self.assertTrue(all(10 < value < 11.4 for value in timestamps))
        self.assertEqual(value["sampling_policy"]["maximum_source_viewports"], 12)
        validate_story_segment_review_packet(
            value, self.timeline, self.grid,
            segment_timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_unknown_segment_and_grid_lineage_fail(self):
        with self.assertRaises(ValueError):
            build_story_segment_review_packet(
                self.timeline, self.grid, segment_id="missing",
                segment_timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
            )
        self.timeline["source_id"] = "other"
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
