import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.segment_view_relevance import build_segment_view_relevance
from aegis360.story_segment_review_packet import build_story_segment_review_packet
from tests.test_story_segment_review_packet import build_segment_packet_fixture, digest


class SegmentViewRelevanceTests(unittest.TestCase):
    def setUp(self):
        grid, grid_sha, timeline = build_segment_packet_fixture()
        self.packet = build_story_segment_review_packet(
            timeline, grid, segment_id="segment:story:0000",
            segment_timeline_sha256=digest(timeline), grid_sha256=grid_sha,
        )
        ids = self.packet["samples"][0]["candidate_ids"]
        self.config = {
            "schema_version": "aegis360.segment-view-relevance-config.v1",
            "reviewer_type": "agent", "reviewer_id": "segment-view-audit-v1",
            "reviewer_asset_sha256": None, "status": "observed",
            "candidate_observations": [
                {"candidate_id": candidate_id, "visibility": "clear",
                 "segment_relevance": "primary" if index == 1 else "supporting",
                 "temporal_consistency": "stable"}
                for index, candidate_id in enumerate(ids)
            ],
        }

    def build(self, config=None):
        config = self.config if config is None else config
        return build_segment_view_relevance(
            config, self.packet, config_sha256=digest(config),
            packet_sha256=digest(self.packet),
        )

    def test_observed_covers_order_and_does_not_select(self):
        value = self.build()
        self.assertFalse(value["planner_authority"]["candidate_selected"])
        self.assertEqual(len(value["evidence"]["candidate_observations"]), 4)

    def test_abstain_and_primary_count_fail_closed(self):
        abstain = copy.deepcopy(self.config)
        abstain["status"] = "abstain"
        abstain["candidate_observations"] = []
        self.assertEqual(self.build(abstain)["evidence"]["status"], "abstain")
        for index in (0, 2):
            broken = copy.deepcopy(self.config)
            for item in broken["candidate_observations"]:
                item["segment_relevance"] = "supporting"
            if index == 2:
                broken["candidate_observations"][0]["segment_relevance"] = "primary"
                broken["candidate_observations"][1]["segment_relevance"] = "primary"
            with self.assertRaises(ValueError):
                self.build(broken)

    def test_reorder_and_model_provenance_fail(self):
        reordered = copy.deepcopy(self.config)
        reordered["candidate_observations"].reverse()
        with self.assertRaises(ValueError):
            self.build(reordered)
        model = copy.deepcopy(self.config)
        model["reviewer_type"] = "local_model"
        with self.assertRaises(ValueError):
            self.build(model)


if __name__ == "__main__":
    unittest.main()
