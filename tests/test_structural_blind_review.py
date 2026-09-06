import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.structural_blind_review import (  # noqa: E402
    SCHEDULE_CONFIG_SHA256, SCORE_CONTRACT_SHA256, SELECTION_PROOF_SHA256,
    build_structural_blind_review, evaluate_structural_blind_reviews,
    validate_structural_blind_evaluation, validate_structural_blind_review,
)


def answer(classification):
    values = {
        "story_change": ("observed", "observed", "persistent", "supports", "absent"),
        "no_semantic_change": ("observed", "observed", "not_persistent", "supports", "absent"),
        "capture_artifact": ("observed", "observed", "persistent", "supports", "present"),
        "abstain": ("unclear", "unclear", "unclear", "insufficient", "unclear"),
    }[classification]
    return dict(zip(("early_persistence", "late_persistence", "persistent_difference",
                     "transition_support", "artifact_evidence"), values),
                classification=classification)


class StructuralBlindReviewTests(unittest.TestCase):
    def setUp(self):
        self.packets = [f"packet-{index:020x}" for index in range(1, 9)]
        self.public_sha = "a" * 64
        self.tree_sha = "b" * 64
        self.classes = ["story_change"] * 3 + ["no_semantic_change"] * 5
        self.responses = [dict(packet_id=packet, **answer(kind))
                          for packet, kind in zip(self.packets, self.classes)]

    def review(self, slot="reviewer-00000000000000000001", classes=None):
        responses = [dict(packet_id=packet, **answer(kind))
                     for packet, kind in zip(self.packets, classes or self.classes)]
        return build_structural_blind_review(
            public_packet_ids=self.packets, public_index_sha256=self.public_sha,
            bundle_tree_sha256=self.tree_sha,
            schedule_config_sha256=SCHEDULE_CONFIG_SHA256,
            reviewer_slot_id=slot, responses=responses)

    def evaluation(self, classes_a=None, classes_b=None, scores=None):
        a = self.review(classes=classes_a)
        b = self.review("reviewer-00000000000000000002", classes_b)
        mapping = [{"packet_id": packet, "selection_rank": index,
                    "event_id": f"event:multi:{index:04d}",
                    "signal_id": f"event:scene-change:{index:04d}"}
                   for index, packet in enumerate(self.packets, 1)]
        values = scores or [0.9, 0.8, 0.7, 0.5, 0.4, 0.3, 0.2, 0.1]
        score_rows = [{"selection_rank": index,
                       "event_id": f"event:multi:{index:04d}",
                       "signal_id": f"event:scene-change:{index:04d}",
                       "score": value}
                      for index, value in enumerate(values, 1)]
        inputs = dict(public_packet_ids=self.packets,
                      public_index_sha256=self.public_sha,
                      bundle_tree_sha256=self.tree_sha,
                      schedule_config_sha256=SCHEDULE_CONFIG_SHA256,
                      private_mapping=mapping, private_mapping_sha256="c" * 64,
                      structural_scores=score_rows, structural_scores_sha256="d" * 64,
                      selection_proof_sha256=SELECTION_PROOF_SHA256,
                      score_contract_sha256=SCORE_CONTRACT_SHA256,
                      review_a=a, review_a_sha256="e" * 64,
                      review_b=b, review_b_sha256="f" * 64)
        return evaluate_structural_blind_reviews(**inputs), inputs

    def test_review_is_closed_ordered_bound_and_consistent(self):
        review = self.review()
        validate_structural_blind_review(
            review, public_packet_ids=self.packets,
            public_index_sha256=self.public_sha, bundle_tree_sha256=self.tree_sha,
            schedule_config_sha256=SCHEDULE_CONFIG_SHA256)
        self.assertEqual([row["packet_id"] for row in review["responses"]], self.packets)
        self.assertFalse(any(review["privacy"].values()))
        for mutation in (
            lambda d: d["responses"][0].__setitem__("free_text", "source at 12.5"),
            lambda d: d["responses"].reverse(),
            lambda d: d["responses"].pop(),
            lambda d: d["responses"][0].__setitem__("classification", "no_semantic_change"),
            lambda d: d["inputs"].__setitem__("bundle_tree_sha256", "0" * 64),
        ):
            changed = copy.deepcopy(review); mutation(changed)
            with self.assertRaises(ValueError):
                validate_structural_blind_review(
                    changed, public_packet_ids=self.packets,
                    public_index_sha256=self.public_sha,
                    bundle_tree_sha256=self.tree_sha,
                    schedule_config_sha256=SCHEDULE_CONFIG_SHA256)

    def test_replicated_equality_and_reversal(self):
        passed, inputs = self.evaluation()
        validate_structural_blind_evaluation(passed, **inputs)
        self.assertEqual(passed["gate"]["outcome"], "replicated")
        tampered = copy.deepcopy(passed)
        tampered["gate"]["outcome"] = "inconclusive"
        with self.assertRaises(ValueError):
            validate_structural_blind_evaluation(tampered, **inputs)
        equal, _ = self.evaluation(scores=[0.7, 0.8, 0.7, 0.7, 0.4, 0.3, 0.2, 0.1])
        self.assertEqual(equal["gate"]["outcome"], "reject")
        reversed_result, _ = self.evaluation(
            scores=[0.3, 0.2, 0.1, 0.9, 0.8, 0.7, 0.6, 0.5])
        self.assertEqual(reversed_result["gate"]["outcome"], "reject")
        self.assertFalse(reversed_result["authority"]["semantic_boundary"])

    def test_disagreement_artifact_abstain_and_imbalance_are_inconclusive(self):
        cases = []
        disagreement = list(self.classes); disagreement[0] = "no_semantic_change"
        cases.append((self.classes, disagreement, "reviewer_disagreement"))
        artifact = list(self.classes); artifact[0] = "capture_artifact"
        cases.append((artifact, artifact, "artifact_or_abstain"))
        abstain = list(self.classes); abstain[0] = "abstain"
        cases.append((abstain, abstain, "artifact_or_abstain"))
        imbalance = ["story_change"] + ["no_semantic_change"] * 7
        cases.append((imbalance, imbalance, "class_imbalance"))
        for left, right, reason in cases:
            result, _ = self.evaluation(left, right)
            self.assertEqual(result["gate"]["outcome"], "inconclusive")
            self.assertEqual(result["gate"]["reason"], reason)
            self.assertIsNone(result["gate"]["strict_ordering_passed"])

    def test_malformed_lineage_mapping_scores_slots_and_no_backfill_error(self):
        _, inputs = self.evaluation()
        mutations = []
        same_slot = copy.deepcopy(inputs)
        same_slot["review_b"]["reviewer_slot_id"] = same_slot["review_a"]["reviewer_slot_id"]
        mutations.append(same_slot)
        stale = copy.deepcopy(inputs); stale["review_a_sha256"] = "bad"
        mutations.append(stale)
        missing = copy.deepcopy(inputs); missing["private_mapping"].pop()
        mutations.append(missing)
        backfill = copy.deepcopy(inputs)
        backfill["public_packet_ids"] = backfill["public_packet_ids"][:-1] + ["packet-ffffffffffffffffffff"]
        mutations.append(backfill)
        mismatch = copy.deepcopy(inputs); mismatch["structural_scores"][0]["signal_id"] = "event:scene-change:9999"
        mutations.append(mismatch)
        duplicate = copy.deepcopy(inputs); duplicate["private_mapping"][1]["selection_rank"] = 1
        mutations.append(duplicate)
        for changed in mutations:
            with self.assertRaises(ValueError):
                evaluate_structural_blind_reviews(**changed)


if __name__ == "__main__":
    unittest.main()
