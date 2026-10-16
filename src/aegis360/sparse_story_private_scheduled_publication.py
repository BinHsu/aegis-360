"""Private exact two-peer publication for one scheduled synthetic packet."""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass, field

from .sparse_story_private_publication import (
    _PrivatePublishedPair, _publish_private_pair,
)
from .sparse_story_private_run_publication import _OwnedPrivateRunRoot
from .sparse_story_private_scheduled_receipt import (
    _PrivateScheduledRunReceipt, _rebuild_private_scheduled_run_receipt,
)


@dataclass(frozen=True, slots=True)
class _PrivateScheduledPublication:
    owner: _OwnedPrivateRunRoot = field(repr=False)
    receipt: _PrivateScheduledRunReceipt = field(repr=False)
    pair: _PrivatePublishedPair = field(repr=False)
    evidence_sha256: str
    receipt_sha256: str
    authority: bool = False

    def revalidate(self):
        if (type(self.owner) is not _OwnedPrivateRunRoot
                or type(self.receipt) is not _PrivateScheduledRunReceipt
                or type(self.pair) is not _PrivatePublishedPair
                or self.authority is not False or self.owner._used is not True):
            raise ValueError("scheduled publication proof differs")
        rebuilt = _rebuild_private_scheduled_run_receipt(self.receipt)
        capture = self.receipt._capture
        expected = (hashlib.sha256(capture.stdout).hexdigest(),
            hashlib.sha256(rebuilt).hexdigest())
        info = os.lstat(self.owner.root)
        if ((info.st_dev, info.st_ino) != self.owner._identity
                or not stat.S_ISDIR(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o700
                or set(os.listdir(self.owner.root)) != {
                    "evidence.json", "receipt.json"}
                or self.pair.revalidate() != expected
                or (self.evidence_sha256, self.receipt_sha256) != expected):
            raise ValueError("scheduled publication peers changed")
        return expected


def _publish_private_scheduled_packet_once(*, owner, receipt):
    """Publish and read back exact evidence then receipt; never retry."""
    if (type(owner) is not _OwnedPrivateRunRoot
            or type(receipt) is not _PrivateScheduledRunReceipt
            or owner._used):
        raise ValueError("scheduled publication owner or receipt differs")
    owner.revalidate_empty()
    rebuilt = _rebuild_private_scheduled_run_receipt(receipt)
    evidence = receipt._capture.stdout
    if type(evidence) is not bytes or not evidence:
        raise ValueError("scheduled evidence is empty")
    owner.revalidate_empty()
    owner._used = True
    pair = _publish_private_pair(evidence_path=owner.root / "evidence.json",
        receipt_path=owner.root / "receipt.json", evidence_bytes=evidence,
        receipt_bytes=rebuilt)
    proof = _PrivateScheduledPublication(owner, receipt, pair,
        hashlib.sha256(evidence).hexdigest(),
        hashlib.sha256(rebuilt).hexdigest())
    try:
        proof.revalidate()
    except BaseException:
        pair.cleanup()
        raise
    return proof
