"""Retained pre/post facts for one coordinator-owned outside-write sentinel root.

This proves only the named local tree stayed unchanged. It grants no isolation
capability and does not create or delete caller files.
"""

from __future__ import annotations

import os
import stat
import hashlib
from pathlib import Path

_EXISTING = "outside-existing"
_EXPECTED = b"outside-existing-sentinel-v1"
_RENAME_SOURCE = b"rename-source-v1"
_SCRATCH_WRITE = b"scratch-write-sentinel-v1"


def _file_facts(value):
    return (value.st_dev, value.st_ino, value.st_uid, value.st_mode,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _directory_facts(value):
    return (value.st_dev, value.st_ino, value.st_uid, value.st_mode)


class _ReadDenialSentinel:
    """Retain one known existing forbidden-read leaf without exposing its bytes."""

    def __init__(self, path: Path):
        if (not isinstance(path, Path) or not path.is_absolute()
                or path.resolve(strict=True) != path):
            raise ValueError("read-denial sentinel path is not canonical")
        self.path = path
        self.parent_fd = self.file_fd = None
        self.closed = False
        try:
            self.parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY
                | os.O_NOFOLLOW | os.O_CLOEXEC)
            self.file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW
                | os.O_CLOEXEC, dir_fd=self.parent_fd)
            self.frozen = _file_facts(os.fstat(self.file_fd))
            if (not stat.S_ISREG(self.frozen[3]) or self.frozen[2] != os.getuid()
                    or self.frozen[4] != 1 or self.frozen[5] < 1
                    or self.frozen[5] > 16 * 1024 * 1024
                    or stat.S_IMODE(self.frozen[3]) & 0o022):
                raise ValueError("read-denial sentinel is not a bounded owned file")
            self.digest = self._digest()
            self.revalidate()
        except BaseException:
            self.close()
            raise

    def _digest(self):
        digest = hashlib.sha256()
        offset = 0
        while offset < self.frozen[5]:
            chunk = os.pread(self.file_fd, min(1024 * 1024, self.frozen[5] - offset), offset)
            if not chunk: raise ValueError("read-denial sentinel was shortened")
            digest.update(chunk)
            offset += len(chunk)
        return digest.digest()

    def revalidate(self):
        if self.closed: raise ValueError("read-denial sentinel is closed")
        named = os.stat(self.path.name, dir_fd=self.parent_fd, follow_symlinks=False)
        absolute = os.lstat(self.path)
        if (self.frozen != _file_facts(os.fstat(self.file_fd))
                or self.frozen != _file_facts(named)
                or self.frozen != _file_facts(absolute)
                or not stat.S_ISREG(named.st_mode)):
            raise ValueError("read-denial sentinel identity changed")
        if self._digest() != self.digest:
            raise ValueError("read-denial sentinel bytes changed")
        if (self.frozen != _file_facts(os.fstat(self.file_fd))
                or self.frozen != _file_facts(os.stat(self.path.name,
                    dir_fd=self.parent_fd, follow_symlinks=False))):
            raise ValueError("read-denial sentinel changed while hashing")

    def close(self):
        if self.closed: return
        self.closed = True
        for fd in (self.file_fd, self.parent_fd):
            if fd is not None: os.close(fd)

    def __enter__(self): return self

    def __exit__(self, *_): self.close()


class _OutsideSentinelSnapshot:
    def __init__(self, root: Path):
        if (not isinstance(root, Path) or not root.is_absolute()
                or root.resolve(strict=True) != root):
            raise ValueError("outside sentinel root is not canonical")
        self.root = root
        self.parent_fd = self.root_fd = self.file_fd = None
        self.closed = False
        try:
            self.parent_fd = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY
                | os.O_NOFOLLOW | os.O_CLOEXEC)
            self.root_fd = os.open(root.name, os.O_RDONLY | os.O_DIRECTORY
                | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=self.parent_fd)
            self.file_fd = os.open(_EXISTING, os.O_RDONLY | os.O_NOFOLLOW
                | os.O_CLOEXEC, dir_fd=self.root_fd)
            self.root_frozen = _directory_facts(os.fstat(self.root_fd))
            self.file_frozen = _file_facts(os.fstat(self.file_fd))
            self.revalidate()
        except BaseException:
            self.close()
            raise

    @property
    def create_path(self): return self.root / "outside-create"

    @property
    def existing_path(self): return self.root / _EXISTING

    @property
    def rename_destination(self): return self.root / "rename-dest"

    def revalidate(self):
        if self.closed:
            raise ValueError("outside sentinel snapshot is closed")
        root_named = os.stat(self.root.name, dir_fd=self.parent_fd,
                             follow_symlinks=False)
        root_absolute = os.lstat(self.root)
        if (self.root_frozen != _directory_facts(os.fstat(self.root_fd))
                or self.root_frozen != _directory_facts(root_named)
                or self.root_frozen != _directory_facts(root_absolute)
                or not stat.S_ISDIR(root_named.st_mode)
                or stat.S_IMODE(root_named.st_mode) != 0o700
                or root_named.st_uid != os.getuid()):
            raise ValueError("outside sentinel root changed")
        if set(os.listdir(self.root_fd)) != {_EXISTING}:
            raise ValueError("outside sentinel child names changed")
        named = os.stat(_EXISTING, dir_fd=self.root_fd, follow_symlinks=False)
        before = os.fstat(self.file_fd)
        if (self.file_frozen != _file_facts(named)
                or self.file_frozen != _file_facts(before)
                or not stat.S_ISREG(named.st_mode)
                or stat.S_IMODE(named.st_mode) != 0o600
                or named.st_uid != os.getuid() or named.st_nlink != 1):
            raise ValueError("outside existing sentinel changed")
        data = os.pread(self.file_fd, len(_EXPECTED) + 1, 0)
        if data != _EXPECTED:
            raise ValueError("outside existing sentinel bytes changed")
        after = os.fstat(self.file_fd)
        named_after = os.stat(_EXISTING, dir_fd=self.root_fd, follow_symlinks=False)
        if (self.file_frozen != _file_facts(after)
                or self.file_frozen != _file_facts(named_after)
                or set(os.listdir(self.root_fd)) != {_EXISTING}):
            raise ValueError("outside sentinel changed while reading")

    def close(self):
        if self.closed: return
        self.closed = True
        for fd in (self.file_fd, self.root_fd, self.parent_fd):
            if fd is not None: os.close(fd)

    def __enter__(self): return self

    def __exit__(self, *_): self.close()


