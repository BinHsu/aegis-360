import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.segment_candidate_utility import (build_segment_candidate_utility,
                                                validate_segment_candidate_utility)
from tests.test_segment_view_relevance import SegmentViewRelevanceTests
from tests.test_story_segment_review_packet import build_segment_packet_fixture, digest


class SegmentCandidateUtilityTests(unittest.TestCase):
    def setUp(self):
        fixture = SegmentViewRelevanceTests()
        fixture.setUp()
        self.relevance = fixture.build()
        self.grid, self.grid_sha256, _ = build_segment_packet_fixture()
        self.ids = [item["candidate_id"] for item in self.grid["candidates"]]
        self.policy = json.loads(
            (ROOT / "config/segment-candidate-utility-policy-v1.json").read_text()
        )

    def build(self):
        return build_segment_candidate_utility(
            self.relevance, self.grid, self.policy,
            relevance_sha256=digest(self.relevance), grid_sha256=self.grid_sha256,
            policy_sha256=digest(self.policy),
        )

    def test_scores_every_grid_candidate_without_selecting(self):
        result = self.build()
        self.assertEqual([item["candidate_id"] for item in result["utilities"]], self.ids)
        self.assertEqual([item["total"] for item in result["utilities"]], [2.5, 3.5, 2.5, 2.5])
        self.assertTrue(all(item["eligible"] for item in result["utilities"]))
        self.assertFalse(result["planner_authority"]["candidate_selected"])
        self.assertEqual(result["inputs"], {
            "segment_view_relevance_sha256": digest(self.relevance),
            "context_view_grid_sha256": self.grid_sha256,
            "utility_policy_sha256": digest(self.policy),
        })
        validate_segment_candidate_utility(
            result, self.relevance, self.grid, self.policy,
            relevance_sha256=digest(self.relevance), grid_sha256=self.grid_sha256,
            policy_sha256=digest(self.policy),
        )

    def test_abstention_exposes_no_alternative_and_neutral_utility(self):
        abstain = copy.deepcopy(self.relevance)
        abstain["evidence"] = {"status": "abstain", "candidate_observations": []}
        self.relevance = abstain
        utilities = self.build()["utilities"]
        self.assertFalse(any(item["eligible"] for item in utilities))
        self.assertTrue(all(item["total"] == 0.0 for item in utilities))

    def test_grid_order_policy_and_lineage_fail_closed(self):
        reordered = copy.deepcopy(self.relevance)
        reordered["evidence"]["candidate_observations"].reverse()
        self.relevance = reordered
        with self.assertRaises(ValueError):
            self.build()

        self.setUp()
        mutated = self.build()
        mutated["utilities"][0]["total"] += 1
        with self.assertRaises(ValueError):
            validate_segment_candidate_utility(
                mutated, self.relevance, self.grid, self.policy,
                relevance_sha256=digest(self.relevance), grid_sha256=self.grid_sha256,
                policy_sha256=digest(self.policy),
            )

        self.setUp()
        del self.policy["visibility_weights"]["partial"]
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
