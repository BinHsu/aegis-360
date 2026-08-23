import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.continuity_transition_utility import (build_continuity_transition_utility,
                                                    validate_continuity_transition_utility)
from tests.test_causal_continuity_evidence import CausalContinuityEvidenceTests, digest


class ContinuityTransitionUtilityTests(unittest.TestCase):
    def setUp(self):
        fixture = CausalContinuityEvidenceTests(); fixture.setUp(); fixture.observe_first()
        self.evidence = fixture.build(); self.grid = fixture.grid
        self.policy = json.loads(
            (ROOT / "config/continuity-transition-utility-policy-v1.json").read_text()
        )

    def build(self):
        return build_continuity_transition_utility(
            self.evidence, self.grid, self.policy,
            evidence_sha256=digest(self.evidence), grid_sha256=digest(self.grid),
            policy_sha256=digest(self.policy),
        )

    def test_complete_matrix_and_cross_candidate_preservation_zero(self):
        value = self.build(); rows = value["edge_utilities"][0]["transitions"]
        self.assertEqual(len(rows), 16)
        self.assertEqual([(row["previous_candidate_id"], row["next_candidate_id"])
                          for row in rows[:5]], [
            ("context:cardinal:0", "context:cardinal:0"),
            ("context:cardinal:0", "context:cardinal:1"),
            ("context:cardinal:0", "context:cardinal:2"),
            ("context:cardinal:0", "context:cardinal:3"),
            ("context:cardinal:1", "context:cardinal:0")])
        self.assertEqual(rows[1]["components"]["same_candidate_preservation"], 0.0)
        self.assertFalse(value["planner_authority"]["transition_selected"])
        validate_continuity_transition_utility(
            value, self.evidence, self.grid, self.policy,
            evidence_sha256=digest(self.evidence), grid_sha256=digest(self.grid),
            policy_sha256=digest(self.policy),
        )

    def test_absent_from_cross_path_scores_below_preserved_same_path(self):
        rows = self.build()["edge_utilities"][0]["transitions"]
        by_pair = {(row["previous_candidate_id"], row["next_candidate_id"]): row
                   for row in rows}
        self.assertGreater(by_pair[("context:cardinal:0", "context:cardinal:0")]["total"],
                           by_pair[("context:cardinal:3", "context:cardinal:0")]["total"])

    def test_abstain_is_complete_neutral_matrix(self):
        self.evidence["edges"][0].update(status="abstain", from_cue="unknown",
                                         to_cue="unknown", narrative_relation="unknown",
                                         from_support=[], to_support=[], candidate_observations=[])
        rows = self.build()["edge_utilities"][0]["transitions"]
        self.assertEqual(len(rows), 16)
        self.assertTrue(all(row["total"] == 0 for row in rows))

    def test_lineage_policy_order_and_mutation_fail_closed(self):
        broken = copy.deepcopy(self.evidence)
        broken["edges"][0]["candidate_observations"].reverse()
        self.evidence = broken
        with self.assertRaises(ValueError): self.build()
        self.setUp(); self.policy["endpoint_weights"]["clear_absent"] = 2
        with self.assertRaises(ValueError): self.build()
        self.setUp(); value = self.build(); value["edge_utilities"][0]["transitions"][0]["total"] += 1
        with self.assertRaises(ValueError):
            validate_continuity_transition_utility(
                value, self.evidence, self.grid, self.policy,
                evidence_sha256=digest(self.evidence), grid_sha256=digest(self.grid),
                policy_sha256=digest(self.policy),
            )


if __name__ == "__main__":
    unittest.main()
