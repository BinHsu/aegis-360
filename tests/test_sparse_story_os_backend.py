import os
import plistlib
import stat
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_os_backend import (  # noqa: E402
    _CPU_SUBTYPE_ARM64E_RAW, _DarwinNative, _MountFacts, _OSBackendProof,
    _check_nodes, _check_records, _identity, _observe_os_backend,
    _observe_test_os_backend,
    _validate_universal_backend,
)


def thin(subtype=_CPU_SUBTYPE_ARM64E_RAW):
    command = struct.pack("<II", 1, 8)
    return struct.pack("<IIIIIIII", 0xFEEDFACF, 0x0100000C, subtype, 2,
                       1, len(command), 0, 0) + command


def fat(payload=None, subtype=_CPU_SUBTYPE_ARM64E_RAW):
    payload = thin(subtype) if payload is None else payload
    offset = 4096
    row = struct.pack(">IIIII", 0x0100000C, subtype, offset, len(payload), 12)
    return struct.pack(">II", 0xCAFEBABE, 1) + row + bytes(offset - 28) + payload


def multi_fat(rows):
    header_size = 8 + 20 * len(rows)
    result = bytearray(struct.pack(">II", 0xCAFEBABE, len(rows)))
    for cpu, subtype, offset, payload in rows:
        result.extend(struct.pack(">IIIII", cpu, subtype, offset, len(payload), 12))
    if len(result) != header_size: raise AssertionError
    for _, _, offset, payload in rows:
        if len(result) < offset: result.extend(bytes(offset - len(result)))
        result.extend(payload)
    return bytes(result)


class FakeNative:
    def __init__(self, build="25F84"):
        self.build = build
        self.mount = _MountFacts((1, 2), 1, "apfs")

    def fstatfs(self, _fd): return self.mount
    def osversion(self): return self.build


