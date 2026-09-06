"""Retained, non-authoritative facts for the frozen macOS Seatbelt backend."""

from __future__ import annotations

import ctypes
import hashlib
import os
import plistlib
import stat
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

_TOKEN = object()
_BACKEND = Path("/usr/bin/sandbox-exec")
_SYSTEM_VERSION = Path("/System/Library/CoreServices/SystemVersion.plist")
_SF_RESTRICTED = 0x00080000
_MNT_RDONLY = 0x00000001
_CPU_TYPE_ARM64 = 0x0100000C
_CPU_SUBTYPE_ARM64E_RAW = 0x80000002
_MH_EXECUTE = 2
_MAX_BACKEND = 16 * 1024 ** 3
_MAX_PLIST = 65536
_MAX_FAT_ARCH = 32
_READ_CHUNK = 1024 * 1024


class _Fsid(ctypes.Structure):
    _fields_ = [("values", ctypes.c_int32 * 2)]


class _Statfs(ctypes.Structure):
    _fields_ = [
        ("f_bsize", ctypes.c_uint32), ("f_iosize", ctypes.c_int32),
        ("f_blocks", ctypes.c_uint64), ("f_bfree", ctypes.c_uint64),
        ("f_bavail", ctypes.c_uint64), ("f_files", ctypes.c_uint64),
        ("f_ffree", ctypes.c_uint64), ("f_fsid", _Fsid),
        ("f_owner", ctypes.c_uint32), ("f_type", ctypes.c_uint32),
        ("f_flags", ctypes.c_uint32), ("f_fssubtype", ctypes.c_uint32),
        ("f_fstypename", ctypes.c_char * 16),
        ("f_mntonname", ctypes.c_char * 1024),
        ("f_mntfromname", ctypes.c_char * 1024),
        ("f_flags_ext", ctypes.c_uint32), ("f_reserved", ctypes.c_uint32 * 7),
    ]


if (ctypes.sizeof(_Statfs) != 2168 or _Statfs.f_fsid.offset != 48
        or _Statfs.f_flags.offset != 64 or _Statfs.f_fstypename.offset != 72):
    raise RuntimeError("unsupported Darwin statfs ABI")


@dataclass(frozen=True)
class _MountFacts:
    fsid: tuple[int, int]
    flags: int
    filesystem: str


class _DarwinNative:
    def __init__(self):
        if sys.platform != "darwin" or os.uname().machine != "arm64":
            raise ValueError("OS backend proof requires Darwin arm64")
        self._libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        self._libc.fstatfs.argtypes = [ctypes.c_int, ctypes.POINTER(_Statfs)]
        self._libc.fstatfs.restype = ctypes.c_int
        self._libc.sysctlbyname.argtypes = [ctypes.c_char_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
        self._libc.sysctlbyname.restype = ctypes.c_int

    def fstatfs(self, fd: int) -> _MountFacts:
        value = _Statfs()
        if self._libc.fstatfs(fd, ctypes.byref(value)) != 0:
            raise OSError(ctypes.get_errno(), "fstatfs failed")
        raw = bytes(value.f_fstypename).split(b"\0", 1)[0]
        try:
            filesystem = raw.decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError("filesystem name is invalid") from error
        return _MountFacts(tuple(value.f_fsid.values), value.f_flags, filesystem)

    def osversion(self) -> str:
        length = ctypes.c_size_t()
        name = b"kern.osversion"
        if self._libc.sysctlbyname(name, None, ctypes.byref(length), None, 0) != 0:
            raise OSError(ctypes.get_errno(), "sysctl size failed")
        if not 2 <= length.value <= 129:
            raise ValueError("kern.osversion size is invalid")
        buffer = (ctypes.c_ubyte * length.value)()
        actual = ctypes.c_size_t(length.value)
        if self._libc.sysctlbyname(name, buffer, ctypes.byref(actual), None, 0) != 0:
            raise OSError(ctypes.get_errno(), "sysctl read failed")
        raw = bytes(buffer[:actual.value])
        if actual.value != length.value or not raw.endswith(b"\0") or b"\0" in raw[:-1]:
            raise ValueError("kern.osversion bytes are invalid")
        try:
            text = raw[:-1].decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError("kern.osversion is invalid") from error
        if not 1 <= len(text) <= 128 or any(not (c.isalnum() or c in ".-_") for c in text):
            raise ValueError("kern.osversion is invalid")
        return text


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_uid, value.st_gid,
            stat.S_IFMT(value.st_mode), stat.S_IMODE(value.st_mode), value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns, value.st_flags)


