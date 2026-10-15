"""Private exact-rebuild facts for the two coordinator-owned case rows.

The current synthetic fixture does not implement those two native case IDs.
An unrelated successful fixture invocation must not be relabelled as either
coordinator row, even when its frozen stdin/support hashes happen to match.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .sparse_story_coordinator_cardinality import _audit_private_synthetic_cardinality
from .sparse_story_private_run_receipt import (
    _PrivateRunReceipt, _rebuild_private_synthetic_run_receipt,
)
from .sparse_story_probe_denials import _ClaimedProbedBatch
from .sparse_story_raw_probe_transport import _verify_native_launch_event

_EXACT_CASES = {"single_invocation", "receipt_rebuild"}


@dataclass(frozen=True, slots=True)
class _PrivateExactRebuildFacts:
    """In-memory observation only; not a case result or publication receipt."""

    case_id: str
    launch_count: int
    receipt_sha256: str
    stdout_sha256: str


def _observe_private_exact_rebuild_facts(*, claim, executed_row, receipt):
    """Rebuild bytes from the exact native case that actually ran."""
    if (type(claim) is not _ClaimedProbedBatch
            or type(receipt) is not _PrivateRunReceipt
            or receipt._claim is not claim):
        raise TypeError("exact rebuild facts require one retained claim and receipt")
    cardinality = _audit_private_synthetic_cardinality(
        claim=claim, frozen_row=executed_row)
    capture = cardinality.capture
    if receipt._capture is not capture:
        raise ValueError("run receipt belongs to another native capture")
    candidate = claim._session._candidate
    suffix = ("--aegis-synthetic-case", executed_row["case_id"], "--",
        *executed_row["stimulus"]["argv"])
    event = _verify_native_launch_event(capture, candidate=candidate,
        suffix=suffix)
    if (event._ledger is not claim._launch_ledger
            or claim._launch_ledger.count != 1):
        raise ValueError("native launch cardinality is not exactly one")
    rebuilt = _rebuild_private_synthetic_run_receipt(
        receipt=receipt, frozen_row=executed_row)
    claim.revalidate()
    if (claim._session._invocation_capture is not capture
            or receipt.bytes != rebuilt):
        raise ValueError("exact native capture or receipt changed")
    return _PrivateExactRebuildFacts(executed_row["case_id"], 1,
        hashlib.sha256(rebuilt).hexdigest(), cardinality.stdout_sha256)


def _observe_private_exact_rebuild_case(*, claim, frozen_row, receipt):
    """Require the coordinator row itself to be the launched native case."""
    if (type(frozen_row) is not dict
            or frozen_row.get("case_id") not in _EXACT_CASES):
        raise ValueError("exact rebuild coordinator row is invalid")
    return _observe_private_exact_rebuild_facts(
        claim=claim, executed_row=frozen_row, receipt=receipt)
