"""Actual native receipt facts cannot be reassigned to coordinator case IDs."""

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_exact_rebuild_cases import (  # noqa: E402
    _observe_private_exact_rebuild_case,
    _observe_private_exact_rebuild_facts,
)
from aegis360.sparse_story_private_run_receipt import (  # noqa: E402
    _build_private_synthetic_run_receipt,
)
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch  # noqa: E402
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    canonical_run_receipt_shape_bytes,
)
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_case_manifest,
)
from tests import test_sparse_story_raw_probe_transport as host_tests  # noqa: E402
from tests import test_sparse_story_synthetic_plan as plan_tests  # noqa: E402


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class ExactRebuildCaseHostTests(unittest.TestCase):
    def test_each_coordinator_row_rebuilds_its_own_native_receipt(self):
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20,
            stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
        rows = {row["case_id"]: row for row in manifest["cases"]}
        for case_id in ("single_invocation", "receipt_rebuild"):
            with self.subTest(case_id=case_id), host_tests.RawProbeTransportHostTests.context(
                    self, own_batch_scratch=True, coordinated=True,
                    expose_live=True) as inputs:
                live = inputs.pop("_fixture_live")
                session = _open_retained_probed_batch(**inputs)
                try:
                    claim = session.claim_once()
                    capture = claim._run_coordinator_fixture_case_once(
                        case_id, rows[case_id])
                    self.assertTrue(capture.completed, capture.reason)
                    with mock.patch("aegis360.sparse_story_receipt_inputs._require_live",
                            return_value=live):
                        receipt = _build_private_synthetic_run_receipt(
                            claim=claim, frozen_row=rows[case_id])
                        facts = _observe_private_exact_rebuild_case(
                            claim=claim, frozen_row=rows[case_id], receipt=receipt)
                        self.assertEqual(facts.case_id, case_id)
                        self.assertEqual(facts.launch_count, 1)
                        self.assertEqual(facts.receipt_sha256,
                            hashlib.sha256(receipt.bytes).hexdigest())
                        other = ("receipt_rebuild" if case_id == "single_invocation"
                                 else "single_invocation")
                        with self.assertRaises(ValueError):
                            _observe_private_exact_rebuild_case(
                                claim=claim, frozen_row=rows[other], receipt=receipt)
                finally:
                    session.close()

    def test_real_fd_receipt_proves_its_facts_but_not_coordinator_rows(self):
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20,
            stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
        rows = {row["case_id"]: row for row in manifest["cases"]}
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as inputs:
            live = inputs.pop("_fixture_live")
            session = _open_retained_probed_batch(**inputs)
            try:
                claim = session.claim_once()
                capture = claim._run_fixed_synthetic_fd_case_once(
                    rows["fd_hygiene"])
                self.assertTrue(capture.completed, capture.reason)
                with mock.patch("aegis360.sparse_story_receipt_inputs._require_live",
                        return_value=live):
                    receipt = _build_private_synthetic_run_receipt(
                        claim=claim, frozen_row=rows["fd_hygiene"])
                    facts = _observe_private_exact_rebuild_facts(
                        claim=claim, executed_row=rows["fd_hygiene"],
                        receipt=receipt)
                    self.assertEqual(facts.case_id, "fd_hygiene")
                    self.assertEqual(facts.launch_count, 1)
                    self.assertEqual(facts.receipt_sha256,
                        hashlib.sha256(receipt.bytes).hexdigest())
                    for case_id in ("single_invocation", "receipt_rebuild"):
                        with self.subTest(case_id=case_id), self.assertRaises(ValueError):
                            _observe_private_exact_rebuild_case(
                                claim=claim, frozen_row=rows[case_id],
                                receipt=receipt)

                    original = receipt.bytes
                    changed = json.loads(original)
                    changed["execution"]["stdout_sha256"] = "0" * 64
                    receipt.bytes = canonical_run_receipt_shape_bytes(changed)
                    with self.assertRaisesRegex(ValueError, "exactly rebuild"):
                        _observe_private_exact_rebuild_facts(
                            claim=claim, executed_row=rows["fd_hygiene"],
                            receipt=receipt)
                    receipt.bytes = original
                    claim._launch_ledger.count = 2
                    with self.assertRaises(ValueError):
                        _observe_private_exact_rebuild_facts(
                            claim=claim, executed_row=rows["fd_hygiene"],
                            receipt=receipt)
                    claim._launch_ledger.count = 1
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
