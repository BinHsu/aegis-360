"""Owned two-peer publication tests; no receipt or case authority."""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.sparse_story_private_publication import (  # noqa: E402
    PublicationIncomplete, _publish_private_pair,
)


def local_exclusive_rename(source, destination):
    if Path(destination).exists():
        raise ValueError("destination exists")
    os.rename(source, destination)


class PrivatePublicationTests(unittest.TestCase):
    def publish(self, root):
        return _publish_private_pair(
            evidence_path=root / "evidence.json",
            receipt_path=root / "receipt.json",
            evidence_bytes=b"opaque-evidence",
            receipt_bytes=b"opaque-receipt")

    def test_two_peers_publish_revalidate_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                pair = self.publish(root)
            self.assertEqual(pair.revalidate(), (
                hashlib.sha256(b"opaque-evidence").hexdigest(),
                hashlib.sha256(b"opaque-receipt").hexdigest()))
            self.assertNotIn(str(root), repr(pair))
            self.assertEqual(pair.cleanup(), ("receipt", "evidence"))
            self.assertFalse((root / "evidence.json").exists())
            self.assertFalse((root / "receipt.json").exists())

    def test_preexisting_second_peer_is_preserved_and_first_rolled_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "receipt.json").write_bytes(b"preexisting")
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                with self.assertRaises(ValueError):
                    self.publish(root)
            self.assertFalse((root / "evidence.json").exists())
            self.assertEqual((root / "receipt.json").read_bytes(), b"preexisting")

    def test_preexisting_first_peer_never_starts_second(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "evidence.json").write_bytes(b"preexisting")
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                with self.assertRaises(ValueError):
                    self.publish(root)
            self.assertEqual((root / "evidence.json").read_bytes(), b"preexisting")
            self.assertFalse((root / "receipt.json").exists())

    def test_changed_peer_blocks_cleanup_and_preserves_pair(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                pair = self.publish(root)
            (root / "receipt.json").chmod(0o644)
            (root / "receipt.json").write_bytes(b"changed")
            with self.assertRaises(PublicationIncomplete):
                pair.cleanup()
            self.assertEqual((root / "receipt.json").read_bytes(), b"changed")
            self.assertEqual((root / "evidence.json").read_bytes(), b"opaque-evidence")

    def test_replaced_peer_survives_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                pair = self.publish(root)
            os.rename(root / "receipt.json", root / "held-receipt.json")
            (root / "receipt.json").write_bytes(b"replacement")
            with self.assertRaises(PublicationIncomplete):
                pair.cleanup()
            self.assertEqual((root / "receipt.json").read_bytes(), b"replacement")
            self.assertEqual((root / "evidence.json").read_bytes(), b"opaque-evidence")

    def test_symlink_and_hardlink_peer_block_cleanup(self):
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                                side_effect=local_exclusive_rename):
                    pair = self.publish(root)
                receipt = root / "receipt.json"
                if kind == "symlink":
                    os.rename(receipt, root / "held-receipt.json")
                    receipt.symlink_to(root / "held-receipt.json")
                else:
                    os.link(receipt, root / "other-link.json")
                with self.assertRaises((PublicationIncomplete, OSError)):
                    pair.cleanup()
                self.assertTrue(receipt.is_file())
                self.assertEqual((root / "evidence.json").read_bytes(), b"opaque-evidence")

    def test_replaced_parent_blocks_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "published"
            parent.mkdir()
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                pair = self.publish(parent)
            os.rename(parent, root / "held-parent")
            parent.mkdir()
            (parent / "receipt.json").write_bytes(b"replacement")
            with self.assertRaises(PublicationIncomplete):
                pair.cleanup()
            self.assertEqual((parent / "receipt.json").read_bytes(), b"replacement")
            self.assertEqual((root / "held-parent" / "evidence.json").read_bytes(),
                             b"opaque-evidence")

    def test_blind_delete_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=local_exclusive_rename):
                pair = self.publish(root)
            os.rename(root / "receipt.json", root / "held-receipt.json")
            (root / "receipt.json").write_bytes(b"replacement")

            def preservation_assertion():
                try:
                    pair.cleanup()
                except PublicationIncomplete:
                    pass
                self.assertEqual((root / "receipt.json").read_bytes(),
                                 b"replacement")

            preservation_assertion()
            with mock.patch("aegis360.sparse_story_private_publication._verify",
                            return_value=None), mock.patch(
                    "aegis360.sparse_story_private_publication._remove_exact",
                    side_effect=lambda peer: peer.path.unlink()):
                with self.assertRaises(FileNotFoundError):
                    preservation_assertion()

    def test_replacement_during_second_publication_survives_rollback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = 0

            def replace_receipt_after_rename(source, destination):
                nonlocal calls
                calls += 1
                local_exclusive_rename(source, destination)
                if calls == 2:
                    os.rename(destination, root / "held-receipt.json")
                    Path(destination).write_bytes(b"replacement")

            with mock.patch("aegis360.sparse_story_private_publication._rename_exclusive",
                            side_effect=replace_receipt_after_rename):
                with self.assertRaises(PublicationIncomplete):
                    self.publish(root)
            self.assertEqual((root / "receipt.json").read_bytes(), b"replacement")
            self.assertFalse((root / "evidence.json").exists())
