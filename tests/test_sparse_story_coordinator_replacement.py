"""Distinguishing checks for private replacement-safe owned-peer cleanup."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.sparse_story_coordinator_replacement import (  # noqa: E402
    _create_owned_peer, _observe_replacement_cleanup,
)


class ReplacementCleanupTests(unittest.TestCase):
    def row(self):
        return {"case_id": "replacement_race",
                "expected_result": "replacement_preserved",
                "stimulus": {"argv": [], "stdin_sha256": "0" * 64,
                             "support_manifest_sha256": "1" * 64}}

    def prepare(self, root):
        names = (root / "receipt.json", root / "evidence.json")
        originals = tuple(_create_owned_peer(name, f"original-{i}".encode())
                          for i, name in enumerate(names))
        for i, name in enumerate(names):
            os.rename(name, root / f"held-{i}")
        replacements = tuple(_create_owned_peer(name, f"replacement-{i}".encode())
                             for i, name in enumerate(names))
        return originals, replacements

    def test_replacement_survives_exact_owner_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            originals, replacements = self.prepare(root)
            frozen = self.row()
            result = _observe_replacement_cleanup(
                frozen_row=frozen, actual_row=self.row(),
                owned_peers=originals, replacement_peers=replacements)
            self.assertTrue(result.cleanup_attempted)
            self.assertTrue(result.replacement_peers_preserved)
            self.assertIsNone(result.case_result)
            self.assertEqual((root / "receipt.json").read_bytes(), b"replacement-0")
            self.assertEqual((root / "evidence.json").read_bytes(), b"replacement-1")
            self.assertEqual((root / "held-0").read_bytes(), b"original-0")
            self.assertEqual((root / "held-1").read_bytes(), b"original-1")

    def test_blind_cleanup_negative_control_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            originals, replacements = self.prepare(root)
            frozen = self.row()
            with mock.patch(
                    "aegis360.sparse_story_coordinator_replacement._remove_owned_file",
                    side_effect=lambda path, identity: path.unlink()):
                with self.assertRaises(FileNotFoundError):
                    _observe_replacement_cleanup(
                        frozen_row=frozen, actual_row=self.row(),
                        owned_peers=originals, replacement_peers=replacements)
            self.assertFalse((root / "receipt.json").exists())

    def test_changed_row_or_replacement_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            originals, replacements = self.prepare(root)
            frozen = self.row()
            changed = self.row(); changed["stimulus"]["argv"] = ["changed"]
            with self.assertRaisesRegex(ValueError, "binding"):
                _observe_replacement_cleanup(
                    frozen_row=frozen, actual_row=changed,
                    owned_peers=originals, replacement_peers=replacements)
            (root / "evidence.json").write_bytes(b"altered")
            with self.assertRaisesRegex(ValueError, "changed"):
                _observe_replacement_cleanup(
                    frozen_row=frozen, actual_row=self.row(),
                    owned_peers=originals, replacement_peers=replacements)
            self.assertEqual((root / "receipt.json").read_bytes(), b"replacement-0")
