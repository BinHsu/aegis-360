"""Private selected-bundle mutation observation; no invocation authority."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

from .sparse_story_batch_policy import _BatchPolicyCandidate
from .sparse_story_media_tree import publish_selected_one_packet_media_gate
from .sparse_story_runner_contract import (
    build_asset_manifest_shape, canonical_asset_manifest_shape_bytes,
)

_TOKEN = object()
_EMPTY_SUPPORT_SHA = hashlib.sha256(canonical_asset_manifest_shape_bytes(
    build_asset_manifest_shape(asset_kind="synthetic_support", entries=[]))).hexdigest()


class _OwnedSelectedBundleMutation:
    """An exclusive selected publication, retained only for one negative test.

    The changed bundle is intentionally never deleted here. Its caller owns the
    enclosing synthetic workspace and must inspect it after this observation.
    """

    def __init__(self, token, root: Path, root_identity: tuple[int, int],
                 relative: str):
        if token is not _TOKEN:
            raise TypeError("selected mutation owner requires publication")
        self._root = root
        self._root_identity = root_identity
        self._relative = relative
        self._used = False

    def observe_once(self, *, candidate, frozen_row, spawn):
        if self._used:
            raise ValueError("selected mutation owner already used")
        if type(candidate) is not _BatchPolicyCandidate:
            raise ValueError("selected mutation candidate differs")
        if not callable(spawn):
            raise ValueError("selected mutation spawn guard is missing")
        stimulus = frozen_row.get("stimulus") if type(frozen_row) is dict else None
        if (type(frozen_row) is not dict
                or set(frozen_row) != {"case_id", "expected_result", "stimulus"}
                or frozen_row["case_id"] != "bundle_mutation"
                or frozen_row["expected_result"] != "trust_invalid"
                or type(stimulus) is not dict
                or set(stimulus) != {"argv", "stdin_sha256", "support_manifest_sha256"}
                or stimulus["argv"] != [self._relative]
                or stimulus["stdin_sha256"] != hashlib.sha256(b"").hexdigest()
                or stimulus["support_manifest_sha256"] != _EMPTY_SUPPORT_SHA):
            raise ValueError("frozen bundle mutation row differs")
        proof = candidate._proofs[0]
        if proof._root != self._root:
            raise ValueError("selected mutation bundle differs")
        candidate.invocation_binding_sha256()  # Complete baseline before mutation.
        root_stat = os.lstat(self._root)
        if ((root_stat.st_dev, root_stat.st_ino) != self._root_identity
                or not stat.S_ISDIR(root_stat.st_mode)):
            raise ValueError("selected mutation owner identity changed")
        selected = next((row for row in proof._leaves
                         if row[0] == self._relative), None)
        if selected is None:
            raise ValueError("selected mutation leaf differs")
        path = self._root / self._relative
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            retained = os.fstat(selected[1]); actual = os.fstat(fd)
            if ((actual.st_dev, actual.st_ino, actual.st_nlink, actual.st_size)
                    != (retained.st_dev, retained.st_ino,
                        retained.st_nlink, retained.st_size)
                    or not stat.S_ISREG(actual.st_mode) or actual.st_size < 1):
                raise ValueError("selected mutation leaf identity changed")
            first = os.pread(fd, 1, 0)
            if len(first) != 1:
                raise ValueError("selected mutation leaf is unreadable")
            self._used = True
            try:
                os.fchmod(fd, actual.st_mode | stat.S_IWUSR)
                write_fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
                try:
                    writable = os.fstat(write_fd)
                    if (writable.st_dev, writable.st_ino) != (actual.st_dev, actual.st_ino):
                        raise ValueError("selected mutation write target changed")
                    written = os.pwrite(write_fd, bytes([first[0] ^ 1]), 0)
                    if written != 1:
                        raise OSError("selected mutation write was incomplete")
                    os.fsync(write_fd)
                finally:
                    os.close(write_fd)
            finally:
                os.fchmod(fd, stat.S_IMODE(actual.st_mode))
            if (os.pread(fd, 1, 0) != bytes([first[0] ^ 1])
                    or (os.fstat(fd).st_dev, os.fstat(fd).st_ino)
                    != (actual.st_dev, actual.st_ino)):
                raise ValueError("selected mutation did not change owned bytes")
        finally:
            os.close(fd)
        try:
            candidate.invocation_binding_sha256()
        except ValueError:
            return "trust_invalid"
        # A cached or weakened trust validator must not turn the case green.
        raise ValueError("selected mutation was accepted by retained trust")


def _publish_owned_selected_bundle_for_mutation(**inputs):
    """Publish exclusively, then retain the selected root identity and leaf."""
    result = publish_selected_one_packet_media_gate(**inputs)
    root = inputs["bundle_destination"]
    if not isinstance(root, Path):
        raise ValueError("selected mutation destination must be a Path")
    root_stat = os.lstat(root)
    if not stat.S_ISDIR(root_stat.st_mode):
        raise ValueError("selected mutation destination is not a directory")
    one = result[1]
    relative = one["packets"][0]["projection"]["rows"][0]["media_ref"]
    owner = _OwnedSelectedBundleMutation(
        _TOKEN, root, (root_stat.st_dev, root_stat.st_ino), relative)
    return owner, result