def _pread(fd: int, offset: int, length: int, file_size: int) -> bytes:
    if offset < 0 or length < 0 or offset > file_size or length > file_size - offset:
        raise ValueError("Mach-O range exceeds backend")
    value = os.pread(fd, length, offset)
    if len(value) != length:
        raise ValueError("Mach-O data is truncated")
    return value


def _validate_thin(fd: int, offset: int, size: int, raw_subtype: int) -> None:
    header = _pread(fd, offset, 32, offset + size)
    if header[:4] != b"\xcf\xfa\xed\xfe":
        raise ValueError("ARM64 slice is not thin little-endian Mach-O")
    _, cpu, subtype, filetype, count, commands_size, _, _ = struct.unpack("<IIIIIIII", header)
    if cpu != _CPU_TYPE_ARM64 or subtype != raw_subtype or filetype != _MH_EXECUTE:
        raise ValueError("ARM64 slice identity is invalid")
    if commands_size > size - 32 or count > commands_size // 8:
        raise ValueError("Mach-O commands exceed slice")
    cursor = 0
    for _ in range(count):
        if cursor > commands_size - 8:
            raise ValueError("Mach-O commands are truncated")
        _, command_size = struct.unpack("<II", _pread(fd, offset + 32 + cursor, 8,
                                                       offset + size))
        if command_size < 8 or command_size % 8 or command_size > commands_size - cursor:
            raise ValueError("Mach-O command is invalid")
        cursor += command_size
    if cursor != commands_size:
        raise ValueError("Mach-O commands have trailing bytes")


def _validate_universal_backend(fd: int, file_size: int) -> None:
    header = _pread(fd, 0, 8, file_size)
    magic, count = struct.unpack(">II", header)
    if magic != 0xCAFEBABE or not 1 <= count <= _MAX_FAT_ARCH:
        raise ValueError("backend is not bounded fat32 Mach-O")
    if count > (file_size - 8) // 20:
        raise ValueError("fat architecture table exceeds backend")
    selected = []
    ranges = []
    seen_architectures = set()
    for number in range(count):
        cpu, subtype, offset, size, align = struct.unpack(">IIIII",
            _pread(fd, 8 + number * 20, 20, file_size))
        if (size == 0 or offset < 8 + count * 20 or offset > file_size
                or size > file_size - offset or align > 31):
            raise ValueError("fat architecture row is invalid")
        if (cpu, subtype) in seen_architectures:
            raise ValueError("fat architecture row is duplicated")
        seen_architectures.add((cpu, subtype))
        if offset % (1 << align):
            raise ValueError("fat architecture alignment is invalid")
        ranges.append((offset, offset + size))
        if cpu == _CPU_TYPE_ARM64:
            if subtype != _CPU_SUBTYPE_ARM64E_RAW:
                raise ValueError("host ARM64 raw subtype is invalid")
            selected.append((offset, size, subtype))
    if len(selected) != 1 or any(a < d and c < b for i, (a, b) in enumerate(ranges)
                                for c, d in ranges[i + 1:]):
        raise ValueError("fat architecture selection is ambiguous")
    _validate_thin(fd, *selected[0])


def _hash_fd(fd: int, maximum: int) -> tuple[int, str, bytes]:
    """Hash the frozen fstat size; final identity recheck detects later growth."""
    value = os.fstat(fd)
    if value.st_size < 1 or value.st_size > maximum:
        raise ValueError("OS backend file size is invalid")
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    captured = bytearray() if maximum == _MAX_PLIST else None
    total = 0
    while chunk := os.read(fd, min(_READ_CHUNK, value.st_size - total)):
        total += len(chunk)
        if total > value.st_size:
            raise ValueError("OS backend file grew while hashing")
        digest.update(chunk)
        if captured is not None:
            captured.extend(chunk)
    if total != value.st_size:
        raise ValueError("OS backend file changed while hashing")
    return total, digest.hexdigest(), bytes(captured or b"")


class _OSBackendProof:
    def __init__(self, token, *, native, records, mounts, backend_hash,
                 system_hash, os_build):
        if token is not _TOKEN:
            raise TypeError("OS backend proofs cannot be constructed by callers")
        self._native = native
        self._records = records
        self._mounts = mounts
        self._backend_hash = backend_hash
        self._system_hash = system_hash
        self._os_build = os_build
        self._closed = False

    def revalidate(self) -> None:
        if self._closed:
            raise ValueError("OS backend proof is closed")
        _check_records(self._native, self._records, self._mounts,
                       self._backend_hash, self._system_hash, self._os_build)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        error = None
        for record in reversed(self._records):
            try:
                os.close(record[1])
            except OSError as caught:
                if error is None:
                    error = caught
        if error is not None:
            raise error

    def __enter__(self):
        if self._closed:
            raise ValueError("OS backend proof is closed")
        return self

    def __exit__(self, *_):
        self.close()


