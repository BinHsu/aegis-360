"""Private two-peer byte publisher; no adapter receipt or case authority.

Paths and identities stay inside this object. Only the two byte hashes are
intended as inputs to a later coordinator-owned result derivation.
"""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .sparse_story_media_tree import _rename_exclusive


class PublicationIncomplete(ValueError):
    """A peer may remain because exact ownership could not be revalidated."""

    def __init__(self, message: str, *, removed_roles: tuple[str, ...] = ()):
        super().__init__(message)
        self.removed_roles = removed_roles


@dataclass(frozen=True)
class _PublishedPeer:
    path: Path = field(repr=False)
    identity: tuple[int, int] = field(repr=False)
    sha256: str
    size: int = field(repr=False)


def _facts(path: Path) -> tuple[tuple[int, int], str, int]:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or stat.S_IMODE(before.st_mode) != 0o444):
            raise PublicationIncomplete("published peer type or mode changed")
        digest = hashlib.sha256()
        while chunk := os.read(fd, 65536):
            digest.update(chunk)
        after = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                or (after.st_dev, after.st_ino) != (named.st_dev, named.st_ino)):
            raise PublicationIncomplete("published peer changed while checked")
        return (after.st_dev, after.st_ino), digest.hexdigest(), after.st_size
    finally:
        os.close(fd)


def _verify(peer: _PublishedPeer) -> None:
    try:
        facts = _facts(peer.path)
    except (FileNotFoundError, NotADirectoryError, OSError) as error:
        raise PublicationIncomplete("published peer is missing or inaccessible") from error
    if facts != (peer.identity, peer.sha256, peer.size):
        raise PublicationIncomplete("published peer identity or bytes changed")


def _remove_exact(peer: _PublishedPeer) -> None:
    """Remove a verified peer, refusing any changed or replaced name."""
    _verify(peer)
    parent_fd = os.open(peer.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        current = os.stat(peer.path.name, dir_fd=parent_fd, follow_symlinks=False)
        if ((current.st_dev, current.st_ino) != peer.identity
                or not stat.S_ISREG(current.st_mode)):
            raise PublicationIncomplete("published peer was replaced before unlink")
        os.unlink(peer.path.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


@dataclass(frozen=True)
class _PrivatePublishedPair:
    _evidence: _PublishedPeer = field(repr=False)
    _receipt: _PublishedPeer = field(repr=False)

    @property
    def evidence_sha256(self) -> str:
        return self._evidence.sha256

    @property
    def receipt_sha256(self) -> str:
        return self._receipt.sha256

    def revalidate(self) -> tuple[str, str]:
        _verify(self._evidence)
        _verify(self._receipt)
        return self.evidence_sha256, self.receipt_sha256

    def cleanup(self) -> tuple[str, str]:
        # Validate the pair before removing either peer. A changed or replaced
        # peer makes cleanup incomplete and leaves both names for inspection.
        self.revalidate()
        _remove_exact(self._receipt)
        try:
            _remove_exact(self._evidence)
        except BaseException as error:
            raise PublicationIncomplete("evidence cleanup incomplete",
                                        removed_roles=("receipt",)) from error
        return ("receipt", "evidence")


def _write_exclusive(path: Path, data: bytes) -> _PublishedPeer:
    if type(data) is not bytes or len(data) > 1_048_576:
        raise ValueError("private peer bytes are invalid")
    fd, stage_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    stage = Path(stage_name)
    stage_info = os.fstat(fd)
    stage_identity = (stage_info.st_dev, stage_info.st_ino)
    published = False
    peer = None
    try:
        with os.fdopen(fd, "wb", closefd=False) as output:
            output.write(data)
            output.flush()
        os.fsync(fd)
        os.fchmod(fd, 0o444)
        os.fsync(fd)
        info = os.fstat(fd)
        peer = _PublishedPeer(path, (info.st_dev, info.st_ino),
                              hashlib.sha256(data).hexdigest(), len(data))
        _rename_exclusive(stage, path)
        published = True
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        _verify(peer)
        return peer
    except BaseException as error:
        if published:
            try:
                _remove_exact(peer)
            except BaseException as cleanup:
                raise PublicationIncomplete("published peer cleanup incomplete") from cleanup
        raise
    finally:
        os.close(fd)
        if not published:
            try:
                current = os.stat(stage, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                if ((current.st_dev, current.st_ino) != stage_identity
                        or not stat.S_ISREG(current.st_mode)):
                    raise PublicationIncomplete("staging peer was replaced")
                stage.unlink()


def _publish_private_pair(*, evidence_path: Path, receipt_path: Path,
                          evidence_bytes: bytes, receipt_bytes: bytes
                          ) -> _PrivatePublishedPair:
    """Publish two opaque peers; rollback only exactly owned first peer."""
    if (not isinstance(evidence_path, Path) or not isinstance(receipt_path, Path)
            or evidence_path == receipt_path
            or evidence_path.parent != receipt_path.parent
            or type(evidence_bytes) is not bytes or type(receipt_bytes) is not bytes):
        raise ValueError("private publication inputs are invalid")
    evidence = _write_exclusive(evidence_path, evidence_bytes)
    try:
        receipt = _write_exclusive(receipt_path, receipt_bytes)
        pair = _PrivatePublishedPair(evidence, receipt)
        pair.revalidate()
        return pair
    except BaseException as error:
        try:
            _remove_exact(evidence)
        except BaseException as cleanup:
            raise PublicationIncomplete("first peer cleanup incomplete") from cleanup
        raise error
