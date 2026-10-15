"""Prelaunch and reconstruction boundaries for the private 37-row driver."""

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_complete_cases import (  # noqa: E402
    _PrivateCompleteSyntheticObservations, _PrivateObservedCase,
    _observe_private_complete_synthetic_cases_once,
    _revalidate_private_complete_synthetic_observations,
)
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_case_manifest,
)
from tests.test_sparse_story_synthetic_plan import SyntheticCasePlanTests  # noqa: E402


class PrivateCompleteCaseTests(unittest.TestCase):
    def setUp(self):
        _, self.manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20,
            stimuli=SyntheticCasePlanTests().stimuli())

    def inputs(self):
        return dict(frozen_manifest=self.manifest, adapter_proof=(),
            mutation_claim=None, mutation_owner=None,
            replacement_claim=None, replacement_owner=None,
            exact_claims={}, prepared_owners={})

    def test_caller_supplied_adapter_result_strings_cannot_enter_driver(self):
        with mock.patch(
                "aegis360.sparse_story_probe_denials."
                "_ClaimedProbedBatch._run_coordinator_fixture_case_once") as launch:
            with self.assertRaisesRegex(ValueError, "adapter proof"):
                _observe_private_complete_synthetic_cases_once(**self.inputs())
        launch.assert_not_called()

    def test_changed_frozen_manifest_fails_before_coordinator_execution(self):
        changed = {**self.manifest, "cases": [
            {**self.manifest["cases"][0], "expected_result": "trust_invalid"},
            *self.manifest["cases"][1:]]}
        with mock.patch(
                "aegis360.sparse_story_probe_denials."
                "_ClaimedProbedBatch._run_coordinator_fixture_case_once") as launch:
            with self.assertRaises(ValueError):
                _observe_private_complete_synthetic_cases_once(**{
                    **self.inputs(), "frozen_manifest": changed})
        launch.assert_not_called()

    def test_private_proof_cannot_relabel_or_omit_a_row(self):
        from aegis360.sparse_story_runner_contract import sha256

        rows = tuple(_PrivateObservedCase(row["case_id"],
            row["expected_result"], None) for row in self.manifest["cases"])
        proof = _PrivateCompleteSyntheticObservations(
            sha256(self.manifest), rows)
        wrong_order = _PrivateCompleteSyntheticObservations(
            proof.manifest_sha256, (rows[1], rows[0], *rows[2:]))
        with self.assertRaisesRegex(ValueError, "order"):
            _revalidate_private_complete_synthetic_observations(
                proof=wrong_order, frozen_manifest=self.manifest,
                prepared_owners={})
        missing = _PrivateCompleteSyntheticObservations(
            proof.manifest_sha256, rows[:-1])
        with self.assertRaisesRegex(ValueError, "shape"):
            _revalidate_private_complete_synthetic_observations(
                proof=missing, frozen_manifest=self.manifest,
                prepared_owners={})
        with self.assertRaisesRegex(ValueError, "adapter row proof"):
            _revalidate_private_complete_synthetic_observations(
                proof=proof, frozen_manifest=self.manifest,
                prepared_owners={})


if __name__ == "__main__":
    unittest.main()
