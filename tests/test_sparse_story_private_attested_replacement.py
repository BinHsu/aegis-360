"""Real native replacement row binds receipt bytes to publisher refusal."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_attested_replacement import (
    _observe_attested_private_replacement,
)
from aegis360.sparse_story_private_run_publication import _OwnedPrivateRunRoot
from aegis360.sparse_story_private_run_receipt import _build_private_synthetic_run_receipt
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch
from aegis360.sparse_story_synthetic_plan import _freeze_private_synthetic_case_manifest
from tests import test_sparse_story_raw_probe_transport as host_tests
from tests import test_sparse_story_synthetic_plan as plan_tests


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class AttestedReplacementHostTests(unittest.TestCase):
    def test_native_replacement_receipt_publishes_and_preserves_four_peers(self):
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20,
            stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
        rows = {row["case_id"]: row for row in manifest["cases"]}
        row = rows["replacement_race"]
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as inputs:
            live = inputs.pop("_fixture_live")
            session = _open_retained_probed_batch(**inputs)
            try:
                claim = session.claim_once()
                capture = claim._run_coordinator_fixture_case_once(
                    "replacement_race", row)
                self.assertTrue(capture.completed, capture.reason)
                with mock.patch("aegis360.sparse_story_receipt_inputs._require_live",
                        return_value=live):
                    receipt = _build_private_synthetic_run_receipt(
                        claim=claim, frozen_row=row)
                    with tempfile.TemporaryDirectory() as temporary:
                        owner = _OwnedPrivateRunRoot(Path(temporary))
                        receipt.bytes += b" "
                        with self.assertRaises(ValueError):
                            _observe_attested_private_replacement(
                                owner=owner, receipt=receipt, frozen_row=row)
                        self.assertEqual(os.listdir(owner.root), [])
                        receipt.bytes = receipt.bytes[:-1]
                        with self.assertRaises(ValueError):
                            _observe_attested_private_replacement(
                                owner=owner, receipt=receipt,
                                frozen_row=rows["single_invocation"])
                        self.assertEqual(os.listdir(owner.root), [])
                        observed = _observe_attested_private_replacement(
                            owner=owner, receipt=receipt, frozen_row=row)
                        self.assertTrue(observed.revalidation_refused)
                        self.assertTrue(observed.cleanup_refused)
                        self.assertTrue(observed.originals_held)
                        self.assertTrue(observed.replacements_preserved)
                        self.assertIsNone(observed.case_result)
                        self.assertEqual((owner.root / "held-evidence.json").read_bytes(),
                                         capture.stdout)
                        self.assertEqual((owner.root / "held-receipt.json").read_bytes(),
                                         receipt.bytes)
                        self.assertEqual((owner.root / "evidence.json").read_bytes(),
                                         b"replacement-evidence-v1")
                        self.assertEqual((owner.root / "receipt.json").read_bytes(),
                                         b"replacement-receipt-v1")
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
