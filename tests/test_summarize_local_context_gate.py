import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from aegis360.local_context_adapter import build_local_context_document  # noqa: E402
from summarize_local_context_gate import summarize  # noqa: E402
from tests.test_local_context_adapter import decision, proposal  # noqa: E402


def context(source_id, window_id, *, abstained=False):
    candidate_proposal = proposal()
    candidate_proposal["window"].update({
        "source_id": source_id, "window_id": window_id,
    })
    model_decision = decision()
    if abstained:
        model_decision.update({
            "context_class": "uncertain", "subject_scope": "uncertain",
            "selected_candidate_id": None,
        })
    return build_local_context_document(
        candidate_proposal, model_decision, adapter_id="fixture-adapter",
        model_id="fixture-model", model_sha256="a" * 64,
    )


class SummarizeLocalContextGateTests(unittest.TestCase):
    def write_inputs(self, root, expected_second="abstained"):
        expectations = root / "expectations.json"
        first = root / "first.json"
        second = root / "second.json"
        expectations.write_text(json.dumps({
            "schema_version": "aegis360.local-context-gate-expectations.v1",
            "cases": [
                {"source_id": "a", "window_id": "w1", "expected_outcome": "group_selected"},
                {"source_id": "b", "window_id": "w2", "expected_outcome": expected_second},
            ],
        }), encoding="utf-8")
        first.write_text(json.dumps(context("a", "w1")), encoding="utf-8")
        second.write_text(json.dumps(context("b", "w2", abstained=True)), encoding="utf-8")
        return expectations, first, second

    def test_summarizes_closed_outcomes_without_accuracy_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_inputs(Path(temporary))
            result = summarize(paths[0], [paths[1], paths[2]])
        self.assertTrue(result["expectations_met"])
        self.assertEqual(result["case_count"], 2)
        self.assertEqual(result["observed_outcome_counts"]["group_selected"], 1)
        self.assertEqual(result["observed_outcome_counts"]["abstained"], 1)
        self.assertEqual(result["excluded_from_scoring"], ["context_class", "evidence_flags"])
        self.assertNotIn("accuracy", result)

    def test_records_mismatch_without_hiding_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_inputs(Path(temporary), expected_second="context_selected")
            result = summarize(paths[0], [paths[1], paths[2]])
        self.assertFalse(result["expectations_met"])
        failed = next(case for case in result["cases"] if not case["passed"])
        self.assertEqual(failed["expected_outcome"], "context_selected")
        self.assertEqual(failed["observed_outcome"], "abstained")

    def test_requires_exact_case_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = self.write_inputs(Path(temporary))
            with self.assertRaisesRegex(ValueError, "exactly match"):
                summarize(paths[0], [paths[1]])


if __name__ == "__main__":
    unittest.main()
