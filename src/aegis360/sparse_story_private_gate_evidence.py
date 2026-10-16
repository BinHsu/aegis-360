"""Bind the complete private case result to its separate scheduled packet.

This is live synthetic evidence, not a capability or public aggregate.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from dataclasses import dataclass, field

from .sparse_story_private_case_result import (
    _PrivateCaseResultRebuild, _revalidate_private_synthetic_case_result,
)
from .sparse_story_private_scheduled_publication import (
    _PrivateScheduledPublication,
)
from .sparse_story_batch_policy import _require_live


@dataclass(frozen=True, slots=True)
class _PrivateSyntheticGateEvidence:
    case_result: _PrivateCaseResultRebuild = field(repr=False)
    publication: _PrivateScheduledPublication = field(repr=False)
    packet_id: str
    case_result_sha256: str
    schedule_sha256: str
    backend_manifest_sha256: str
    runner_policy_sha256: str
    compiled_policy_sha256: str
    capability_receipt_sha256: str
    receipt_sha256: str
    evidence_sha256: str
    authority: bool = False

    def revalidate(self):
        if (type(self.case_result) is not _PrivateCaseResultRebuild
                or type(self.publication) is not _PrivateScheduledPublication
                or self.authority is not False):
            raise ValueError("private gate evidence type or authority differs")
        _revalidate_private_synthetic_case_result(self.case_result)
        evidence_sha, receipt_sha = self.publication.revalidate()
        schedule = self.publication.receipt._schedule
        result = json.loads(self.case_result.bytes)
        manifest = self.case_result._manifest
        case_claims = [row.proof.claim for row in self.case_result._complete.rows]
        repeat_claims = [self.case_result._repeat._first_claim,
            self.case_result._repeat._second_claim]
        scheduled_claim = schedule._claim
        candidate = schedule._candidate
        capability = scheduled_claim.receipt_bytes()
        capability_value = json.loads(capability)
        derived_inputs = {
            "schedule_sha256": schedule.schedule_sha256,
            "backend_manifest_sha256": hashlib.sha256(
                candidate._backend_bytes).hexdigest(),
            "runner_policy_sha256": hashlib.sha256(
                candidate._runner_policy_bytes).hexdigest(),
            "compiled_policy_sha256": hashlib.sha256(
                candidate._policy_bytes()).hexdigest(),
            "capability_receipt_sha256": hashlib.sha256(
                capability).hexdigest(),
        }
        if (schedule._case_manifest is not manifest
                or schedule.case_manifest_sha256
                    != self.case_result._complete.manifest_sha256
                or schedule.packet_id != manifest["repeat_packet_id"]
                or result["repeatability"]["packet_id"] != schedule.packet_id
                or not result["repeatability"]["equal"]
                or any(row["passed"] is not True for row in result["cases"])
                or len(case_claims) != 37 or len(repeat_claims) != 2
                or len({id(claim) for claim in
                    [*case_claims, *repeat_claims, scheduled_claim]}) != 40
                or len({id(claim._session._candidate) for claim in
                    [*case_claims, *repeat_claims, scheduled_claim]}) != 40
                or self.packet_id != schedule.packet_id
                or self.case_result_sha256 != self.case_result.sha256
                or any(getattr(self, key) != value
                    for key, value in derived_inputs.items())
                or capability_value["backend_manifest_sha256"]
                    != derived_inputs["backend_manifest_sha256"]
                or capability_value["runner_policy_sha256"]
                    != derived_inputs["runner_policy_sha256"]
                or capability_value["compiled_policy_sha256"]
                    != derived_inputs["compiled_policy_sha256"]
                or self.receipt_sha256 != receipt_sha
                or self.evidence_sha256 != evidence_sha):
            raise ValueError("private gate case result and packet differ")
        runtime_sha = manifest["synthetic_adapter_manifest_sha256"]
        for claim in [*case_claims, *repeat_claims, scheduled_claim]:
            live = _require_live(claim._session._candidate._facade)
            if (live._adapter_binding._runtime.backend_identity()[2]
                    != runtime_sha):
                raise ValueError("private gate runtime manifest differs")
        return self


def _bind_private_synthetic_gate_evidence(*, case_result, publication):
    if (type(case_result) is not _PrivateCaseResultRebuild
            or type(publication) is not _PrivateScheduledPublication):
        raise TypeError("private gate requires result and publication proofs")
    schedule = publication.receipt._schedule
    candidate = schedule._candidate
    proof = _PrivateSyntheticGateEvidence(case_result, publication,
        schedule.packet_id, case_result.sha256, schedule.schedule_sha256,
        hashlib.sha256(candidate._backend_bytes).hexdigest(),
        hashlib.sha256(candidate._runner_policy_bytes).hexdigest(),
        hashlib.sha256(candidate._policy_bytes()).hexdigest(),
        hashlib.sha256(schedule._claim.receipt_bytes()).hexdigest(),
        publication.receipt_sha256, publication.evidence_sha256)
    return proof.revalidate()


_FINALIZED_TOKEN = object()


class _PrivateFinalizedSyntheticGate:
    """Retain exact private hashes only after all 40 owned sessions close."""

    __slots__ = ("_token", "_sessions", "_publication", "packet_id",
        "input_hashes", "case_result_sha256", "receipt_sha256",
        "evidence_sha256", "authority", "_seal")

    def __setattr__(self, _name, _value):
        raise TypeError("finalized private gate is immutable")

    def _seal_hash(self):
        payload = (self.packet_id, self.input_hashes,
            self.case_result_sha256, self.receipt_sha256,
            self.evidence_sha256, id(self._publication), tuple(
                (id(session), str(session._batch_scratch.root),
                    session._batch_scratch.root_identity)
                for session in self._sessions))
        return hashlib.sha256(json.dumps(payload,
            separators=(",", ":")).encode()).hexdigest()

    def __init__(self, token, sessions, publication, source):
        if token is not _FINALIZED_TOKEN:
            raise TypeError("finalized gate requires owned cleanup")
        object.__setattr__(self, "_token", token)
        object.__setattr__(self, "_sessions", sessions)
        object.__setattr__(self, "_publication", publication)
        object.__setattr__(self, "packet_id", source.packet_id)
        object.__setattr__(self, "input_hashes", tuple((key, getattr(source, key)) for key in (
            "schedule_sha256", "backend_manifest_sha256",
            "runner_policy_sha256", "compiled_policy_sha256",
            "capability_receipt_sha256")))
        object.__setattr__(self, "case_result_sha256", source.case_result_sha256)
        object.__setattr__(self, "receipt_sha256", source.receipt_sha256)
        object.__setattr__(self, "evidence_sha256", source.evidence_sha256)
        object.__setattr__(self, "authority", False)
        object.__setattr__(self, "_seal", self._seal_hash())
        self.revalidate()

    def revalidate(self):
        owner = self._publication.owner
        info = os.lstat(owner.root)
        if (self._token is not _FINALIZED_TOKEN or self.authority is not False
                or self._seal != self._seal_hash()
                or len(self._sessions) != 40
                or len({id(session) for session in self._sessions}) != 40
                or any(not session._closed or not session._batch_scratch.closed
                    for session in self._sessions)
                or any(os.path.lexists(session._batch_scratch.root)
                    for session in self._sessions)
                or not owner._used
                or (info.st_dev, info.st_ino) != owner._identity
                or not stat.S_ISDIR(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o700
                or set(os.listdir(owner.root)) != {
                    "evidence.json", "receipt.json"}
                or self._publication.pair.revalidate() != (
                    self.evidence_sha256, self.receipt_sha256)):
            raise ValueError("private gate cleanup or publication differs")
        return self


def _finalize_private_synthetic_gate_once(proof):
    if type(proof) is not _PrivateSyntheticGateEvidence:
        raise TypeError("private gate finalization requires exact live proof")
    proof.revalidate()
    case_claims = [row.proof.claim for row in proof.case_result._complete.rows]
    repeat = proof.case_result._repeat
    claims = [*case_claims, repeat._first_claim, repeat._second_claim,
        proof.publication.receipt._schedule._claim]
    sessions = tuple(claim._session for claim in claims)
    for session in sessions:
        session.close()
    return _PrivateFinalizedSyntheticGate(_FINALIZED_TOKEN, sessions,
        proof.publication, proof)