def _check_nodes(native, records, frozen_mounts):
    for index, (name, fd, frozen, parent_fd, expected_mode, is_directory) in enumerate(records):
        current = os.fstat(fd)
        named = (os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                 if parent_fd is not None else os.stat(name, follow_symlinks=False))
        writable = os.access(name, os.W_OK, dir_fd=parent_fd,
                             effective_ids=True, follow_symlinks=False)
        retained_kind = stat.S_ISDIR(current.st_mode) if is_directory else stat.S_ISREG(current.st_mode)
        named_kind = stat.S_ISDIR(named.st_mode) if is_directory else stat.S_ISREG(named.st_mode)
        if (_identity(current) != frozen or _identity(named) != frozen
                or current.st_uid != 0 or current.st_gid != 0
                or named.st_uid != 0 or named.st_gid != 0
                or stat.S_IMODE(current.st_mode) != expected_mode
                or stat.S_IMODE(named.st_mode) != expected_mode
                or not retained_kind or not named_kind
                or writable or not current.st_flags & _SF_RESTRICTED
                or (not is_directory and current.st_nlink != 1)):
            raise ValueError("OS backend identity or vnode predicate changed")
        mount = native.fstatfs(fd)
        if mount != frozen_mounts[index] or mount.filesystem != "apfs" or not mount.flags & _MNT_RDONLY:
            raise ValueError("readonly_restricted_system_volume changed")
    if len({mount.fsid for mount in frozen_mounts}) != 1:
        raise ValueError("OS backend objects are not on one filesystem")


def _check_records(native, records, frozen_mounts, backend_hash, system_hash, os_build):
    _check_nodes(native, records, frozen_mounts)
    _, current_backend_hash, _ = _hash_fd(records[1][1], _MAX_BACKEND)
    _, current_system_hash, plist_bytes = _hash_fd(records[3][1], _MAX_PLIST)
    if current_backend_hash != backend_hash or current_system_hash != system_hash:
        raise ValueError("OS backend content changed")
    try:
        plist = plistlib.loads(plist_bytes)
    except (plistlib.InvalidFileException, ValueError, TypeError) as error:
        raise ValueError("SystemVersion plist is invalid") from error
    if (not isinstance(plist, dict) or plist.get("ProductName") != "macOS"
            or plist.get("ProductBuildVersion") != os_build
            or native.osversion() != os_build):
        raise ValueError("SystemVersion does not match native kernel build")
    _validate_universal_backend(records[1][1], os.fstat(records[1][1]).st_size)
    _check_nodes(native, records, frozen_mounts)


def _open_pair(parent: Path, leaf: str, parent_mode: int, leaf_mode: int):
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        leaf_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                          dir_fd=parent_fd)
    except BaseException:
        os.close(parent_fd)
        raise
    parent_value, leaf_value = os.fstat(parent_fd), os.fstat(leaf_fd)
    return [(str(parent), parent_fd, _identity(parent_value), None, parent_mode, True),
            (leaf, leaf_fd, _identity(leaf_value), parent_fd, leaf_mode, False)]


def _observe_os_backend(*, native=None, backend_path: Path = _BACKEND,
                        system_version_path: Path = _SYSTEM_VERSION) -> _OSBackendProof:
    """Observe fixed OS facts without deriving any manifest or capability."""
    native = _DarwinNative() if native is None else native
    if backend_path.name != "sandbox-exec" or system_version_path.name != "SystemVersion.plist":
        raise ValueError("OS backend paths are invalid")
    records = []
    try:
        records.extend(_open_pair(backend_path.parent, backend_path.name, 0o755, 0o755))
        records.extend(_open_pair(system_version_path.parent, system_version_path.name,
                                  0o755, 0o444))
        mounts = tuple(native.fstatfs(record[1]) for record in records)
        _, backend_hash, _ = _hash_fd(records[1][1], _MAX_BACKEND)
        _, system_hash, plist_bytes = _hash_fd(records[3][1], _MAX_PLIST)
        try:
            plist = plistlib.loads(plist_bytes)
        except (plistlib.InvalidFileException, ValueError, TypeError) as error:
            raise ValueError("SystemVersion plist is invalid") from error
        os_build = plist.get("ProductBuildVersion") if isinstance(plist, dict) else None
        if not isinstance(os_build, str):
            raise ValueError("SystemVersion build is invalid")
        proof = _OSBackendProof(_TOKEN, native=native, records=records, mounts=mounts,
            backend_hash=backend_hash, system_hash=system_hash, os_build=os_build)
        proof.revalidate()
        return proof
    except BaseException:
        for record in reversed(records):
            try:
                os.close(record[1])
            except OSError:
                pass
        raise
