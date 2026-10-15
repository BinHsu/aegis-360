"""Private replacement observation over two published opaque peers.

This deliberately returns no protocol enum: adapter receipt lineage and the
complete coordinator-owned case result are separate unfinished boundaries.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .sparse_story_coordinator_replacement import _create_owned_peer, _file_facts
from .sparse_story_media_tree import _rename_exclusive
from .sparse_story_private_publication import (
    PublicationIncomplete, _publish_private_pair,
)
from .sparse_story_runner_contract import canonical_asset_manifest_shape_bytes


@dataclass(frozen=True)
class _PrivateReplacementObservation:
    revalidation_refused: bool
    cleanup_refused: bool
    originals_held: bool
    replacements_preserved: bool
    evidence_sha256: str
    receipt_sha256: str
    case_result: None = None


def _verify_row(*, frozen_row: Mapping[str, object], argv: tuple[str, ...],
                stdin: bytes, support_manifest: Mapping[str, object]) -> None:
    if (not isinstance(frozen_row, Mapping)
            or set(frozen_row) != {"case_id", "expected_result", "stimulus"}
            or frozen_row["case_id"] != "replacement_race"
            or frozen_row["expected_result"] != "replacement_preserved"
            or not isinstance(frozen_row["stimulus"], Mapping)
            or set(frozen_row["stimulus"]) != {
                "argv", "stdin_sha256", "support_manifest_sha256"}
            or type(argv) is not tuple or len(argv) > 8
            or any(type(value) is not str or not value or "\x00" in value
                   for value in argv)
            or type(stdin) is not bytes or len(stdin) > 1_048_576):
        raise ValueError("replacement frozen row is invalid")
    support = canonical_asset_manifest_shape_bytes(support_manifest)
    if (support_manifest["asset_kind"] != "synthetic_support"
            or frozen_row["stimulus"] != {
                "argv": list(argv),
                "stdin_sha256": hashlib.sha256(stdin).hexdigest(),
                "support_manifest_sha256": hashlib.sha256(support).hexdigest()}):
        raise ValueError("replacement frozen stimulus changed")


def _observe_private_replacement_race(*, frozen_row: Mapping[str, object],
        argv: tuple[str, ...], stdin: bytes,
        support_manifest: Mapping[str, object], private_root: Path,
        evidence_bytes: bytes, receipt_bytes: bytes,
        replacement_evidence_bytes: bytes,
        replacement_receipt_bytes: bytes) -> _PrivateReplacementObservation:
    """Publish, replace both names, and prove the publisher refuses cleanup.

    Caller owns an empty private root and its eventual cleanup. Failure leaves
    created paths intact for inspection. No model or adapter is invoked here.
    """
    _verify_row(frozen_row=frozen_row, argv=argv, stdin=stdin,
                support_manifest=support_manifest)
    if (not isinstance(private_root, Path)
            or any(type(value) is not bytes for value in (
                evidence_bytes, receipt_bytes, replacement_evidence_bytes,
                replacement_receipt_bytes))):
        raise ValueError("replacement peer inputs are invalid")
    info = os.lstat(private_root)
    if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700
            or os.listdir(private_root)):
        raise ValueError("replacement private root must be empty and owner-only")
    evidence_path = private_root / "evidence.json"
    receipt_path = private_root / "receipt.json"
    pair = _publish_private_pair(evidence_path=evidence_path,
        receipt_path=receipt_path, evidence_bytes=evidence_bytes,
        receipt_bytes=receipt_bytes)
    pair.revalidate()
    held_paths = (private_root / "held-evidence.json",
                  private_root / "held-receipt.json")
    _rename_exclusive(evidence_path, held_paths[0])
    _rename_exclusive(receipt_path, held_paths[1])
    replacements = (
        _create_owned_peer(evidence_path, replacement_evidence_bytes),
        _create_owned_peer(receipt_path, replacement_receipt_bytes))
    try:
        pair.revalidate()
    except PublicationIncomplete:
        revalidation_refused = True
    else:
        raise ValueError("publisher accepted replacement peers")
    try:
        pair.cleanup()
    except PublicationIncomplete as error:
        if error.removed_roles:
            raise ValueError("publisher removed a peer during replacement cleanup") from error
        cleanup_refused = True
    else:
        raise ValueError("publisher accepted replacement cleanup")
    if (not all(_file_facts(peer.path) == (peer.identity, peer.sha256)
                for peer in replacements)
            or _file_facts(held_paths[0]) != (
                pair._evidence.identity, pair.evidence_sha256)
            or _file_facts(held_paths[1]) != (
                pair._receipt.identity, pair.receipt_sha256)):
        raise ValueError("original or replacement peer changed")
    return _PrivateReplacementObservation(
        revalidation_refused, cleanup_refused, True, True,
        pair.evidence_sha256, pair.receipt_sha256)
