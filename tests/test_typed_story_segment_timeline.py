import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.typed_story_segment_timeline import (
    build_typed_story_segment_timeline, validate_typed_story_segment_timeline,
)
from tests.test_typed_segment_boundaries import TypedSegmentBoundaryTests, digest


class TypedStorySegmentTimelineTests(unittest.TestCase):
    def setUp(self):
        fixture = TypedSegmentBoundaryTests()
        fixture.setUp()
        self.grid = fixture.grid
        self.authorized = fixture.build()

    def build(self, boundaries=None, grid=None, grid_sha=None):
        boundaries = self.authorized if boundaries is None else boundaries
        grid = self.grid if grid is None else grid
        return build_typed_story_segment_timeline(
            grid, boundaries, grid_sha256=digest(grid) if grid_sha is None else grid_sha,
            boundaries_sha256=digest(boundaries))

    def test_zero_authorized_is_one_full_window_segment(self):
        value = copy.deepcopy(self.authorized)
        row = value["boundaries"][0]
        row["disposition"] = "rejected"
        row["effective_timestamp_seconds"] = None
        row["typed_labels"] = {"classification": "no_semantic_change",
                               "structural_role": "unknown", "change_type": "unknown",
                               "narrative_function": "unknown", "viewer_value": "unknown"}
        value["boundary_authority"]["authorized_boundary_count"] = 0
        timeline = self.build(value)
        self.assertEqual(len(timeline["segments"]), 1)
        self.assertEqual((timeline["segments"][0]["start_seconds"],
                          timeline["segments"][0]["end_seconds"]), (385.0, 387.0))
        self.assertIsNone(timeline["segments"][0]["left_boundary"])
        self.assertIsNone(timeline["segments"][0]["right_boundary"])

    def test_authorized_boundary_splits_and_preserves_typed_origin(self):
        timeline = self.build()
        self.assertEqual(len(timeline["segments"]), 2)
        boundary = timeline["segments"][0]["right_boundary"]
        self.assertEqual(boundary["origin"], "typed_continuous_onset")
        self.assertEqual(boundary, timeline["segments"][1]["left_boundary"])
        self.assertEqual(boundary["effective_timestamp_seconds"], 385.75)
        validate_typed_story_segment_timeline(
            timeline, self.grid, self.authorized, grid_sha256=digest(self.grid),
            boundaries_sha256=digest(self.authorized))

    def test_mixed_rejected_and_abstained_rows_do_not_split(self):
        mixed = copy.deepcopy(self.authorized)
        base = mixed["boundaries"][0]
        for index, disposition in enumerate(("rejected", "abstained"), start=1):
            row = copy.deepcopy(base)
            row["candidate_id"] = f"continuous-onset:{index:04d}"
            row["disposition"] = disposition
            row["effective_timestamp_seconds"] = None
            row["typed_labels"] = {
                "classification": ("no_semantic_change" if disposition == "rejected"
                                   else "unknown"),
                "structural_role": "unknown", "change_type": "unknown",
                "narrative_function": "unknown", "viewer_value": "unknown"}
            mixed["boundaries"].append(row)
        timeline = self.build(mixed)
        self.assertEqual(len(timeline["segments"]), 2)

    def test_tamper_order_duplicate_source_window_and_hash_fail(self):
        duplicate = copy.deepcopy(self.authorized)
        duplicate["boundaries"].append(copy.deepcopy(duplicate["boundaries"][0]))
        duplicate["boundary_authority"]["authorized_boundary_count"] = 2
        with self.assertRaises(ValueError):
            self.build(duplicate)
        ordered = copy.deepcopy(self.authorized)
        second = copy.deepcopy(ordered["boundaries"][0])
        second["candidate_id"] = "continuous-onset:0001"
        second["effective_timestamp_seconds"] = 385.5
        second["uncertainty_interval"]["end_seconds"] = 385.5
        second["support_interval"]["start_seconds"] = 385.5
        ordered["boundaries"].append(second)
        ordered["boundary_authority"]["authorized_boundary_count"] = 2
        with self.assertRaises(ValueError):
            self.build(ordered)
        for field in ("source_id", "window"):
            broken = copy.deepcopy(self.authorized)
            broken[field] = "other" if field == "source_id" else {
                "start_seconds": 0, "duration_seconds": 1}
            with self.assertRaises(ValueError):
                self.build(broken)
        with self.assertRaises(ValueError):
            self.build(grid_sha="b" * 64)
        extra = copy.deepcopy(self.authorized)
        extra["unexpected"] = True
        with self.assertRaises(ValueError):
            self.build(extra)
        outside = copy.deepcopy(self.authorized)
        outside["boundaries"][0]["uncertainty_interval"]["start_seconds"] = 0
        with self.assertRaises(ValueError):
            self.build(outside)
        timeline = self.build()
        timeline["segments"][0]["end_seconds"] = 386
        with self.assertRaises(ValueError):
            validate_typed_story_segment_timeline(
                timeline, self.grid, self.authorized,
                grid_sha256=digest(self.grid), boundaries_sha256=digest(self.authorized))

    def test_cli_atomic_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            grid_path, boundary_path = root / "grid.json", root / "boundaries.json"
            grid_path.write_text(json.dumps(self.grid, sort_keys=True))
            boundary_path.write_text(json.dumps(self.authorized, sort_keys=True))
            output = root / "timeline.json"
            command = [sys.executable,
                       str(ROOT / "scripts/build_typed_story_segment_timeline.py"),
                       str(grid_path), str(boundary_path), str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
