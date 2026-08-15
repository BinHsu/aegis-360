import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.candidate_availability import build_candidate_availability
from aegis360.context_views import build_context_view_grid
from aegis360.editorial_roles import build_editorial_roles
from aegis360.event_timeline import build_event_timeline, validate_event_timeline


def digest(value):
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


class EventTimelineTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(
            source_id="fixture", start_seconds=10, duration_seconds=20,
        )
        self.grid_sha = digest(self.grid)
        self.roles = build_editorial_roles(
            self.grid, grid_sha256=self.grid_sha,
            primary_candidate_id="context:cardinal:3",
            reaction_candidate_id="context:cardinal:1", adapter_id="fixture",
        )
        self.reactions = {
            "schema_version": "aegis360.reaction-intervals.v1",
            "source_id": "fixture",
            "source_sound_event_schema": "aegis360.apple-sound-events.v1",
            "policy": {
                "applause_threshold": .5, "clapping_threshold": .5,
                "minimum_supporting_windows": 2,
                "status": "poc_hypothesis_not_editorial_ground_truth",
            },
            "intervals": [
                {
                    "start_seconds": 8, "end_seconds": 14,
                    "supporting_window_count": 3,
                    "peak_applause_confidence": .8,
                    "peak_clapping_confidence": .9,
                },
                {
                    "start_seconds": 22, "end_seconds": 28,
                    "supporting_window_count": 4,
                    "peak_applause_confidence": .7,
                    "peak_clapping_confidence": .75,
                },
            ],
            "privacy": {}, "limitations": [],
        }
        config = {
            "schema_version": "aegis360.candidate-availability-config.v1",
            "config_id": "fixture", "reviewer_kind": "human",
            "adapter_id": "fixture",
            "candidates": [{
                "candidate_id": "context:cardinal:1",
                "intervals": [{"start_seconds": 12, "end_seconds": 26}],
            }],
        }
        self.availability = build_candidate_availability(
            config, self.grid, config_sha256="a" * 64, grid_sha256=self.grid_sha,
        )

    def build(self):
        return build_event_timeline(
            self.grid, self.roles, self.reactions, self.availability,
            grid_sha256=self.grid_sha, roles_sha256=digest(self.roles),
            reactions_sha256=digest(self.reactions),
            availability_sha256=digest(self.availability),
        )

    def test_clips_events_retains_source_timing_and_onset_availability(self):
        value = self.build()
        self.assertEqual(len(value["events"]), 2)
        first, second = value["events"]
        self.assertEqual((first["start_seconds"], first["end_seconds"]), (10.0, 14.0))
        self.assertEqual(first["audio_evidence"]["source_event_start_seconds"], 8.0)
        self.assertFalse(first["view_context"]["proposed_available_at_event_onset"])
        self.assertTrue(second["view_context"]["proposed_available_at_event_onset"])
        self.assertEqual(
            second["view_context"]["proposed_available_intervals"],
            [{"start_seconds": 22, "end_seconds": 26}],
        )
        self.assertFalse(value["privacy"]["contains_editorial_decision"])

    def test_exact_rebuild_rejects_decisions_geometry_and_hash_changes(self):
        value = self.build()
        kwargs = {
            "grid_sha256": self.grid_sha, "roles_sha256": digest(self.roles),
            "reactions_sha256": digest(self.reactions),
            "availability_sha256": digest(self.availability),
        }
        validate_event_timeline(
            value, self.grid, self.roles, self.reactions, self.availability, **kwargs,
        )
        mutations = (
            lambda v: v["events"][0].update({"decision": "promote"}),
            lambda v: v["events"][0]["view_context"].__setitem__(
                "current_candidate_id", "context:cardinal:0",
            ),
            lambda v: v["inputs"].__setitem__(
                "reaction_intervals_sha256", "0" * 64,
            ),
        )
        for mutation in mutations:
            broken = json.loads(json.dumps(value))
            mutation(broken)
            with self.assertRaises(ValueError):
                validate_event_timeline(
                    broken, self.grid, self.roles, self.reactions,
                    self.availability, **kwargs,
                )


if __name__ == "__main__":
    unittest.main()
