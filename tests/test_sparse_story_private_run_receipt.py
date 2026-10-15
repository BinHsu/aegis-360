"""Private adapter receipt rebuild against a real retained native fixture run."""

import hashlib
import json
import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_run_receipt import (  # noqa: E402
    _build_private_synthetic_run_receipt,
    _rebuild_private_synthetic_run_receipt,
)
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch  # noqa: E402
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    canonical_run_receipt_bytes, canonical_run_receipt_shape_bytes,
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
class PrivateRunReceiptHostTests(unittest.TestCase):
    def test_real_claim_receipt_rebuild_rejects_mutated_bytes_and_capture(self):
        planned = plan_tests.SyntheticCasePlanTests().stimuli()
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20, stimuli=planned)
        row = next(row for row in manifest["cases"]
            if row["case_id"] == "fd_hygiene")
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as inputs:
            live = inputs.pop("_fixture_live")
            session = _open_retained_probed_batch(**inputs)
            try:
                claim = session.claim_once()
                capture = claim._run_fixed_synthetic_fd_case_once(row)
                self.assertTrue(capture.completed, capture.reason)
                with mock.patch("aegis360.sparse_story_receipt_inputs._require_live",
                        return_value=live):
                    self.exercise_receipt(claim, capture, row, session)
            finally:
                session.close()

    def exercise_receipt(self, claim, capture, row, session):
        receipt = _build_private_synthetic_run_receipt(
            claim=claim, frozen_row=row)
        self.assertEqual(receipt.bytes,
            _rebuild_private_synthetic_run_receipt(
                receipt=receipt, frozen_row=row))
        parsed = json.loads(receipt.bytes)
        self.assertEqual(parsed["execution"]["invocation_count"], 1)
        self.assertEqual(parsed["execution"]["stdout_sha256"],
            hashlib.sha256(capture.stdout).hexdigest())
        self.assertFalse(parsed["execution"]["invocation_failed"])
        self.assertNotIn(b"/private/", receipt.bytes)
        self.assertNotIn(b"pid", receipt.bytes)

        original = receipt.bytes
        receipt.bytes = original + b" "
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            _rebuild_private_synthetic_run_receipt(
                receipt=receipt, frozen_row=row)
        changed = json.loads(original)
        changed["execution"]["stdout_sha256"] = "0" * 64
        receipt.bytes = canonical_run_receipt_shape_bytes(changed)
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            _rebuild_private_synthetic_run_receipt(
                receipt=receipt, frozen_row=row)
        receipt.bytes = original
        session._invocation_capture = replace(capture, stdout=b"forged")
        with self.assertRaises(ValueError):
            _rebuild_private_synthetic_run_receipt(
                receipt=receipt, frozen_row=row)
        session._invocation_capture = capture
        claim._launch_ledger.count = 2
        with self.assertRaises(ValueError):
            _rebuild_private_synthetic_run_receipt(
                receipt=receipt, frozen_row=row)
        claim._launch_ledger.count = 1
        with self.assertRaises(ValueError):
            canonical_run_receipt_bytes(parsed)


if __name__ == "__main__":
    unittest.main()