class _ScratchProbeSnapshot:
    """Retain scratch rename source and check exact expected probe side effects."""

    def __init__(self, root: Path, home: Path, tmpdir: Path):
        if (not all(isinstance(path, Path) and path.is_absolute()
                    and path.resolve(strict=True) == path for path in (root, home, tmpdir))
                or home.parent != root or tmpdir.parent != root or home == tmpdir):
            raise ValueError("scratch probe paths are invalid")
        self.root, self.home, self.tmpdir = root, home, tmpdir
        self.root_fd = self.source_fd = None
        self.closed = False
        try:
            self.root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY
                | os.O_NOFOLLOW | os.O_CLOEXEC)
            self.source_fd = os.open("rename-source", os.O_RDONLY | os.O_NOFOLLOW
                | os.O_CLOEXEC, dir_fd=self.root_fd)
            self.root_frozen = _directory_facts(os.fstat(self.root_fd))
            self.source_frozen = _file_facts(os.fstat(self.source_fd))
            self.private_frozen = tuple(_directory_facts(os.stat(path.name,
                dir_fd=self.root_fd, follow_symlinks=False))
                for path in (home, tmpdir))
            self.prevalidate()
        except BaseException:
            self.close()
            raise

    @property
    def source_path(self): return self.root / "rename-source"

    @property
    def scratch_write_path(self): return self.root / "scratch-write"

    @property
    def fork_marker_path(self): return self.root / "fork-marker"

    @property
    def exec_marker_path(self): return self.root / "exec-marker"

    def _shared(self):
        if self.closed: raise ValueError("scratch probe snapshot is closed")
        if (self.root_frozen != _directory_facts(os.fstat(self.root_fd))
                or self.root_frozen != _directory_facts(os.lstat(self.root))
                or stat.S_IMODE(self.root_frozen[3]) != 0o700
                or self.root_frozen[2] != os.getuid()):
            raise ValueError("scratch probe root changed")
        named = os.stat("rename-source", dir_fd=self.root_fd, follow_symlinks=False)
        if (self.source_frozen != _file_facts(os.fstat(self.source_fd))
                or self.source_frozen != _file_facts(named)
                or not stat.S_ISREG(named.st_mode) or named.st_nlink != 1
                or stat.S_IMODE(named.st_mode) != 0o600
                or os.pread(self.source_fd, len(_RENAME_SOURCE) + 1, 0) != _RENAME_SOURCE):
            raise ValueError("scratch rename source changed")
        if self.source_frozen != _file_facts(os.fstat(self.source_fd)):
            raise ValueError("scratch rename source changed while reading")
        for directory, frozen in zip((self.home, self.tmpdir), self.private_frozen):
            named_dir = os.stat(directory.name, dir_fd=self.root_fd,
                                follow_symlinks=False)
            if (frozen != _directory_facts(named_dir)
                    or frozen != _directory_facts(os.lstat(directory))
                    or not stat.S_ISDIR(named_dir.st_mode)
                    or stat.S_IMODE(named_dir.st_mode) != 0o700
                    or named_dir.st_uid != os.getuid()
                    or os.listdir(directory)):
                raise ValueError("scratch private directory changed")

    def prevalidate(self):
        try: self._shared()
        except OSError as error:
            raise ValueError("scratch probe state cannot be inspected") from error
        if set(os.listdir(self.root_fd)) != {self.home.name, self.tmpdir.name,
                                            "rename-source"}:
            raise ValueError("scratch pre-probe children changed")

    def postvalidate(self):
        try: self._shared()
        except OSError as error:
            raise ValueError("scratch probe state cannot be inspected") from error
        if set(os.listdir(self.root_fd)) != {self.home.name, self.tmpdir.name,
                                            "rename-source", "scratch-write"}:
            raise ValueError("scratch post-probe children are invalid")
        fd = os.open("scratch-write", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                     dir_fd=self.root_fd)
        try:
            opened = os.fstat(fd)
            named = os.stat("scratch-write", dir_fd=self.root_fd,
                            follow_symlinks=False)
            if (_file_facts(opened) != _file_facts(named)
                    or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or stat.S_IMODE(opened.st_mode) != 0o600
                    or os.pread(fd, len(_SCRATCH_WRITE) + 1, 0) != _SCRATCH_WRITE):
                raise ValueError("scratch write sentinel is invalid")
        finally:
            os.close(fd)
        if set(os.listdir(self.root_fd)) != {self.home.name, self.tmpdir.name,
                                            "rename-source", "scratch-write"}:
            raise ValueError("scratch children changed while reading")
        self._shared()

    def close(self):
        if self.closed: return
        self.closed = True
        for fd in (self.source_fd, self.root_fd):
            if fd is not None: os.close(fd)

    def __enter__(self): return self

    def __exit__(self, *_): self.close()
