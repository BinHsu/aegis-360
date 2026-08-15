import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.global_camera_segments import build_global_camera_segments


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class GlobalCameraSegmentsTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=30)
        self.grid_sha = digest(self.grid)
        self.timeline = {
            "schema_version": "aegis360.event-timeline.v1", "source_id": "fixture",
            "events": [
                {"event_id": "e0", "view_context": {"current_candidate_id": "context:cardinal:0", "proposed_candidate_id": "context:cardinal:1", "proposed_available_intervals": [{"start_seconds": 5, "end_seconds": 8}]}},
                {"event_id": "e1", "view_context": {"current_candidate_id": "context:cardinal:0", "proposed_candidate_id": "context:cardinal:1", "proposed_available_intervals": [{"start_seconds": 20, "end_seconds": 24}]}},
            ],
        }
        self.plan = {
            "schema_version": "aegis360.global-event-plan.v1",
            "inputs": {"context_view_grid_sha256": self.grid_sha},
            "decisions": [
                {"event_id": "e0", "selected_candidate_id": "context:cardinal:1"},
                {"event_id": "e1", "selected_candidate_id": "context:cardinal:0"},
            ],
        }

    def build(self):
        return build_global_camera_segments(
            self.plan, self.timeline, self.grid, plan_sha256=digest(self.plan),
            timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_selected_view_is_clipped_to_availability(self):
        value = self.build()
        self.assertEqual(
            [(row["start_seconds"], row["end_seconds"], row["candidate_id"]) for row in value["segments"]],
            [(0.0, 5.0, "context:cardinal:0"), (5.0, 8.0, "context:cardinal:1"), (8.0, 30.0, "context:cardinal:0")],
        )

    def test_unknown_selection_and_incomplete_decisions_fail(self):
        self.plan["decisions"][0]["selected_candidate_id"] = "invented"
        with self.assertRaises(ValueError):
            self.build()
        self.plan["decisions"] = self.plan["decisions"][:1]
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
