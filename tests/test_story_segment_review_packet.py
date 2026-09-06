import hashlib
import json
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.story_segment_review_packet import build_story_segment_review_packet, validate_story_segment_review_packet
from aegis360.typed_story_segment_timeline import build_typed_story_segment_timeline
from tests.test_typed_segment_boundaries import TypedSegmentBoundaryTests


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

    def test_legacy_v1_shape_and_rebuild_are_unchanged(self):
        value = self.build()
        self.assertEqual(value["schema_version"],
                         "aegis360.story-segment-review-packet.v1")
        self.assertEqual(set(value["inputs"]), {
            "story_segment_timeline_sha256", "context_view_grid_sha256"})
        self.assertEqual(digest(value),
                         "96536c2e6e68afccb4c075e7f1cf0ee8329de20d03360bc1948cfa6e8c85ecca")
        self.assertEqual(value, self.build())

    def test_typed_zero_boundary_timeline_emits_packet_v2(self):
        fixture = TypedSegmentBoundaryTests()
        fixture.setUp()
        boundaries = fixture.build()
        row = boundaries["boundaries"][0]
        row["disposition"] = "rejected"
        row["effective_timestamp_seconds"] = None
        row["typed_labels"] = {
            "classification": "no_semantic_change", "structural_role": "unknown",
            "change_type": "unknown", "narrative_function": "unknown",
            "viewer_value": "unknown"}
        boundaries["boundary_authority"]["authorized_boundary_count"] = 0
        typed = build_typed_story_segment_timeline(
            fixture.grid, boundaries, grid_sha256=digest(fixture.grid),
            boundaries_sha256=digest(boundaries))
        value = build_story_segment_review_packet(
            typed, fixture.grid, segment_id="segment:typed-story:0000",
            segment_timeline_sha256=digest(typed), grid_sha256=digest(fixture.grid))
        self.assertEqual(value["schema_version"],
                         "aegis360.story-segment-review-packet.v2")
        self.assertEqual(set(value["inputs"]), {
            "typed_story_segment_timeline_sha256", "context_view_grid_sha256"})
        self.assertEqual(len(value["samples"]), 3)
        self.assertTrue(all(typed["segments"][0]["start_seconds"] < sample["timestamp_seconds"]
                            < typed["segments"][0]["end_seconds"]
                            for sample in value["samples"]))
        validate_story_segment_review_packet(
            value, typed, fixture.grid, segment_timeline_sha256=digest(typed),
            grid_sha256=digest(fixture.grid))
        tampered = copy.deepcopy(value)
        tampered["schema_version"] = "aegis360.story-segment-review-packet.v1"
        with self.assertRaises(ValueError):
            validate_story_segment_review_packet(
                tampered, typed, fixture.grid, segment_timeline_sha256=digest(typed),
                grid_sha256=digest(fixture.grid))
        wrong_grid = copy.deepcopy(typed)
        wrong_grid["inputs"]["context_view_grid_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            build_story_segment_review_packet(
                wrong_grid, fixture.grid, segment_id="segment:typed-story:0000",
                segment_timeline_sha256=digest(wrong_grid),
                grid_sha256=digest(fixture.grid))

    def test_arbitrary_timeline_schema_is_rejected(self):
        broken = copy.deepcopy(self.timeline)
        broken["schema_version"] = "aegis360.story-segment-timeline.v999"
        with self.assertRaises(ValueError):
            build_story_segment_review_packet(
                broken, self.grid, segment_id="segment:story:0000",
                segment_timeline_sha256=digest(broken), grid_sha256=self.grid_sha)

    def test_cli_emits_v2_for_typed_timeline(self):
        fixture = TypedSegmentBoundaryTests()
        fixture.setUp()
        boundaries = fixture.build()
        row = boundaries["boundaries"][0]
        row["disposition"] = "rejected"
        row["effective_timestamp_seconds"] = None
        row["typed_labels"] = {
            "classification": "no_semantic_change", "structural_role": "unknown",
            "change_type": "unknown", "narrative_function": "unknown",
            "viewer_value": "unknown"}
        boundaries["boundary_authority"]["authorized_boundary_count"] = 0
        typed = build_typed_story_segment_timeline(
            fixture.grid, boundaries, grid_sha256=digest(fixture.grid),
            boundaries_sha256=digest(boundaries))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            timeline_path, grid_path = root / "timeline.json", root / "grid.json"
            output_path = root / "packet.json"
            timeline_path.write_text(json.dumps(typed, sort_keys=True))
            grid_path.write_text(json.dumps(fixture.grid, sort_keys=True))
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/build_story_segment_review_packet.py"),
                str(timeline_path), str(grid_path), "segment:typed-story:0000",
                str(output_path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output_path.read_text())["schema_version"],
                             "aegis360.story-segment-review-packet.v2")


if __name__ == "__main__":
    unittest.main()
