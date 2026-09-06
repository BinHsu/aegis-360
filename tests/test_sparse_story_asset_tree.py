import errno
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    MAX_DEPTH, MAX_LEAF_BYTES, MAX_LEAVES, MAX_TOTAL_BYTES,
    _AssetTreeProof, _observe_asset_manifest_shape, _observe_asset_tree,
    validate_asset_tree,
)


def seal(root):
    for node in sorted((p for p in root.rglob("*") if p.is_dir()),
                       key=lambda p: len(p.parts), reverse=True):
        node.chmod(0o555)
    for node in root.rglob("*"):
        if node.is_file() and not node.is_symlink():
            node.chmod(0o444)
    root.chmod(0o555)


def unseal(root):
    if not root.exists() or root.is_symlink():
        return
    for node in root.rglob("*"):
        if node.is_dir():
            node.chmod(0o755)
        elif not node.is_symlink():
            node.chmod(0o644)
    root.chmod(0o755)


class SparseStoryAssetTreeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)

    def tearDown(self):
        for node in self.base.iterdir():
            unseal(node)
        self.temporary.cleanup()

    def precommit(self, root, asset_kind="model", entrypoint=None):
        before = len(os.listdir("/dev/fd"))
        manifest = _observe_asset_manifest_shape(
            root=root, asset_kind=asset_kind, entrypoint=entrypoint)
        self.assertEqual(len(os.listdir("/dev/fd")), before)
        return manifest

    def test_precommitted_model_manifest_is_only_public_proof_path(self):
        root = self.base / "model"
        (root / "weights").mkdir(parents=True)
        (root / "config.json").write_bytes(b"config")
        (root / "weights" / "one.bin").write_bytes(b"weights")
        seal(root)
        manifest = self.precommit(root)
        with validate_asset_tree(manifest=manifest, root=root) as proof:
            self.assertEqual(proof.manifest(), manifest)
            device, inode, digest = proof.backend_identity()
            self.assertEqual((device, inode), (root.stat().st_dev, root.stat().st_ino))
            self.assertEqual(len(digest), 64)
            self.assertFalse(hasattr(proof, "root_fd"))
        with self.assertRaisesRegex(ValueError, "closed"):
            proof.manifest()
        with self.assertRaises(TypeError):
            _AssetTreeProof(None, root=root, parent_fd=-1, root_fd=-1,
                            root_frozen=(), directories=[], leaves=[], children={},
                            asset_kind="model", entrypoint=None)

    def test_runtime_entrypoint_and_empty_support_use_precommit(self):
        runtime = self.base / "runtime"
        (runtime / "bin").mkdir(parents=True)
        entrypoint = runtime / "bin" / "adapter"
        entrypoint.write_bytes(b"#!/bin/false")
        entrypoint.chmod(0o555)
        runtime.chmod(0o555)
        (runtime / "bin").chmod(0o555)
        manifest = self.precommit(runtime, "runtime", "bin/adapter")
        with validate_asset_tree(manifest=manifest, root=runtime) as proof:
            self.assertEqual(proof.manifest()["entries"][0]["mode"], 0o555)
        support = self.base / "support"
        support.mkdir()
        support.chmod(0o555)
        manifest = self.precommit(support, "synthetic_support")
        with validate_asset_tree(manifest=manifest, root=support) as proof:
            self.assertEqual(proof.manifest()["entries"], [])

    def test_root_and_directory_utime_do_not_invalidate_proof(self):
        root = self.base / "asset"
        nested = root / "nested"
        nested.mkdir(parents=True)
        (nested / "value").write_bytes(b"stable")
        seal(root)
        manifest = self.precommit(root)
        with validate_asset_tree(manifest=manifest, root=root) as proof:
            os.utime(root, ns=(root.stat().st_atime_ns, root.stat().st_mtime_ns + 1_000_000))
            os.utime(nested, ns=(nested.stat().st_atime_ns,
                                 nested.stat().st_mtime_ns + 1_000_000))
            self.assertEqual(proof.manifest(), manifest)

    def test_replacement_and_extra_nodes_fail_precommitted_validation(self):
        root = self.base / "asset"
        root.mkdir()
        leaf = root / "value"
        leaf.write_bytes(b"original")
        seal(root)
        manifest = self.precommit(root)
        root.chmod(0o755)
        leaf.unlink()
        leaf.write_bytes(b"replacement")
        leaf.chmod(0o444)
        root.chmod(0o555)
        with self.assertRaises(ValueError):
            validate_asset_tree(manifest=manifest, root=root)

        unseal(root)
        leaf.write_bytes(b"original")
        seal(root)
        manifest = self.precommit(root)
        root.chmod(0o755)
        (root / "extra").mkdir()
        (root / "extra").chmod(0o555)
        root.chmod(0o555)
        with self.assertRaises(ValueError):
            validate_asset_tree(manifest=manifest, root=root)

    def test_raw_observer_rejects_symlink_hardlink_empty_dir_and_bounds(self):
        empty = self.base / "empty-dir"
        (empty / "unused").mkdir(parents=True)
        seal(empty)
        with self.assertRaisesRegex(ValueError, "directory set"):
            _observe_asset_tree(root=empty, asset_kind="synthetic_support")
        symlink = self.base / "symlink"
        symlink.mkdir()
        (symlink / "link").symlink_to("outside")
        symlink.chmod(0o555)
        with self.assertRaises(ValueError):
            _observe_asset_tree(root=symlink, asset_kind="model")
        hardlink = self.base / "hardlink"
        hardlink.mkdir()
        leaf = hardlink / "a"
        leaf.write_bytes(b"same")
        os.link(leaf, hardlink / "b")
        seal(hardlink)
        with self.assertRaisesRegex(ValueError, "leaf"):
            _observe_asset_tree(root=hardlink, asset_kind="model")

        deep = self.base / "deep"
        node = deep
        for number in range(17):
            node = node / f"d{number}"
            node.mkdir(parents=True, exist_ok=True)
        (node / "leaf").write_bytes(b"x")
        seal(deep)
        with self.assertRaisesRegex(ValueError, "depth"):
            _observe_asset_tree(root=deep, asset_kind="model")

    def test_manifest_bounds_preflight_before_any_filesystem_open(self):
        base_entry = {"relative_path": "x", "mode": 0o444, "size": 0,
                      "sha256": "0" * 64}
        cases = [
            ({"entries": [base_entry] * (MAX_LEAVES + 1)}, "leaf count"),
            ({"entries": [{**base_entry, "relative_path": "/".join(
                ["d"] * (MAX_DEPTH + 1))}]}, "depth"),
            ({"entries": [{**base_entry, "size": MAX_LEAF_BYTES + 1}]}, "leaf size"),
            ({"entries": [{**base_entry, "relative_path": str(i),
                            "size": MAX_LEAF_BYTES} for i in range(5)]}, "total size"),
        ]
        for partial, message in cases:
            manifest = {"asset_kind": "model", "entrypoint": None,
                        "root_tree_sha256": "0" * 64, **partial}
            with self.subTest(message=message):
                with mock.patch("aegis360.sparse_story_asset_tree.os.open") as opened:
                    with self.assertRaisesRegex(ValueError, message):
                        validate_asset_tree(manifest=manifest,
                                            root=self.base / "does-not-exist")
                    opened.assert_not_called()
        self.assertEqual((MAX_LEAVES, MAX_DEPTH, MAX_LEAF_BYTES, MAX_TOTAL_BYTES),
                         (4096, 16, 16 * 1024 ** 3, 64 * 1024 ** 3))

    def test_close_attempts_all_descriptors_after_external_close(self):
        root = self.base / "close"
        root.mkdir()
        (root / "a").write_bytes(b"a")
        (root / "b").write_bytes(b"b")
        seal(root)
        manifest = self.precommit(root)
        before = len(os.listdir("/dev/fd"))
        proof = validate_asset_tree(manifest=manifest, root=root)
        os.close(proof._leaves[0][1])
        with self.assertRaises(OSError):
            proof.close()
        self.assertEqual(len(os.listdir("/dev/fd")), before)
        proof.close()
        with self.assertRaisesRegex(ValueError, "closed"):
            proof.manifest()

    def test_injected_close_error_does_not_leak_or_leave_proof_open(self):
        root = self.base / "close-error"
        root.mkdir()
        (root / "a").write_bytes(b"a")
        (root / "b").write_bytes(b"b")
        seal(root)
        manifest = self.precommit(root)
        before = len(os.listdir("/dev/fd"))
        proof = validate_asset_tree(manifest=manifest, root=root)
        target = proof._leaves[0][1]
        real_close = os.close
        calls = []

        def close_then_report(fd):
            calls.append(fd)
            real_close(fd)
            if fd == target:
                raise OSError(errno.EIO, "synthetic close report")

        expected = len(proof._leaves) + len(proof._directories) + 2
        with mock.patch("aegis360.sparse_story_asset_tree.os.close",
                        side_effect=close_then_report):
            with self.assertRaisesRegex(OSError, "synthetic"):
                proof.close()
        self.assertEqual(len(calls), expected)
        self.assertEqual(len(os.listdir("/dev/fd")), before)
        with self.assertRaisesRegex(ValueError, "closed"):
            proof.manifest()

    def test_descriptor_exhaustion_fails_closed_without_leak(self):
        root = self.base / "fd-limit"
        root.mkdir()
        (root / "a").write_bytes(b"a")
        (root / "b").write_bytes(b"b")
        seal(root)
        real_open = os.open
        before = len(os.listdir("/dev/fd"))

        def exhaust(path, *args, **kwargs):
            if path == "b" and kwargs.get("dir_fd") is not None:
                raise OSError(errno.EMFILE, "synthetic fd exhaustion")
            return real_open(path, *args, **kwargs)

        with mock.patch("aegis360.sparse_story_asset_tree.os.open", side_effect=exhaust):
            with self.assertRaisesRegex(ValueError, "descriptor capacity"):
                _observe_asset_manifest_shape(root=root, asset_kind="model")
        self.assertEqual(len(os.listdir("/dev/fd")), before)


if __name__ == "__main__":
    unittest.main()
