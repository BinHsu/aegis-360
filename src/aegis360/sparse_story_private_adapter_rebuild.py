"""Rebuild the 33 private fixture observations from retained native events.

This is an in-memory check, not a case result or public authority. Call it while
all claims and prepared owners remain live, after the 33 fixture calls finish.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from .sparse_story_probe_denials import (
    _ClaimedProbedBatch, _PreparedFixedSyntheticOwner,
    _classify_fixed_synthetic_output,
)
from .sparse_story_raw_probe_transport import _verify_native_launch_event
from .sparse_story_runner_contract import CASE_SPECS, canonical_case_manifest_bytes

_COORDINATOR = {"bundle_mutation", "replacement_race", "single_invocation",
    "receipt_rebuild"}
_DENIED = {"grandchild_containment", "network_ipv4_denied",
    "network_ipv6_denied", "unix_socket_denied", "repository_read_denied",
    "protocol_read_denied", "neighbor_packet_read_denied",
    "result_read_denied", "outside_write_denied"}
_ALLOWED = {"bundle_read_allowed", "model_read_allowed",
    "prompt_read_allowed", "scratch_write_allowed"}


@dataclass(frozen=True, slots=True)
class _PrivateAdapterRowProof:
    case_id: str
    observed_result: str
    claim: _ClaimedProbedBatch
    capture: object


@dataclass(frozen=True, slots=True)
class _PrivateAdapterRowsProof:
    manifest_sha256: str
    rows: tuple[_PrivateAdapterRowProof, ...]
    authority: bool = False


def _rebuild_private_adapter_observations(*, frozen_manifest, claims,
        prepared_owners):
    """Independently classify captured bytes and the exact one-shot events."""
    manifest_bytes = canonical_case_manifest_bytes(frozen_manifest,
        synthetic_adapter_manifest_sha256=frozen_manifest.get(
            "synthetic_adapter_manifest_sha256"),
        cases=frozen_manifest.get("cases"),
        repeat_packet_id=frozen_manifest.get("repeat_packet_id"))
    expected = {case_id for case_id, _ in CASE_SPECS} - _COORDINATOR
    if (type(claims) is not dict or type(prepared_owners) is not dict
            or set(claims) | set(prepared_owners) != expected
            or set(claims) & set(prepared_owners)):
        raise ValueError("private adapter claims are incomplete")
    used = set()
    rows = []
    for frozen_row in frozen_manifest["cases"]:
        case_id = frozen_row["case_id"]
        if case_id in _COORDINATOR:
            continue
        owner = prepared_owners.get(case_id)
        if owner is not None:
            if (type(owner) is not _PreparedFixedSyntheticOwner
                    or owner.case_id != case_id or owner.state != "running"
                    or list(owner.argv) != frozen_row["stimulus"]["argv"]):
                raise ValueError("private prepared owner differs")
            claim = owner.claim
        else:
            claim = claims[case_id]
        if (type(claim) is not _ClaimedProbedBatch or id(claim) in used):
            raise ValueError("private adapter claim is duplicated or invalid")
        used.add(id(claim))
        claim.revalidate()
        claim._verify_frozen_case_stimulus(frozen_row)
        capture = claim._session._invocation_capture
        candidate = claim._session._candidate
        suffix = ("--aegis-synthetic-case", case_id, "--",
            *frozen_row["stimulus"]["argv"])
        event = _verify_native_launch_event(capture, candidate=candidate,
            suffix=suffix)
        if (event._ledger is not claim._launch_ledger
                or claim._launch_ledger.count != 1
                or capture.group_gone is not True):
            raise ValueError("private adapter launch or group proof is incomplete")
        raw = _classify_fixed_synthetic_output(capture)
        observed = ("isolation_denied" if raw == "success" else
            "invocation_failure") if case_id in _DENIED else (
            ("isolation_allowed" if raw == "success" else
                "invocation_failure") if case_id in _ALLOWED else raw)
        rows.append(_PrivateAdapterRowProof(case_id, observed, claim, capture))
    if len(rows) != 33:
        raise ValueError("private adapter rows are incomplete")
    return _PrivateAdapterRowsProof(hashlib.sha256(manifest_bytes).hexdigest(),
        tuple(rows))
