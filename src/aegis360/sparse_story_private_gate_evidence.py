"""Bind the complete private case result to its separate scheduled packet.

This is live synthetic evidence, not a capability or public aggregate.
"""

from __future__ import annotations

import json
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
    proof = _PrivateSyntheticGateEvidence(case_result, publication,
        publication.receipt._schedule.packet_id, case_result.sha256,
        publication.receipt_sha256, publication.evidence_sha256)
    return proof.revalidate()
