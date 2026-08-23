import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.story_segment_timeline import build_story_segment_timeline, validate_story_segment_timeline


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def timeline_fixture():
    return {"schema_version": "aegis360.event-timeline.v2", "source_id": "fixture",
            "window": {"start_seconds": 0, "duration_seconds": 30},
            "events": [
                {"event_id": "e0", "signals": [
                    {"signal_id": "s0", "signal_type": "scene_change",
                     "evidence": {"timestamp_seconds": 10}}]},
                {"event_id": "e1", "signals": [
                    {"signal_id": "s1", "signal_type": "scene_change",
                     "evidence": {"timestamp_seconds": 20}}]},
            ]}


class StorySegmentTimelineTests(unittest.TestCase):
    def test_partitions_window_and_binds_both_sides(self):
        timeline = timeline_fixture()
        value = build_story_segment_timeline(timeline, timeline_sha256=digest(timeline))
        self.assertEqual([(item["start_seconds"], item["end_seconds"])
                          for item in value["segments"]], [(0, 10), (10, 20), (20, 30)])
        self.assertIsNone(value["segments"][0]["left_boundary"])
        self.assertEqual(value["segments"][1]["left_boundary"]["event_id"], "e0")
        self.assertEqual(value["segments"][1]["right_boundary"]["event_id"], "e1")
        validate_story_segment_timeline(value, timeline, timeline_sha256=digest(timeline))

    def test_duplicate_outside_and_mutation_fail(self):
        for timestamp in (0, 30):
            timeline = timeline_fixture()
            timeline["events"][0]["signals"][0]["evidence"]["timestamp_seconds"] = timestamp
            with self.assertRaises(ValueError):
                build_story_segment_timeline(timeline, timeline_sha256=digest(timeline))
        timeline = timeline_fixture()
        timeline["events"][1]["signals"][0]["evidence"]["timestamp_seconds"] = 10
        with self.assertRaises(ValueError):
            build_story_segment_timeline(timeline, timeline_sha256=digest(timeline))


if __name__ == "__main__":
    unittest.main()
