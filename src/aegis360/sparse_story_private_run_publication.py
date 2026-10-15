"""Private binding of one attested synthetic run to two exact published peers.

This does not create a scheduled case result or aggregate, and opens no public
receipt or invocation authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from .sparse_story_private_publication import _publish_private_pair
from .sparse_story_private_run_receipt import (
    _PrivateRunReceipt, _rebuild_private_synthetic_run_receipt,
)
from .sparse_story_probe_denials import _classify_fixed_synthetic_output
from .sparse_story_runner_contract import canonical_run_receipt_shape_bytes


class _OwnedPrivateRunRoot:
    """An exclusively created empty root, used for one two-peer publication."""

    def __init__(self, parent: Path):
        if not isinstance(parent, Path) or not parent.is_dir():
            raise ValueError("private run parent is invalid")
        self.root = Path(tempfile.mkdtemp(prefix="aegis-run-", dir=parent))
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
            raise ValueError("private run root identity or emptiness changed")

    def publish_once(self, *, receipt, frozen_row):
        if self._used:
            raise ValueError("private run root was already used")
        self.revalidate_empty()
        if type(receipt) is not _PrivateRunReceipt:
            raise TypeError("private publication requires an attested run receipt")
        rebuilt = _rebuild_private_synthetic_run_receipt(
            receipt=receipt, frozen_row=frozen_row)
        capture = receipt._capture
        if (_classify_fixed_synthetic_output(capture) != "success"
                or type(capture.stdout) is not bytes):
            raise ValueError("private run evidence is not successful raw output")
        parsed = json.loads(rebuilt)
        if (canonical_run_receipt_shape_bytes(parsed) != rebuilt
                or parsed["execution"]["stdout_sha256"]
                != hashlib.sha256(capture.stdout).hexdigest()
                or not parsed["execution"]["stdout_present"]
                or parsed["execution"]["invocation_failed"]):
            raise ValueError("private run receipt and evidence differ")
        # Check the live claim again immediately before the first peer is made.
        if (_rebuild_private_synthetic_run_receipt(
                receipt=receipt, frozen_row=frozen_row) != rebuilt
                or receipt.bytes != rebuilt):
            raise ValueError("private run receipt changed before publication")
        evidence = capture.stdout
        self.revalidate_empty()
        self._used = True
        pair = _publish_private_pair(
            evidence_path=self.root / "evidence.json",
            receipt_path=self.root / "receipt.json",
            evidence_bytes=evidence, receipt_bytes=rebuilt)
        try:
            if (pair.revalidate() != (
                    hashlib.sha256(evidence).hexdigest(),
                    hashlib.sha256(rebuilt).hexdigest())
                    or set(os.listdir(self.root)) != {"evidence.json", "receipt.json"}
                    or _rebuild_private_synthetic_run_receipt(
                        receipt=receipt, frozen_row=frozen_row) != rebuilt
                    or receipt.bytes != rebuilt
                    or capture.stdout != evidence):
                raise ValueError("private run publication changed after write")
            info = os.lstat(self.root)
            if ((info.st_dev, info.st_ino) != self._identity
                    or stat.S_IMODE(info.st_mode) != 0o700):
                raise ValueError("private run root changed after write")
            return pair
        except BaseException:
            # The publisher only removes exact identity-proven peers. Any
            # replacement or changed file survives for explicit inspection.
            pair.cleanup()
            raise
