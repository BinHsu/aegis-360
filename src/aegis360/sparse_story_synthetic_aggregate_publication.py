"""Exclusive, read-back publication of one completed synthetic gate result."""

from __future__ import annotations

import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .sparse_story_private_publication import (
    PublicationIncomplete, _PublishedPeer, _remove_exact, _verify,
    _write_exclusive,
)


def _read_exact_peer(peer):
    _verify(peer)
    fd = os.open(peer.path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if ((before.st_dev, before.st_ino) != peer.identity
                or before.st_size != peer.size):
            raise PublicationIncomplete("aggregate peer changed before readback")
        data = bytearray()
        while chunk := os.read(fd, 65536):
            data.extend(chunk)
            if len(data) > peer.size:
                raise PublicationIncomplete("aggregate readback grew")
        after = os.fstat(fd)
        if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                != (before.st_dev, before.st_ino, before.st_size,
                    before.st_mtime_ns)):
            raise PublicationIncomplete("aggregate peer changed during readback")
    finally:
        os.close(fd)
    _verify(peer)
    if len(data) != peer.size:
        raise PublicationIncomplete("aggregate readback size differs")
    return bytes(data)


class _OwnedSyntheticAggregateRoot:
    """One exact empty directory; replacement is never silently removed."""

    def __init__(self, parent: Path):
        if not isinstance(parent, Path) or not parent.is_dir():
            raise ValueError("aggregate parent is invalid")
        self.root = Path(tempfile.mkdtemp(prefix="aegis-aggregate-", dir=parent))
        info = os.lstat(self.root)
        self._identity = (info.st_dev, info.st_ino)
        self._used = False
        self.revalidate_empty()

    def revalidate_empty(self):
        info = os.lstat(self.root)
        if (not stat.S_ISDIR(info.st_mode)
                or (info.st_dev, info.st_ino) != self._identity
                or stat.S_IMODE(info.st_mode) != 0o700
                or os.listdir(self.root)):
            raise ValueError("aggregate root identity or emptiness changed")

    def publish_once(self, *, proof):
        from .sparse_story_runner_contract import (
            canonical_run_result_bytes, derive_run_result,
        )

        if self._used:
            raise ValueError("aggregate root was already used")
        self.revalidate_empty()
        value = derive_run_result(proof=proof)
        encoded = canonical_run_result_bytes(value, proof=proof)
        self.revalidate_empty()
        self._used = True
        peer = _write_exclusive(self.root / "result.json", encoded)
        published = _PublishedSyntheticAggregate(self, proof, peer)
        try:
            published.revalidate()
        except BaseException:
            try:
                _remove_exact(peer)
            except BaseException as cleanup:
                raise PublicationIncomplete(
                    "aggregate publication cleanup incomplete") from cleanup
            raise
        return published


@dataclass(frozen=True, slots=True)
class _PublishedSyntheticAggregate:
    owner: _OwnedSyntheticAggregateRoot = field(repr=False)
    proof: object = field(repr=False)
    peer: _PublishedPeer = field(repr=False)

    def revalidate(self):
        from .sparse_story_runner_contract import (
            canonical_run_result_bytes, derive_run_result,
        )

        owner = self.owner
        if (type(owner) is not _OwnedSyntheticAggregateRoot
                or owner._used is not True
                or type(self.peer) is not _PublishedPeer):
            raise ValueError("aggregate publication proof differs")
        info = os.lstat(owner.root)
        if (not stat.S_ISDIR(info.st_mode)
                or (info.st_dev, info.st_ino) != owner._identity
                or stat.S_IMODE(info.st_mode) != 0o700
                or set(os.listdir(owner.root)) != {"result.json"}
                or self.peer.path != owner.root / "result.json"):
            raise ValueError("aggregate publication root changed")
        expected = canonical_run_result_bytes(
            derive_run_result(proof=self.proof), proof=self.proof)
        if _read_exact_peer(self.peer) != expected:
            raise ValueError("aggregate publication bytes differ")
        after = os.lstat(owner.root)
        if (not stat.S_ISDIR(after.st_mode)
                or (after.st_dev, after.st_ino) != owner._identity
                or stat.S_IMODE(after.st_mode) != 0o700
                or set(os.listdir(owner.root)) != {"result.json"}):
            raise ValueError("aggregate publication root changed during readback")
        return expected
