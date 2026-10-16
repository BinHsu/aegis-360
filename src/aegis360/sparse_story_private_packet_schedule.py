"""Exact private synthetic packet schedule binding; no runner authority."""

from __future__ import annotations

import hashlib
import json

from .sparse_story_runner_contract import (
    canonical_adapter_request_shape_bytes, canonical_case_manifest_bytes,
    canonical_bytes,
)
from .sparse_story_receipt_inputs import _derive_private_receipt_inputs

_SCHEMA = "aegis360.private-synthetic-packet-schedule.v1"


class _PrivateSyntheticPacketSchedule:
    """Retain one claim and one manifest for a later, separate invocation proof.

    The serialized shape contains only digests and a packet ID. It is private
    evidence, and its hash is not a public schedule or capability receipt.
    """

    __slots__ = ("_claim", "_candidate", "_case_manifest", "_manifest_bytes",
        "_request_bytes", "_binding_sha256", "packet_id", "request_sha256",
        "projection_sha256", "case_manifest_sha256", "schedule_bytes",
        "schedule_sha256")

    def __init__(self, claim, case_manifest):
        from .sparse_story_probe_denials import _ClaimedProbedBatch

        if type(claim) is not _ClaimedProbedBatch:
            raise TypeError("private schedule requires one retained claim")
        claim.revalidate()
        if (claim._invoked or claim._session._invocation_started
                or claim._launch_ledger.count != 0):
            raise ValueError("private schedule claim was already consumed")
        candidate = claim._session._candidate
        runtime_manifest_sha256 = _derive_private_receipt_inputs(
            candidate).runtime_manifest_sha256
        if case_manifest.get("synthetic_adapter_manifest_sha256") != runtime_manifest_sha256:
            raise ValueError("private schedule adapter manifest differs from runtime")
        request_bytes = candidate._request_bytes
        request = json.loads(request_bytes)
        if canonical_adapter_request_shape_bytes(request) != request_bytes:
            raise ValueError("private schedule request is not canonical")
        manifest_bytes = canonical_case_manifest_bytes(case_manifest,
            synthetic_adapter_manifest_sha256=case_manifest.get(
                "synthetic_adapter_manifest_sha256"),
            cases=case_manifest.get("cases"),
            repeat_packet_id=case_manifest.get("repeat_packet_id"))
        packet_id = request["packet_id"]
        if packet_id != case_manifest["repeat_packet_id"]:
            raise ValueError("schedule packet differs from case repeat packet")
        binding_sha256 = candidate.invocation_binding_sha256()
        request_sha256 = hashlib.sha256(request_bytes).hexdigest()
        projection_sha256 = hashlib.sha256(canonical_bytes(
            request["projection"])).hexdigest()
        case_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        schedule_bytes = canonical_bytes({
            "schema_version": _SCHEMA,
            "run_kind": "synthetic_gate",
            "packets": [{"packet_id": packet_id,
                "adapter_request_sha256": request_sha256,
                "adapter_projection_sha256": projection_sha256,
                "candidate_binding_sha256": binding_sha256}],
            "synthetic_case_manifest_sha256": case_manifest_sha256,
        })
        self._claim = claim
        self._candidate = candidate
        self._case_manifest = case_manifest
        self._manifest_bytes = manifest_bytes
        self._request_bytes = request_bytes
        self._binding_sha256 = binding_sha256
        self.packet_id = packet_id
        self.request_sha256 = request_sha256
        self.projection_sha256 = projection_sha256
        self.case_manifest_sha256 = case_manifest_sha256
        self.schedule_bytes = schedule_bytes
        self.schedule_sha256 = hashlib.sha256(schedule_bytes).hexdigest()
        self.revalidate()

    def revalidate(self, *, allow_invoked=False):
        from .sparse_story_raw_probe_transport import _verify_native_launch_event

        if type(allow_invoked) is not bool:
            raise TypeError("private schedule invocation state must be boolean")
        claim = self._claim
        claim.revalidate()
        if claim._session._candidate is not self._candidate:
            raise ValueError("private schedule candidate changed")
        count = claim._launch_ledger.count
        if allow_invoked:
            if (not claim._invoked or not claim._session._invocation_started
                    or count != 1 or claim._launch_ledger._event is None
                    or claim._launch_ledger._event.mode != "adapter"):
                raise ValueError("private scheduled invocation is absent")
            capture = claim._session._invocation_capture
            if capture is not None:
                _verify_native_launch_event(capture,
                    candidate=self._candidate, suffix=())
        elif (claim._invoked or claim._session._invocation_started
                or count != 0):
            raise ValueError("private schedule claim was already consumed")
        if (self._candidate._request_bytes != self._request_bytes
                or self._candidate.invocation_binding_sha256()
                    != self._binding_sha256):
            raise ValueError("private schedule candidate binding changed")
        request = json.loads(self._candidate._request_bytes)
        if (canonical_adapter_request_shape_bytes(request) != self._request_bytes
                or request["packet_id"] != self.packet_id
                or hashlib.sha256(self._request_bytes).hexdigest()
                    != self.request_sha256
                or hashlib.sha256(canonical_bytes(request["projection"])).hexdigest()
                    != self.projection_sha256):
            raise ValueError("private schedule request changed")
        manifest_bytes = canonical_case_manifest_bytes(self._case_manifest,
            synthetic_adapter_manifest_sha256=self._case_manifest.get(
                "synthetic_adapter_manifest_sha256"),
            cases=self._case_manifest.get("cases"),
            repeat_packet_id=self._case_manifest.get("repeat_packet_id"))
        if (self._case_manifest["synthetic_adapter_manifest_sha256"]
                != _derive_private_receipt_inputs(
                    self._candidate).runtime_manifest_sha256):
            raise ValueError("private schedule adapter manifest differs from runtime")
        if (manifest_bytes != self._manifest_bytes
                or self._case_manifest["repeat_packet_id"] != self.packet_id
                or hashlib.sha256(manifest_bytes).hexdigest()
                    != self.case_manifest_sha256):
            raise ValueError("private schedule case manifest changed")
        rebuilt = canonical_bytes({
            "schema_version": _SCHEMA,
            "run_kind": "synthetic_gate",
            "packets": [{"packet_id": self.packet_id,
                "adapter_request_sha256": self.request_sha256,
                "adapter_projection_sha256": self.projection_sha256,
                "candidate_binding_sha256": self._binding_sha256}],
            "synthetic_case_manifest_sha256": self.case_manifest_sha256,
        })
        if (rebuilt != self.schedule_bytes
                or hashlib.sha256(rebuilt).hexdigest() != self.schedule_sha256):
            raise ValueError("private schedule bytes changed")
        return rebuilt
