import errno
import copy
import os
import pickle
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    MAX_DEPTH, MAX_LEAF_BYTES, MAX_LEAVES, MAX_TOTAL_BYTES,
    _AssetTreeProof, _observe_asset_manifest_shape, _observe_asset_tree,
    _validate_runtime_entrypoint, validate_asset_tree,
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


def thin_macho(cpu_type=0x0100000C, cpu_subtype=0, file_type=2,
               load_command=None):
    if load_command is None:
        load_command = struct.pack("<IIQQ", 0x80000028, 24, 0, 0)
    command_count = 0 if not load_command else 1
    return struct.pack("<IiiIIIII", 0xFEEDFACF, cpu_type, cpu_subtype,
                       file_type, command_count, len(load_command), 0, 0) + load_command


def universal_macho(cpu_type=0x0100000C, *, fat64=False):
    entry_size = 32 if fat64 else 20
    offset = 8 + entry_size
    payload = thin_macho(cpu_type)
    magic = 0xCAFEBABF if fat64 else 0xCAFEBABE
    if fat64:
        row = struct.pack(">iiQQII", cpu_type, 0, offset, len(payload), 0, 0)
    else:
        row = struct.pack(">iiIII", cpu_type, 0, offset, len(payload), 0)
    return struct.pack(">II", magic, 1) + row + payload


class SparseStoryAssetTreeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.uname = mock.patch("aegis360.sparse_story_asset_tree.os.uname",
            return_value=SimpleNamespace(sysname="Darwin", machine="arm64"))
        self.uname.start()

    def tearDown(self):
        self.uname.stop()
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

    def test_retained_proof_cannot_be_copied_or_pickled(self):
        root = self.base / "noncopyable"
        root.mkdir(); (root / "value").write_bytes(b"value"); seal(root)
        manifest = self.precommit(root)
        with validate_asset_tree(manifest=manifest, root=root) as proof:
            for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                with self.assertRaises(TypeError): operation(proof)

    def test_runtime_entrypoint_and_empty_support_use_precommit(self):
        runtime = self.base / "runtime"
        (runtime / "bin").mkdir(parents=True)
        entrypoint = runtime / "bin" / "adapter"
        entrypoint.write_bytes(thin_macho())
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

    def test_runtime_rejects_script_malformed_and_thin_wrong_architecture(self):
        for name, content in (
                ("script", b"#!/bin/false\n"),
                ("malformed", b"not a native executable"),
                ("wrong-architecture", thin_macho(0x01000007)),
                ("arm64e-subtype", thin_macho(cpu_subtype=2)),
                ("wrong-file-type", thin_macho(file_type=6)),
                ("swapped-magic", b"\xfe\xed\xfa\xcf" + thin_macho()[4:])):
            with self.subTest(name=name):
                runtime = self.base / name
                runtime.mkdir()
                entrypoint = runtime / "adapter"
                entrypoint.write_bytes(content)
                entrypoint.chmod(0o555)
                runtime.chmod(0o555)
                with self.assertRaisesRegex(ValueError, "Mach-O|architecture"):
                    self.precommit(runtime, "runtime", "adapter")

    def test_runtime_accepts_only_thin_host_architecture(self):
        runtime = self.base / "thin"
        runtime.mkdir()
        entrypoint = runtime / "adapter"
        entrypoint.write_bytes(thin_macho())
        entrypoint.chmod(0o555)
        runtime.chmod(0o555)
        manifest = self.precommit(runtime, "runtime", "adapter")
        with validate_asset_tree(manifest=manifest, root=runtime) as proof:
            self.assertEqual(proof.manifest(), manifest)

    def test_runtime_requires_kernel_darwin_arm64_host_facts(self):
        runtime = self.base / "host-facts"
        runtime.mkdir()
        entrypoint = runtime / "adapter"
        entrypoint.write_bytes(thin_macho())
        entrypoint.chmod(0o555)
        runtime.chmod(0o555)
        for sysname, machine in (("Linux", "arm64"), ("Darwin", "x86_64")):
            with self.subTest(sysname=sysname, machine=machine), mock.patch(
                    "aegis360.sparse_story_asset_tree.os.uname",
                    return_value=SimpleNamespace(sysname=sysname, machine=machine)):
                with self.assertRaisesRegex(ValueError, "host"):
                    self.precommit(runtime, "runtime", "adapter")
        with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                        return_value=SimpleNamespace(sysname="Darwin", machine="arm64")):
            self.assertEqual(self.precommit(runtime, "runtime", "adapter")
                             ["entrypoint"], "adapter")

    def test_runtime_rejects_every_universal_binary(self):
        for name, content in (
                ("fat-host", universal_macho()),
                ("fat64-host", universal_macho(fat64=True)),
                ("fat-without-host", universal_macho(0x01000007))):
            with self.subTest(name=name):
                runtime = self.base / name
                runtime.mkdir()
                entrypoint = runtime / "adapter"
                entrypoint.write_bytes(content)
                entrypoint.chmod(0o555)
                runtime.chmod(0o555)
                with self.assertRaisesRegex(ValueError, "thin"):
                    self.precommit(runtime, "runtime", "adapter")

    def test_runtime_rejects_truncated_and_overflowing_load_command_tables(self):
        truncated = struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0,
                                2, 1, 8, 0, 0) + b"\x00" * 4
        overflowing = struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0,
                                  2, 1, 0xFFFFFFFF, 0, 0)
        malformed_command = (struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C,
                                         0, 2, 1, 8, 0, 0)
                             + struct.pack("<II", 1, 0xFFFFFFFF))
        unaligned_command = (struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C,
                                         0, 2, 1, 9, 0, 0)
                             + struct.pack("<II", 1, 9) + b"x")
        cases = (
            ("truncated-table", truncated),
            ("overflowing-table", overflowing),
            ("overflowing-command", malformed_command),
            ("unaligned-command", unaligned_command),
        )
        for name, content in cases:
            with self.subTest(name=name):
                runtime = self.base / name
                runtime.mkdir()
                entrypoint = runtime / "adapter"
                entrypoint.write_bytes(content)
                entrypoint.chmod(0o555)
                runtime.chmod(0o555)
                with self.assertRaisesRegex(ValueError, "truncated|exceeds|malformed"):
                    self.precommit(runtime, "runtime", "adapter")

    def test_runtime_parser_bounds_pread_and_accepts_exact_command_tables(self):
        zero = thin_macho(load_command=b"")
        two_commands = (struct.pack("<II", 1, 8)
                        + struct.pack("<II", 2, 8))
        multiple = (struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C,
                                0, 2, 2, len(two_commands), 0, 0)
                    + two_commands)
        for content in (zero, multiple):
            path = self.base / f"commands-{len(content)}"
            path.write_bytes(content)
            fd = os.open(path, os.O_RDONLY)
            try:
                _validate_runtime_entrypoint(fd)
            finally:
                os.close(fd)

        huge_size = 0xFFFFFFF8
        huge = (struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C,
                            0, 2, 1, huge_size, 0, 0)
                + struct.pack("<II", 1, huge_size))
        path = self.base / "huge-command"
        path.write_bytes(huge)
        fd = os.open(path, os.O_RDONLY)
        real_pread = os.pread
        requests = []

        def observe_pread(selected_fd, length, offset):
            requests.append(length)
            return real_pread(selected_fd, length, offset)

        try:
            with mock.patch("aegis360.sparse_story_asset_tree.os.fstat",
                    return_value=SimpleNamespace(st_size=32 + huge_size)), \
                 mock.patch("aegis360.sparse_story_asset_tree.os.pread",
                            side_effect=observe_pread):
                _validate_runtime_entrypoint(fd)
        finally:
            os.close(fd)
        self.assertTrue(requests)
        self.assertLessEqual(max(requests), 32)

    def test_runtime_parser_rejects_short_pread(self):
        path = self.base / "short-pread"
        path.write_bytes(thin_macho())
        fd = os.open(path, os.O_RDONLY)
        try:
            with mock.patch("aegis360.sparse_story_asset_tree.os.pread",
                            return_value=b"\xcf\xfa\xed"):
                with self.assertRaisesRegex(ValueError, "truncated"):
                    _validate_runtime_entrypoint(fd)
        finally:
            os.close(fd)

    def test_runtime_entrypoint_replacement_remains_detected(self):
        runtime = self.base / "replace-runtime"
        runtime.mkdir()
        entrypoint = runtime / "adapter"
        entrypoint.write_bytes(thin_macho())
        entrypoint.chmod(0o555)
        runtime.chmod(0o555)
        manifest = self.precommit(runtime, "runtime", "adapter")
        proof = validate_asset_tree(manifest=manifest, root=runtime)
        try:
            runtime.chmod(0o755)
            entrypoint.unlink()
            entrypoint.write_bytes(thin_macho())
            entrypoint.chmod(0o555)
            runtime.chmod(0o555)
            with self.assertRaisesRegex(ValueError, "identity"):
                proof.manifest()
        finally:
            proof.close()

    def test_runtime_replacement_during_validation_and_hash_is_detected(self):
        runtime = self.base / "replace-during-hash"
        runtime.mkdir()
        entrypoint = runtime / "adapter"
        entrypoint.write_bytes(thin_macho())
        entrypoint.chmod(0o555)
        runtime.chmod(0o555)
        manifest = self.precommit(runtime, "runtime", "adapter")
        proof = validate_asset_tree(manifest=manifest, root=runtime)
        original = _validate_runtime_entrypoint

        def validate_then_replace(fd):
            original(fd)
            runtime.chmod(0o755)
            entrypoint.unlink()
            entrypoint.write_bytes(thin_macho())
            entrypoint.chmod(0o555)
            runtime.chmod(0o555)

        try:
            with mock.patch("aegis360.sparse_story_asset_tree._validate_runtime_entrypoint",
                            side_effect=validate_then_replace):
                with self.assertRaisesRegex(ValueError, "changed while hashing"):
                    proof.manifest()
        finally:
            proof.close()

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
