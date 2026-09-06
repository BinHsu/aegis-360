"""Retained filesystem proof for sparse-story asset manifests."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
from pathlib import Path, PurePosixPath
from typing import Mapping

from .sparse_story_runner_contract import (
    build_asset_manifest_shape, canonical_asset_manifest_shape_bytes,
    validate_asset_manifest_shape,
)

MAX_LEAVES = 4096
MAX_DEPTH = 16
MAX_LEAF_BYTES = 16 * 1024 ** 3
MAX_TOTAL_BYTES = 64 * 1024 ** 3

_PROOF_FACTORY_TOKEN = object()


def _common_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    """Identity which remains valid across harmless directory timestamp changes."""
    return (value.st_dev, value.st_ino, value.st_uid,
            stat.S_IFMT(value.st_mode), stat.S_IMODE(value.st_mode))


def _leaf_identity(value: os.stat_result) -> tuple[int, ...]:
    return (*_common_identity(value), value.st_size, value.st_mtime_ns,
            value.st_ctime_ns, value.st_nlink)


def _close_all(fds) -> OSError | None:
    first_error = None
    for fd in fds:
        try:
            os.close(fd)
        except OSError as error:
            if first_error is None:
                first_error = error
    return first_error


class _AssetTreeProof:
    """Opaque retained proof; instances are created only by this module."""

    def __init__(self, token, *, root: Path, parent_fd: int, root_fd: int,
                 root_frozen: tuple[int, ...], directories, leaves, children,
                 asset_kind: str, entrypoint: str | None):
        if token is not _PROOF_FACTORY_TOKEN:
            raise TypeError("asset tree proofs cannot be constructed by callers")
        self._root = root
        self._parent_fd = parent_fd
        self._root_fd = root_fd
        self._root_frozen = root_frozen
        self._directories = directories
        self._leaves = leaves
        self._asset_kind = asset_kind
        self._entrypoint = entrypoint
        self._children = children
        self._closed = False
        self._frozen_manifest_bytes = None

    def _check_open(self):
        if self._closed:
            raise ValueError("asset tree proof is closed")

    def manifest(self) -> dict[str, object]:
        self._check_open()
        root = os.fstat(self._root_fd)
        current_name = os.stat(self._root.name, dir_fd=self._parent_fd,
                               follow_symlinks=False)
        absolute_name = os.stat(self._root, follow_symlinks=False)
        if (not stat.S_ISDIR(root.st_mode)
                or _common_identity(root) != self._root_frozen
                or _common_identity(current_name) != self._root_frozen
                or _common_identity(absolute_name) != self._root_frozen
                or not stat.S_ISDIR(current_name.st_mode)):
            raise ValueError("asset root identity, type, or mode changed")
        for _, fd, frozen, parent_fd, name in self._directories:
            current = os.fstat(fd)
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (not stat.S_ISDIR(current.st_mode)
                    or _common_identity(current) != frozen
                    or _common_identity(named) != frozen
                    or not stat.S_ISDIR(named.st_mode)):
                raise ValueError("asset directory identity or mode changed")
        directory_fds = {"": self._root_fd,
                         **{row[0]: row[1] for row in self._directories}}
        for relative, names in self._children.items():
            if set(os.listdir(directory_fds[relative])) != names:
                raise ValueError("asset directory children changed")
        entries = []
        for relative, fd, frozen, parent_fd, name in self._leaves:
            before = os.fstat(fd)
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            expected_mode = (0o555 if self._asset_kind == "runtime"
                             and relative == self._entrypoint else 0o444)
            if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                    or _leaf_identity(before) != frozen
                    or _leaf_identity(named) != frozen
                    or not stat.S_ISREG(named.st_mode)
                    or stat.S_IMODE(named.st_mode) != expected_mode):
                raise ValueError("asset leaf identity, link count, or mode changed")
            os.lseek(fd, 0, os.SEEK_SET)
            digest = hashlib.sha256()
            while chunk := os.read(fd, 1024 * 1024):
                digest.update(chunk)
            if _leaf_identity(os.fstat(fd)) != frozen:
                raise ValueError("asset leaf changed while hashing")
            entries.append({"relative_path": relative, "mode": expected_mode,
                            "size": before.st_size, "sha256": digest.hexdigest()})
        entries.sort(key=lambda row: row["relative_path"].encode("utf-8"))
        required_dirs = {str(parent) for row in entries
            for parent in _proper_parents(PurePosixPath(row["relative_path"]))}
        actual_dirs = {row[0] for row in self._directories}
        leaf_paths = {PurePosixPath(row["relative_path"]) for row in entries}
        if any(parent in leaf_paths for path in leaf_paths
               for parent in _proper_parents(path)):
            raise ValueError("asset leaf/ancestor prefix collision")
        if actual_dirs != required_dirs:
            raise ValueError("asset directory set is not exact")
        manifest = build_asset_manifest_shape(asset_kind=self._asset_kind,
            entrypoint=self._entrypoint, entries=entries)
        encoded = canonical_asset_manifest_shape_bytes(manifest)
        if self._frozen_manifest_bytes is None:
            self._frozen_manifest_bytes = encoded
        elif encoded != self._frozen_manifest_bytes:
            raise ValueError("asset manifest bytes changed after proof was frozen")
        return json.loads(encoded)

    def backend_identity(self) -> tuple[int, int, str]:
        """Return only the root identity and authoritative manifest digest."""
        self.manifest()
        return (self._root_frozen[0], self._root_frozen[1],
                hashlib.sha256(self._frozen_manifest_bytes).hexdigest())

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        fds = ([row[1] for row in self._leaves]
               + [row[1] for row in reversed(self._directories)]
               + [self._root_fd, self._parent_fd])
        error = _close_all(fds)
        if error is not None:
            raise error

    def __enter__(self):
        self._check_open()
        return self

    def __exit__(self, *_):
        self.close()


def _proper_parents(path: PurePosixPath):
    parent = path.parent
    while parent != PurePosixPath("."):
        yield parent
        parent = parent.parent


def _preflight_manifest(manifest: Mapping[str, object]) -> None:
    """Reject declared resource excess before opening or hashing any asset."""
    if not isinstance(manifest, Mapping):
        raise ValueError("asset manifest must be a mapping")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("asset manifest entries must be a list")
    if len(entries) > MAX_LEAVES:
        raise ValueError("asset manifest exceeds maximum leaf count")
    total = 0
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("asset manifest entry must be a mapping")
        relative = entry.get("relative_path")
        size = entry.get("size")
        if isinstance(relative, str) and len(PurePosixPath(relative).parts) > MAX_DEPTH:
            raise ValueError("asset manifest exceeds maximum depth")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError("asset manifest size is invalid")
        if size > MAX_LEAF_BYTES:
            raise ValueError("asset manifest exceeds maximum leaf size")
        total += size
        if total > MAX_TOTAL_BYTES:
            raise ValueError("asset manifest exceeds maximum total size")
    validate_asset_manifest_shape(manifest)


def _observe_asset_tree(*, root: Path, asset_kind: str,
                        entrypoint: str | None = None) -> _AssetTreeProof:
    """Observe a tree internally; this is not an authority boundary."""
    if not isinstance(root, Path) or not root.is_absolute() or root.name == "":
        raise ValueError("asset root must be a non-root absolute Path")
    parent_fd = os.open(root.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    root_fd = -1
    directories = []
    leaves = []
    children = {}
    total_size = 0
    try:
        root_info = os.stat(root.name, dir_fd=parent_fd, follow_symlinks=False)
        root_fd = os.open(root.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                          dir_fd=parent_fd)
        opened_root = os.fstat(root_fd)
        if (not stat.S_ISDIR(root_info.st_mode)
                or _common_identity(root_info) != _common_identity(opened_root)
                or stat.S_IMODE(opened_root.st_mode) != 0o555
                or opened_root.st_uid != os.getuid()):
            raise ValueError("asset root identity, type, or mode is invalid")
        seen_inodes = {(opened_root.st_dev, opened_root.st_ino)}

        def visit(directory_fd: int, prefix: str):
            nonlocal total_size
            names = os.listdir(directory_fd)
            children[prefix] = set(names)
            for name in names:
                relative = f"{prefix}/{name}" if prefix else name
                probe = {"relative_path": relative, "mode": 0o444,
                         "size": 0, "sha256": "0" * 64}
                try:
                    build_asset_manifest_shape(asset_kind="synthetic_support", entries=[probe])
                except ValueError as error:
                    raise ValueError("asset node path is unsafe") from error
                if len(PurePosixPath(relative).parts) > MAX_DEPTH:
                    raise ValueError("asset path exceeds maximum depth")
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    try:
                        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=directory_fd)
                    except OSError as error:
                        if error.errno == errno.EMFILE:
                            raise ValueError("asset proof lacks descriptor capacity") from error
                        raise
                    opened = os.fstat(child)
                    if (not stat.S_ISDIR(opened.st_mode)
                            or _common_identity(opened) != _common_identity(info)
                            or stat.S_IMODE(opened.st_mode) != 0o555
                            or opened.st_uid != os.getuid()
                            or opened.st_dev != opened_root.st_dev
                            or (opened.st_dev, opened.st_ino) in seen_inodes):
                        _close_all([child])
                        raise ValueError("asset directory is invalid")
                    seen_inodes.add((opened.st_dev, opened.st_ino))
                    directories.append((relative, child, _common_identity(opened),
                                        directory_fd, name))
                    visit(child, relative)
                elif stat.S_ISREG(info.st_mode):
                    try:
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
                    except OSError as error:
                        if error.errno == errno.EMFILE:
                            raise ValueError("asset proof lacks descriptor capacity") from error
                        raise
                    opened = os.fstat(fd)
                    if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                            or _leaf_identity(opened) != _leaf_identity(info)
                            or opened.st_uid != os.getuid()
                            or opened.st_dev != opened_root.st_dev
                            or opened.st_size > MAX_LEAF_BYTES
                            or (opened.st_dev, opened.st_ino) in seen_inodes):
                        _close_all([fd])
                        raise ValueError("asset leaf is invalid")
                    seen_inodes.add((opened.st_dev, opened.st_ino))
                    total_size += opened.st_size
                    if len(leaves) >= MAX_LEAVES or total_size > MAX_TOTAL_BYTES:
                        _close_all([fd])
                        raise ValueError("asset tree exceeds frozen bounds")
                    leaves.append((relative, fd, _leaf_identity(opened), directory_fd, name))
                else:
                    raise ValueError("asset node type is forbidden")
        visit(root_fd, "")
        proof = _AssetTreeProof(_PROOF_FACTORY_TOKEN, root=root, parent_fd=parent_fd,
            root_fd=root_fd, root_frozen=_common_identity(opened_root),
            directories=directories, leaves=leaves, children=children,
            asset_kind=asset_kind, entrypoint=entrypoint)
        proof.manifest()
        return proof
    except BaseException:
        _close_all([row[1] for row in leaves]
                   + [row[1] for row in reversed(directories)]
                   + ([root_fd] if root_fd >= 0 else []) + [parent_fd])
        raise


def _observe_asset_manifest_shape(*, root: Path, asset_kind: str,
                                  entrypoint: str | None = None) -> dict[str, object]:
    """Create a non-authoritative manifest document and retain no descriptors."""
    proof = _observe_asset_tree(root=root, asset_kind=asset_kind,
                                entrypoint=entrypoint)
    try:
        return proof.manifest()
    finally:
        proof.close()


def validate_asset_tree(*, manifest: Mapping[str, object], root: Path) -> _AssetTreeProof:
    """Return retained proof only for a precommitted, exactly matching document."""
    _preflight_manifest(manifest)
    proof = _observe_asset_tree(root=root, asset_kind=manifest["asset_kind"],
                                entrypoint=manifest["entrypoint"])
    try:
        if proof.manifest() != manifest:
            raise ValueError("asset manifest does not derive from filesystem tree")
        return proof
    except BaseException:
        proof.close()
        raise
