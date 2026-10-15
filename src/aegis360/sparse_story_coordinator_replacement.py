"""Private replacement cleanup observation, not an adapter-run case result.

The run receipt/evidence publisher is still closed. This helper covers its
owned-file cleanup primitive with synthetic opaque peers; it cannot attest a
real adapter publication or return the protocol's replacement_preserved enum.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .sparse_story_media_tree import _remove_owned_file


@dataclass(frozen=True)
class _OwnedPeer:
    path: Path
    identity: tuple[int, int]
    sha256: str


@dataclass(frozen=True)
class _ReplacementObservation:
    cleanup_attempted: bool
    replacement_peers_preserved: bool
    # This primitive does not issue a case result or adapter-run receipt.
    case_result: None = None


def _create_owned_peer(path: Path, data: bytes) -> _OwnedPeer:
    """Create an opaque synthetic peer exclusively and retain its identity."""
    if type(data) is not bytes:
        raise ValueError("owned peer bytes are invalid")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as output:
            output.write(data)
            output.flush()
        os.fsync(fd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("owned peer is not a unique regular file")
        return _OwnedPeer(path, (info.st_dev, info.st_ino),
                          hashlib.sha256(data).hexdigest())
    finally:
        os.close(fd)


def _file_facts(path: Path) -> tuple[tuple[int, int], str]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("peer is not a unique regular file")
        digest = hashlib.sha256()
        while chunk := os.read(fd, 65536):
            digest.update(chunk)
        after = os.fstat(fd)
        current = os.stat(path, follow_symlinks=False)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (after.st_dev, after.st_ino) != (current.st_dev, current.st_ino)):
            raise ValueError("peer changed during verification")
        return (after.st_dev, after.st_ino), digest.hexdigest()
    finally:
        os.close(fd)


def _observe_replacement_cleanup(*, frozen_row: Mapping[str, object],
        actual_row: Mapping[str, object], owned_peers: tuple[_OwnedPeer, _OwnedPeer],
        replacement_peers: tuple[_OwnedPeer, _OwnedPeer]) -> _ReplacementObservation:
    """Clean only original identities after two peer names are replaced.

    Caller must create and retain the two owned peers before the race, then
    retain replacement identities at the same names. The frozen row must be
    checked again at the boundary. This is an isolated cleanup observation,
    not the protocol case's adapter publication boundary.
    """
    if (not isinstance(frozen_row, Mapping) or not isinstance(actual_row, Mapping)
            or set(frozen_row) != {"case_id", "expected_result", "stimulus"}
            or frozen_row["case_id"] != "replacement_race"
            or frozen_row["expected_result"] != "replacement_preserved"
            or json.dumps(frozen_row, sort_keys=True, separators=(",", ":"))
               != json.dumps(actual_row, sort_keys=True, separators=(",", ":"))
            or type(owned_peers) is not tuple or type(replacement_peers) is not tuple
            or len(owned_peers) != 2 or len(replacement_peers) != 2
            or any(type(peer) is not _OwnedPeer for peer in (*owned_peers, *replacement_peers))
            or owned_peers[0].path == owned_peers[1].path
            or tuple(peer.path for peer in owned_peers)
               != tuple(peer.path for peer in replacement_peers)):
        raise ValueError("replacement cleanup binding is invalid")
    for original, replacement in zip(owned_peers, replacement_peers):
        if original.identity == replacement.identity:
            raise ValueError("replacement has original identity")
        if _file_facts(replacement.path) != (replacement.identity, replacement.sha256):
            raise ValueError("replacement changed before cleanup")
    for original in owned_peers:
        _remove_owned_file(original.path, original.identity)
    survived = all(_file_facts(peer.path) == (peer.identity, peer.sha256)
                   for peer in replacement_peers)
    return _ReplacementObservation(cleanup_attempted=True,
                                   replacement_peers_preserved=survived)
