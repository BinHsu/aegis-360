import copy
import hashlib
import json
import math
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tests import test_structural_blind_schedule as proof_helpers  # noqa: E402
from aegis360.structural_label_free_scores import (  # noqa: E402
    CONTRACT_SHA256, PROOF_SHA256, SOURCE_SHA256, build_score_artifact,
    canonical_contract_bytes, sample_plan, validate_score_artifact,
    validate_score_contract,
)


class StructuralLabelFreeScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        full = json.loads((ROOT / "config/structural-chapter-labeled-contrast-v1.json").read_bytes())
        cls.contract = {key: full[key] for key in
                        ("acquisition", "descriptor", "sample_offsets_seconds", "score")}
        helper = proof_helpers.StructuralBlindScheduleTests(); cls.proof = helper.proof()

    def inputs(self):
        plan = sample_plan(self.proof, self.contract)
        indices = {index for _, values in plan for index in values}
        return dict(contract=self.contract, selection_proof=self.proof,
            selection_proof_sha256=PROOF_SHA256, source_sha256_before=SOURCE_SHA256,
            source_sha256_after=SOURCE_SHA256, frame_count=max(indices) + 1,
            selected_frames={index: bytes([index % 251]) * (160 * 80) for index in indices})

    def test_contract_hash_and_closed_label_free_output(self):
        validate_score_contract(self.contract)
        self.assertEqual(hashlib.sha256(canonical_contract_bytes(self.contract)).hexdigest(),
                         CONTRACT_SHA256)
        inputs = self.inputs(); artifact = build_score_artifact(**inputs)
        self.assertEqual(len(artifact["scores"]), 8)
        self.assertEqual([row["selection_rank"] for row in artifact["scores"]], list(range(1, 9)))
        self.assertEqual(set(artifact), {"schema_version", "inputs", "scores", "privacy", "authority"})
        encoded = json.dumps(artifact)
        for forbidden in ("expected_class", "semantic_label", "review", "threshold",
                          "private_schedule", "public_index", "source_path"):
            self.assertNotIn(f'"{forbidden}"', encoded)
        validate_score_artifact(artifact, **inputs)

    def test_proof_order_tamper_source_hash_and_missing_sample_fail(self):
        inputs = self.inputs()
        reordered = copy.deepcopy(self.proof)
        reordered["selected"][0], reordered["selected"][1] = reordered["selected"][1], reordered["selected"][0]
        with self.assertRaises(ValueError): build_score_artifact(**{**inputs, "selection_proof": reordered})
        with self.assertRaisesRegex(ValueError, "lineage"):
            build_score_artifact(**{**inputs, "source_sha256_after": "0" * 64})
        missing = dict(inputs); missing["selected_frames"] = dict(inputs["selected_frames"])
        missing["selected_frames"].pop(next(iter(missing["selected_frames"])))
        with self.assertRaisesRegex(ValueError, "missing"):
            build_score_artifact(**missing)

    def test_contract_tamper_and_nonfinite_score_fail(self):
        bad = copy.deepcopy(self.contract); bad["score"] = "threshold"
        with self.assertRaises(ValueError): validate_score_contract(bad)
        inputs = self.inputs()
        with mock.patch("aegis360.structural_label_free_scores.evaluation_metrics",
                        return_value={"score": math.nan}):
            with self.assertRaisesRegex(ValueError, "finite"):
                build_score_artifact(**inputs)


if __name__ == "__main__": unittest.main()
