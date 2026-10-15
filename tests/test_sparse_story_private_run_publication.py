"""Private native-capture publication and bounded portable failure controls."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_run_publication import _OwnedPrivateRunRoot
from aegis360.sparse_story_private_run_receipt import (
    _PrivateRunReceipt, _build_private_synthetic_run_receipt,
)
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch
from aegis360.sparse_story_runner_contract import (
    PRIVACY, RECEIPT_AUTHORITY, RECEIPT_SCHEMA,
    canonical_run_receipt_shape_bytes,
)
from aegis360.sparse_story_synthetic_plan import _freeze_private_synthetic_case_manifest
from tests import test_sparse_story_raw_probe_transport as host_tests
from tests import test_sparse_story_synthetic_plan as plan_tests


def _portable_exclusive_rename(source, destination):
    """Test-only rename substitute for CI hosts without renamex_np."""
    if Path(destination).exists():
        raise ValueError("destination already exists")
    os.rename(source, destination)


def _portable_receipt():
    """Test double for publication mechanics; never treated as native evidence."""
    capture = SimpleNamespace(stdout=b'{"sample":1}')
    value = {
        "schema_version": RECEIPT_SCHEMA,
        "packet_id": "packet-" + "b" * 20,
        "inputs": {name: "a" * 64 for name in (
            "adapter_projection_sha256", "sanitized_media_result_sha256",
            "runtime_manifest_sha256", "model_manifest_sha256",
            "prompt_schema_manifest_sha256", "runner_policy_sha256")},
        "execution": {"invocation_count": 1, "stdout_present": True,
            "stdout_sha256": hashlib.sha256(capture.stdout).hexdigest(),
            "invocation_failed": False},
        "privacy": dict(PRIVACY), "authority": dict(RECEIPT_AUTHORITY),
    }
    receipt = object.__new__(_PrivateRunReceipt)
    receipt._claim = object()
    receipt._capture = capture
    receipt.bytes = canonical_run_receipt_shape_bytes(value)
    return receipt


class PrivateRunPublicationPortableTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.owner = _OwnedPrivateRunRoot(Path(temp.name))
        self.receipt = _portable_receipt()
        self.row = {"case_id": "fd_hygiene"}
        self.rebuild = mock.patch(
            "aegis360.sparse_story_private_run_publication._rebuild_private_synthetic_run_receipt",
            side_effect=lambda **kw: kw["receipt"].bytes)
        self.classify = mock.patch(
            "aegis360.sparse_story_private_run_publication._classify_fixed_synthetic_output",
            return_value="success")
        self.rebuild.start(); self.classify.start()
        self.addCleanup(self.rebuild.stop); self.addCleanup(self.classify.stop)
        rename = mock.patch(
            "aegis360.sparse_story_private_publication._rename_exclusive",
            side_effect=_portable_exclusive_rename)
        rename.start()
        self.addCleanup(rename.stop)

    def test_exact_two_peers_and_hashes(self):
        pair = self.owner.publish_once(receipt=self.receipt, frozen_row=self.row)
        self.assertEqual(pair.revalidate(), (
            hashlib.sha256(self.receipt._capture.stdout).hexdigest(),
            hashlib.sha256(self.receipt.bytes).hexdigest()))
        self.assertEqual((self.owner.root / "evidence.json").read_bytes(),
                         self.receipt._capture.stdout)
        self.assertEqual((self.owner.root / "receipt.json").read_bytes(),
                         self.receipt.bytes)
        with self.assertRaisesRegex(ValueError, "already used"):
            self.owner.publish_once(receipt=self.receipt, frozen_row=self.row)

    def test_preexisting_destination_survives_without_overwrite(self):
        destination = self.owner.root / "evidence.json"
        destination.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "emptiness changed"):
            self.owner.publish_once(receipt=self.receipt, frozen_row=self.row)
        self.assertEqual(destination.read_bytes(), b"keep")
        self.assertFalse((self.owner.root / "receipt.json").exists())

    def test_changed_capture_and_receipt_reject_before_publication(self):
        self.receipt._capture.stdout = b"changed"
        with self.assertRaisesRegex(ValueError, "receipt and evidence differ"):
            self.owner.publish_once(receipt=self.receipt, frozen_row=self.row)
        self.assertEqual(os.listdir(self.owner.root), [])
        self.receipt = _portable_receipt()
        self.receipt.bytes += b" "
        with self.assertRaises(ValueError):
            self.owner.publish_once(receipt=self.receipt, frozen_row=self.row)
        self.assertEqual(os.listdir(self.owner.root), [])

    def test_mutation_after_first_peer_rolls_back_exact_peers(self):
        original = self.receipt.bytes
        from aegis360 import sparse_story_private_run_publication as module
        publish = module._publish_private_pair
        def changed(**kw):
            pair = publish(**kw)
            self.receipt.bytes = original + b" "
            return pair
        with mock.patch.object(module, "_publish_private_pair", side_effect=changed):
            with self.assertRaises(ValueError):
                self.owner.publish_once(receipt=self.receipt, frozen_row=self.row)
        self.assertEqual(os.listdir(self.owner.root), [])


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class PrivateRunPublicationHostTests(unittest.TestCase):
    def test_real_attested_fd_hygiene_publishes_exact_peers(self):
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
                    receipt = _build_private_synthetic_run_receipt(
                        claim=claim, frozen_row=row)
                    with tempfile.TemporaryDirectory() as parent:
                        owner = _OwnedPrivateRunRoot(Path(parent))
                        pair = owner.publish_once(receipt=receipt, frozen_row=row)
                        self.assertEqual((owner.root / "evidence.json").read_bytes(),
                                         capture.stdout)
                        self.assertEqual((owner.root / "receipt.json").read_bytes(),
                                         receipt.bytes)
                        self.assertEqual(pair.revalidate(), (
                            hashlib.sha256(capture.stdout).hexdigest(),
                            hashlib.sha256(receipt.bytes).hexdigest()))
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
