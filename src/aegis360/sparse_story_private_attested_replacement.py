"""Bind one real coordinator capture to the private replacement observation."""

from __future__ import annotations

import hashlib
import os
import stat

from .sparse_story_private_replacement_case import (
    _observe_private_replacement_race, _verify_row,
)
from .sparse_story_private_run_publication import _OwnedPrivateRunRoot
from .sparse_story_private_run_receipt import (
    _PrivateRunReceipt, _rebuild_private_synthetic_run_receipt,
)
from .sparse_story_probe_denials import _classify_fixed_synthetic_output
from .sparse_story_runner_contract import build_asset_manifest_shape


def _observe_attested_private_replacement(*, owner, receipt, frozen_row):
    """Leave four exact peers for inspection; issue no public case result."""
    if (type(owner) is not _OwnedPrivateRunRoot
            or type(receipt) is not _PrivateRunReceipt
            or owner._used):
        raise ValueError("attested replacement owner or receipt is invalid")
    owner.revalidate_empty()
    support = build_asset_manifest_shape(asset_kind="synthetic_support",
        entries=[])
    _verify_row(frozen_row=frozen_row, argv=(), stdin=b"",
        support_manifest=support)
    rebuilt = _rebuild_private_synthetic_run_receipt(
        receipt=receipt, frozen_row=frozen_row)
    capture = receipt._capture
    if (_classify_fixed_synthetic_output(capture) != "success"
            or type(capture.stdout) is not bytes or not capture.stdout):
        raise ValueError("replacement evidence is not successful native output")
    evidence_sha = hashlib.sha256(capture.stdout).hexdigest()
    receipt_sha = hashlib.sha256(rebuilt).hexdigest()
    owner.revalidate_empty()
    owner._used = True
    observed = _observe_private_replacement_race(
        frozen_row=frozen_row, argv=(), stdin=b"",
        support_manifest=support, private_root=owner.root,
        evidence_bytes=capture.stdout, receipt_bytes=rebuilt,
        replacement_evidence_bytes=b"replacement-evidence-v1",
        replacement_receipt_bytes=b"replacement-receipt-v1")
    if (_rebuild_private_synthetic_run_receipt(
            receipt=receipt, frozen_row=frozen_row) != rebuilt
            or observed.evidence_sha256 != evidence_sha
            or observed.receipt_sha256 != receipt_sha
            or not (observed.revalidation_refused and observed.cleanup_refused
                and observed.originals_held and observed.replacements_preserved)
            or observed.case_result is not None):
        raise ValueError("attested replacement observation changed")
    info = os.lstat(owner.root)
    if ((info.st_dev, info.st_ino) != owner._identity
            or not stat.S_ISDIR(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("attested replacement root changed")
    return observed
