"""Private cardinality audit for a retained synthetic adapter invocation.

This module does not issue a case result or a run receipt. In particular, the
retained session receipt belongs to the isolation probe, not to the adapter
invocation whose exact rebuild the synthetic gate requires.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .sparse_story_probe_denials import _ClaimedProbedBatch
from .sparse_story_raw_probe_transport import _RawProbeCapture
from .sparse_story_runner_contract import CASE_SPECS


@dataclass(frozen=True)
class _PrivateCardinalityEvidence:
    """Observed facts only; deliberately has no result enum or authority flag."""

    case_id: str
    claim_consumed: bool
    stdout_sha256: str
    capture: _RawProbeCapture


def _audit_private_synthetic_cardinality(*, claim, frozen_row):
    """Bind a consumed claim and its native capture to exact frozen stimulus.

    The claim's single-use guard must have been consumed by the native path.
    An independent transport event count is needed to assert cardinality one.
    This audit is a prerequisite to, not proof of, ``exact_rebuild``: an adapter
    run receipt and independent reconstruction of its bytes are still needed.
    """
    if type(claim) is not _ClaimedProbedBatch:
        raise TypeError("cardinality audit requires a private claimed batch")
    if (type(frozen_row) is not dict or set(frozen_row) != {
            "case_id", "expected_result", "stimulus"}
            or (frozen_row["case_id"], frozen_row["expected_result"])
                not in CASE_SPECS):
        raise ValueError("cardinality audit row is invalid")
    claim.revalidate()
    session = claim._session
    capture = session._invocation_capture
    if (claim._invoked is not True or session._invocation_started is not True
            or type(capture) is not _RawProbeCapture
            or capture.completed is not True or capture.group_gone is not True
            or capture.postcheck_passed is not True
            or type(capture.returncode) is not int
            or type(capture.stdout) is not bytes):
        raise ValueError("completed native invocation capture is unproven")
    claim._verify_frozen_case_stimulus(frozen_row)
    digest = hashlib.sha256(capture.stdout).hexdigest()
    claim.revalidate()
    if session._invocation_capture is not capture:
        raise ValueError("native capture changed during cardinality audit")
    return _PrivateCardinalityEvidence(frozen_row["case_id"], True, digest, capture)
