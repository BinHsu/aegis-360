"""Actual two-peer publisher replacement observation and mutation control."""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.sparse_story_private_replacement_case import (  # noqa: E402
    _observe_private_replacement_race,
)
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    build_asset_manifest_shape, canonical_asset_manifest_shape_bytes,
)


def local_exclusive_rename(source, destination):
    if Path(destination).exists():
        raise ValueError("destination exists")
    os.rename(source, destination)


class PrivateReplacementCaseTests(unittest.TestCase):
    def inputs(self, root):
        support = build_asset_manifest_shape(asset_kind="synthetic_support",
                                             entries=[])
        argv = ("literal-race",)
        stdin = b"bound-stdin"
        row = {"case_id": "replacement_race",
               "expected_result": "replacement_preserved",
               "stimulus": {
                   "argv": list(argv),
                   "stdin_sha256": hashlib.sha256(stdin).hexdigest(),
                   "support_manifest_sha256": hashlib.sha256(
                       canonical_asset_manifest_shape_bytes(support)).hexdigest()}}
        return dict(frozen_row=row, argv=argv, stdin=stdin,
            support_manifest=support, private_root=root,
            evidence_bytes=b"owned-evidence", receipt_bytes=b"owned-receipt",
            replacement_evidence_bytes=b"replacement-evidence",
            replacement_receipt_bytes=b"replacement-receipt")

    def run_case(self, values):
        with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                        side_effect=local_exclusive_rename), mock.patch(
                "aegis360.sparse_story_private_replacement_case._rename_exclusive",
                side_effect=local_exclusive_rename):
            return _observe_private_replacement_race(**values)

    def test_actual_publisher_refuses_replaced_peers_and_preserves_four_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            result = self.run_case(self.inputs(root))
            self.assertTrue(result.revalidation_refused)
            self.assertTrue(result.cleanup_refused)
            self.assertTrue(result.originals_held)
            self.assertTrue(result.replacements_preserved)
            self.assertIsNone(result.case_result)
            self.assertNotIn(str(root), repr(result))
            self.assertEqual((root / "evidence.json").read_bytes(), b"replacement-evidence")
            self.assertEqual((root / "receipt.json").read_bytes(), b"replacement-receipt")
            self.assertEqual((root / "held-evidence.json").read_bytes(), b"owned-evidence")
            self.assertEqual((root / "held-receipt.json").read_bytes(), b"owned-receipt")

    @unittest.skipUnless(sys.platform == "darwin", "native exclusive rename requires macOS")
    def test_native_exclusive_rename_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            result = _observe_private_replacement_race(**self.inputs(root))
            self.assertTrue(result.replacements_preserved)
            self.assertEqual((root / "receipt.json").read_bytes(), b"replacement-receipt")

    def test_changed_frozen_stimulus_blocks_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            values = self.inputs(root)
            values["stdin"] = b"changed"
            with self.assertRaisesRegex(ValueError, "stimulus"):
                self.run_case(values)
            self.assertEqual(list(root.iterdir()), [])

    def test_blind_delete_control_fails_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)

            def blind_cleanup(self):
                self._evidence.path.unlink()
                self._receipt.path.unlink()

            with mock.patch("aegis360.sparse_story_private_publication._PrivatePublishedPair.cleanup",
                            blind_cleanup):
                with self.assertRaises(ValueError):
                    self.run_case(self.inputs(root))
            self.assertFalse((root / "evidence.json").exists())
            self.assertFalse((root / "receipt.json").exists())
            self.assertEqual((root / "held-evidence.json").read_bytes(), b"owned-evidence")
            self.assertEqual((root / "held-receipt.json").read_bytes(), b"owned-receipt")
