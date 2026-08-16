import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.multi_signal_review_packet import build_multi_signal_review_packet, validate_multi_signal_review_packet


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class MultiSignalReviewPacketTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=30)
        self.grid_sha = digest(self.grid)
        ids = [item["candidate_id"] for item in self.grid["candidates"]]
        self.timeline = {"schema_version": "aegis360.event-timeline.v2", "source_id": "fixture",
                         "window": self.grid["window"], "inputs": {"context_view_grid_sha256": self.grid_sha},
                         "events": [{"event_id": "event:multi:0000", "start_seconds": 8.0,
                                     "end_seconds": 12.0, "signals": [{"signal_type": "scene_change"}],
                                     "review_scope": {"mode": "all_declared_candidates", "candidate_ids": ids}}]}

    def build(self):
        return build_multi_signal_review_packet(
            self.timeline, self.grid, event_id="event:multi:0000",
            timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_neutral_event_uses_two_times_all_four_views(self):
        value = self.build()
        self.assertEqual([row["timestamp_seconds"] for row in value["samples"]], [8.0, 12.0])
        self.assertEqual(sum(len(row["candidate_ids"]) for row in value["samples"]), 8)
        self.assertFalse(value["privacy"]["contains_editorial_decision"])
        validate_multi_signal_review_packet(
            value, self.timeline, self.grid,
            timeline_sha256=digest(self.timeline), grid_sha256=self.grid_sha,
        )

    def test_grid_order_mutation_fails(self):
        self.timeline["events"][0]["review_scope"]["candidate_ids"].reverse()
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