class OSBackendParserTests(unittest.TestCase):
    def validate(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fat"
            path.write_bytes(content)
            fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC)
            try: _validate_universal_backend(fd, len(content))
            finally: os.close(fd)

    def test_bounded_fat32_arm64e_is_accepted(self): self.validate(fat())

    def test_wrong_raw_subtype_and_malformed_commands_fail(self):
        with self.assertRaisesRegex(ValueError, "subtype"):
            self.validate(fat(subtype=2))
        malformed = struct.pack("<IIIIIIIIII", 0xFEEDFACF, 0x0100000C,
            _CPU_SUBTYPE_ARM64E_RAW, 2, 1, 8, 0, 0, 1, 7)
        with self.assertRaisesRegex(ValueError, "command"):
            self.validate(fat(malformed))

    def test_duplicate_disjoint_aligned_nonhost_rows_are_rejected(self):
        content = multi_fat([
            (7, 3, 4096, b"x"), (7, 3, 8192, b"y"),
            (0x0100000C, _CPU_SUBTYPE_ARM64E_RAW, 12288, thin()),
        ])
        with self.assertRaisesRegex(ValueError, "duplicated"):
            self.validate(content)

    def test_multiple_host_rows_are_rejected(self):
        content = multi_fat([
            (0x0100000C, _CPU_SUBTYPE_ARM64E_RAW, 4096, thin()),
            (0x0100000C, _CPU_SUBTYPE_ARM64E_RAW, 8192, thin()),
        ])
        with self.assertRaisesRegex(ValueError, "duplicated"):
            self.validate(content)

    def test_fat_container_negative_matrix(self):
        cases = {
            "count": struct.pack(">II", 0xCAFEBABE, 0),
            "table": struct.pack(">II", 0xCAFEBABE, 1),
            "range": struct.pack(">II", 0xCAFEBABE, 1) +
                     struct.pack(">IIIII", 0x0100000C, _CPU_SUBTYPE_ARM64E_RAW,
                                 4096, 1, 12),
            "size": struct.pack(">II", 0xCAFEBABE, 1) +
                    struct.pack(">IIIII", 0x0100000C, _CPU_SUBTYPE_ARM64E_RAW,
                                28, 0, 0),
            "alignment": struct.pack(">II", 0xCAFEBABE, 1) +
                         struct.pack(">IIIII", 0x0100000C,
                                     _CPU_SUBTYPE_ARM64E_RAW, 29, 1, 2) + b"x",
            "missing": multi_fat([(7, 3, 4096, b"x")]),
        }
        overlap = bytearray(multi_fat([
            (7, 3, 4096, b"x" * 4097),
            (0x0100000C, _CPU_SUBTYPE_ARM64E_RAW, 8192, thin()),
        ]))
        cases["overlap"] = bytes(overlap)
        for name, content in cases.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.validate(content)

    def test_thin_header_negative_matrix_and_short_pread(self):
        base = bytearray(thin())
        variants = []
        for offset, value in ((0, 0), (4, 7), (12, 6)):
            changed = bytearray(base); struct.pack_into("<I", changed, offset, value)
            variants.append(changed)
        trailing = bytearray(base); struct.pack_into("<I", trailing, 16, 0)
        variants.append(trailing)
        for payload in variants:
            with self.assertRaises(ValueError): self.validate(fat(bytes(payload)))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fat"; content = fat(); path.write_bytes(content)
            fd = os.open(path, os.O_RDONLY)
            try:
                with mock.patch("aegis360.sparse_story_os_backend.os.pread",
                                return_value=b"x"):
                    with self.assertRaisesRegex(ValueError, "truncated"):
                        _validate_universal_backend(fd, len(content))
            finally: os.close(fd)

    def test_parser_pread_requests_are_bounded(self):
        content = fat()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fat"; path.write_bytes(content)
            fd = os.open(path, os.O_RDONLY)
            real = os.pread; requests = []
            def observed(selected, length, offset):
                requests.append(length); return real(selected, length, offset)
            try:
                with mock.patch("aegis360.sparse_story_os_backend.os.pread",
                                side_effect=observed):
                    _validate_universal_backend(fd, len(content))
            finally: os.close(fd)
        self.assertLessEqual(max(requests), 32)

    def test_proof_constructor_is_opaque(self):
        with self.assertRaises(TypeError):
            _OSBackendProof(None, native=None, records=[], mounts=[], backend_hash="",
                            backend_size=0, system_hash="", os_build="")

    def test_manifest_facts_return_size_frozen_with_hash(self):
        proof = _OSBackendProof.__new__(_OSBackendProof)
        proof._os_build = "25F84"; proof._backend_hash = "a" * 64
        proof._backend_size = 123; proof._system_hash = "b" * 64
        proof.revalidate = mock.Mock()
        with mock.patch("aegis360.sparse_story_os_backend.os.fstat",
                        side_effect=AssertionError("fresh fstat is forbidden")):
            self.assertEqual(proof._manifest_facts(),
                ("25F84", "a" * 64, 123, "b" * 64))

    @unittest.skipUnless(sys.platform == "darwin" and os.uname().machine == "arm64",
                         "retained fixed OS paths require Darwin arm64")
    def test_retained_opens_are_nofollow_cloexec_and_native_build_must_match(self):
        plist = plistlib.loads(Path(
            "/System/Library/CoreServices/SystemVersion.plist").read_bytes())
        real_open = os.open
        flags = []
        def observed(path, selected_flags, *args, **kwargs):
            flags.append(selected_flags)
            return real_open(path, selected_flags, *args, **kwargs)
        with mock.patch("aegis360.sparse_story_os_backend.os.open",
                        side_effect=observed):
            with _observe_test_os_backend(
                    native=FakeNative(plist["ProductBuildVersion"])) as proof:
                proof.revalidate()
        self.assertEqual(len(flags), 4)
        self.assertTrue(all(value & os.O_NOFOLLOW and value & os.O_CLOEXEC
                            for value in flags))
        with self.assertRaisesRegex(ValueError, "kernel build"):
            _observe_test_os_backend(native=FakeNative("wrong-build"))

    def test_node_predicates_reject_nonregular_and_bad_mount_or_ownership(self):
        def fact(mode=stat.S_IFREG | 0o444, uid=0, gid=0, nlink=1, flags=0x80000):
            return SimpleNamespace(st_dev=1, st_ino=2, st_uid=uid, st_gid=gid,
                st_mode=mode, st_nlink=nlink, st_size=4, st_mtime_ns=5,
                st_ctime_ns=6, st_flags=flags)
        good = fact(); record = ("leaf", 9, _identity(good), 8, 0o444, False)
        mount = _MountFacts((1, 2), 1, "apfs")
        for name, changed, access, native_mount in (
            ("fifo", fact(stat.S_IFIFO | 0o444), False, mount),
            ("uid", fact(uid=1), False, mount), ("gid", fact(gid=1), False, mount),
            ("mode", fact(mode=stat.S_IFREG | 0o400), False, mount),
            ("link", fact(nlink=2), False, mount), ("flags", fact(flags=0), False, mount),
            ("access", good, True, mount),
            ("filesystem", good, False, _MountFacts((1, 2), 1, "hfs")),
            ("readonly", good, False, _MountFacts((1, 2), 0, "apfs")),
        ):
            with self.subTest(name=name), mock.patch(
                    "aegis360.sparse_story_os_backend.os.fstat", return_value=changed), \
                 mock.patch("aegis360.sparse_story_os_backend.os.stat",
                            return_value=changed), \
                 mock.patch("aegis360.sparse_story_os_backend.os.access",
                            return_value=access):
                native = FakeNative(); native.mount = native_mount
                with self.assertRaises(ValueError): _check_nodes(native, [record], (mount,))

        class SplitNative(FakeNative):
            def __init__(self): super().__init__(); self.number = 0
            def fstatfs(self, _fd):
                self.number += 1
                return _MountFacts((self.number, 2), 1, "apfs")
        with mock.patch("aegis360.sparse_story_os_backend.os.fstat", return_value=good), \
             mock.patch("aegis360.sparse_story_os_backend.os.stat", return_value=good), \
             mock.patch("aegis360.sparse_story_os_backend.os.access", return_value=False):
            with self.assertRaisesRegex(ValueError, "one filesystem"):
                _check_nodes(SplitNative(), [record, record],
                             (_MountFacts((1, 2), 1, "apfs"),
                              _MountFacts((2, 2), 1, "apfs")))

    def test_content_hash_plist_and_build_mutations_fail_closed(self):
        records = [("parent", 1), ("backend", 2), ("system-parent", 3),
                   ("system", 4)]
        good_plist = plistlib.dumps({"ProductName": "macOS",
                                     "ProductBuildVersion": "25F84"})
        with mock.patch("aegis360.sparse_story_os_backend._check_nodes"), \
             mock.patch("aegis360.sparse_story_os_backend._validate_universal_backend"), \
             mock.patch("aegis360.sparse_story_os_backend.os.fstat",
                        return_value=SimpleNamespace(st_size=10)), \
             mock.patch("aegis360.sparse_story_os_backend._hash_fd",
                        side_effect=[(10, "wrong", b""),
                                     (10, "system", good_plist)]):
            with self.assertRaisesRegex(ValueError, "content changed"):
                _check_records(FakeNative(), records, (), "backend", "system", "25F84")
        bad_plists = [plistlib.dumps({"ProductName": "OS X",
                                      "ProductBuildVersion": "25F84"}),
                      plistlib.dumps({"ProductName": "macOS",
                                      "ProductBuildVersion": "other"}), b"not-plist"]
        for payload in bad_plists:
            with mock.patch("aegis360.sparse_story_os_backend._check_nodes"), \
                 mock.patch("aegis360.sparse_story_os_backend._validate_universal_backend"), \
                 mock.patch("aegis360.sparse_story_os_backend.os.fstat",
                            return_value=SimpleNamespace(st_size=10)), \
                 mock.patch("aegis360.sparse_story_os_backend._hash_fd",
                            side_effect=[(10, "backend", b""),
                                         (len(payload), "system", payload)]):
                with self.assertRaises(ValueError):
                    _check_records(FakeNative(), records, (), "backend", "system", "25F84")

    def test_sysctl_two_call_validation_matrix(self):
        class Libc:
            def __init__(self, data=b"25F84\0", first=0, second=0,
                         announced=None, returned=None):
                self.data, self.first, self.second = data, first, second
                self.announced = len(data) if announced is None else announced
                self.returned = len(data) if returned is None else returned
                self.calls = 0
            def sysctlbyname(self, _name, output, length, _new, _newlen):
                self.calls += 1
                if output is None:
                    length._obj.value = self.announced; return self.first
                if self.second == 0:
                    for i, value in enumerate(self.data[:self.announced]): output[i] = value
                    length._obj.value = self.returned
                return self.second
        cases = [Libc(first=-1), Libc(second=-1), Libc(announced=1),
                 Libc(announced=130), Libc(data=b"25F84"), Libc(data=b"A\0B\0"),
                 Libc(data=b"\xff\0"), Libc(data=b"bad token\0"),
                 Libc(returned=3)]
        for libc in cases:
            native = _DarwinNative.__new__(_DarwinNative); native._libc = libc
            with self.assertRaises((ValueError, OSError)): native.osversion()
        native = _DarwinNative.__new__(_DarwinNative); native._libc = Libc()
        self.assertEqual(native.osversion(), "25F84")

    def test_close_attempts_every_fd_and_is_idempotent(self):
        proof = _OSBackendProof.__new__(_OSBackendProof)
        proof._closed = False; proof._records = [("a", 4), ("b", 5), ("c", 6)]
        calls = []
        def closing(fd):
            calls.append(fd)
            if fd == 5: raise OSError("synthetic")
        with mock.patch("aegis360.sparse_story_os_backend.os.close",
                        side_effect=closing):
            with self.assertRaises(OSError): proof.close()
            proof.close()
        self.assertEqual(calls, [6, 5, 4])


@unittest.skipUnless(os.environ.get("AEGIS_RUN_HOST_OS_BACKEND_TESTS") == "1",
                     "set AEGIS_RUN_HOST_OS_BACKEND_TESTS=1 for retained host observation")
class OSBackendHostTests(unittest.TestCase):
    def test_real_host_observation_revalidates_and_closes(self):
        with _observe_os_backend() as proof:
            proof.revalidate()
            self.assertFalse(hasattr(proof, "backend_path"))
        with self.assertRaisesRegex(ValueError, "closed"):
            proof.revalidate()


if __name__ == "__main__": unittest.main()
