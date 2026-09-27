"""Retained pre/post facts for one coordinator-owned outside-write sentinel root.

This proves only the named local tree stayed unchanged. It grants no isolation
capability and does not create or delete caller files.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

_EXISTING = "outside-existing"
_EXPECTED = b"outside-existing-sentinel-v1"


def _file_facts(value):
    return (value.st_dev, value.st_ino, value.st_uid, value.st_mode,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def _directory_facts(value):
    return (value.st_dev, value.st_ino, value.st_uid, value.st_mode)


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
