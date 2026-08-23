import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.prefix_foreshadow_plan import plan_prefix_foreshadow, validate_prefix_foreshadow_plan
from tests.test_whole_film_chapter_map import fixture, sha
from aegis360.whole_film_chapter_map import build_whole_film_chapter_map


class PrefixForeshadowPlanTests(unittest.TestCase):
    def setUp(self):
        segments, config = fixture()
        self.chapter_map = build_whole_film_chapter_map(
            segments, config, segment_timeline_sha256=sha(segments),
            config_sha256=sha(config))
        self.eligibility = {
            "schema_version": "aegis360.chapter-map-foreshadow-eligibility.v1",
            "source_id": "fixture", "eligible": True,
            "inputs": {"whole_film_chapter_map_sha256": sha(self.chapter_map)},
            "planner_authority": {"may_plan_one_prefix_foreshadow": True},
        }
        self.proposal = {
            "schema_version": "aegis360.prefix-foreshadow-proposal.v1",
            "proposal_id": "fixture-prefix-v1", "target_chapter_id": "chapter:0001",
            "start_seconds": 21.0, "end_seconds": 23.0,
            "evidence_sha256": "e" * 64,
        }
        self.policy = json.loads((ROOT / "config/prefix-foreshadow-policy-v1.json").read_text())

    def build(self, proposal=None, eligibility=None):
        proposal = self.proposal if proposal is None else proposal
        eligibility = self.eligibility if eligibility is None else eligibility
        return plan_prefix_foreshadow(
            self.chapter_map, eligibility, proposal, self.policy,
            chapter_map_sha256=sha(self.chapter_map), eligibility_sha256=sha(eligibility),
            proposal_sha256=sha(proposal), policy_sha256=sha(self.policy))

    def test_one_copy_then_complete_monotonic_body_retains_payoff(self):
        value = self.build()
        self.assertEqual([(item["role"], item["source_start_seconds"],
                           item["source_end_seconds"]) for item in value["spans"]],
                         [("future_prefix_copy", 21.0, 23.0),
                          ("complete_chronological_body", 0.0, 30.0)])
        self.assertTrue(value["invariants"]["payoff_retained"])
        self.assertFalse(value["planner_authority"]["candidate_selected"])
        validate_prefix_foreshadow_plan(
            value, self.chapter_map, self.eligibility, self.proposal, self.policy,
            chapter_map_sha256=sha(self.chapter_map),
            eligibility_sha256=sha(self.eligibility),
            proposal_sha256=sha(self.proposal), policy_sha256=sha(self.policy))

    def test_unqualified_wrong_chapter_and_out_of_bounds_fail(self):
        denied = copy.deepcopy(self.eligibility)
        denied["eligible"] = False
        with self.assertRaises(ValueError):
            self.build(eligibility=denied)
        for key, value in (("target_chapter_id", "chapter:0000"),
                           ("end_seconds", 25.0), ("start_seconds", 22.5)):
            broken = copy.deepcopy(self.proposal)
            broken[key] = value
            with self.assertRaises(ValueError):
                self.build(proposal=broken)


if __name__ == "__main__":
    unittest.main()
