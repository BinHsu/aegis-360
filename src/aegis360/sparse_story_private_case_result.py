"""Private, evidence-bound reconstruction of one synthetic case result.

The public case-result and aggregate APIs remain closed. The returned bytes are
an in-memory shape check while every retained owner is live.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .sparse_story_private_byte_repeat import (
    _PrivateNativeByteRepeat, _revalidate_private_native_byte_repeat,
)
from .sparse_story_private_complete_cases import (
    _PrivateCompleteSyntheticObservations,
    _revalidate_private_complete_synthetic_observations,
)
from .sparse_story_runner_contract import (
    CASE_RESULT_SCHEMA, canonical_case_result_shape_bytes,
    validate_case_manifest,
)


@dataclass(frozen=True, slots=True)
class _PrivateCaseResultRebuild:
    bytes: bytes
    sha256: str
    _complete: _PrivateCompleteSyntheticObservations = field(
        repr=False, compare=False)
    _repeat: _PrivateNativeByteRepeat = field(repr=False, compare=False)
    _manifest: dict = field(repr=False, compare=False)
    _prepared_owners: dict = field(repr=False, compare=False)
    authority: bool = False


def _portable_request(claim):
    request = json.loads(claim._session._candidate._request_bytes)
    for role in ("model", "prompt_schema"):
        request[role].pop("root_path")
    return request


def _rebuild_private_synthetic_case_result(*, frozen_manifest,
        complete_proof, repeat_proof, prepared_owners):
    """Derive every field from still-live ordered and byte-repeat proofs."""
    if (type(complete_proof) is not _PrivateCompleteSyntheticObservations
            or type(repeat_proof) is not _PrivateNativeByteRepeat):
        raise ValueError("private case result proofs differ")
    validate_case_manifest(frozen_manifest,
        synthetic_adapter_manifest_sha256=frozen_manifest.get(
            "synthetic_adapter_manifest_sha256"),
        cases=frozen_manifest.get("cases"),
        repeat_packet_id=frozen_manifest.get("repeat_packet_id"))
    _revalidate_private_complete_synthetic_observations(
        proof=complete_proof, frozen_manifest=frozen_manifest,
        prepared_owners=prepared_owners)
    _revalidate_private_native_byte_repeat(repeat_proof)
    if (repeat_proof.packet_id != frozen_manifest["repeat_packet_id"]
            or repeat_proof._frozen_row != frozen_manifest["cases"][2]):
        raise ValueError("private repeat row differs from frozen schedule")
    scheduled_claims = [row.proof.claim for row in complete_proof.rows]
    repeat_claims = [repeat_proof._first_claim, repeat_proof._second_claim]
    if (len({id(claim) for claim in scheduled_claims + repeat_claims}) != 39
            or len({id(claim._session._candidate)
                for claim in scheduled_claims + repeat_claims}) != 39
            or len({claim._session._candidate._proofs[0]._root
                for claim in scheduled_claims + repeat_claims}) != 39
            or _portable_request(repeat_claims[0])
                != _portable_request(scheduled_claims[0])
            or _portable_request(repeat_claims[1])
                != _portable_request(scheduled_claims[0])):
        raise ValueError("private repeat claims differ from scheduled packet")
    rows = []
    for frozen, observed in zip(frozen_manifest["cases"],
            complete_proof.rows):
        if frozen["case_id"] != observed.case_id:
            raise ValueError("private case result row order differs")
        rows.append({"case_id": frozen["case_id"],
            "expected_result": frozen["expected_result"],
            "observed_result": observed.observed_result,
            "passed": observed.observed_result == frozen["expected_result"]})
    value = {"schema_version": CASE_RESULT_SCHEMA,
        "case_manifest_sha256": complete_proof.manifest_sha256,
        "cases": rows,
        "repeatability": {"packet_id": repeat_proof.packet_id,
            "first_stdout_sha256": repeat_proof.first_stdout_sha256,
            "second_stdout_sha256": repeat_proof.second_stdout_sha256,
            "equal": repeat_proof.equal}}
    encoded = canonical_case_result_shape_bytes(value,
        case_manifest=frozen_manifest)
    return _PrivateCaseResultRebuild(encoded,
        hashlib.sha256(encoded).hexdigest(), complete_proof, repeat_proof,
        frozen_manifest, prepared_owners)


def _revalidate_private_synthetic_case_result(proof):
    """Rebuild a private result before any later in-memory consumer uses it."""
    if type(proof) is not _PrivateCaseResultRebuild or proof.authority is not False:
        raise ValueError("private case result proof is invalid")
    rebuilt = _rebuild_private_synthetic_case_result(
        frozen_manifest=proof._manifest, complete_proof=proof._complete,
        repeat_proof=proof._repeat, prepared_owners=proof._prepared_owners)
    if proof.bytes != rebuilt.bytes or proof.sha256 != rebuilt.sha256:
        raise ValueError("private case result bytes changed")
    return proof
