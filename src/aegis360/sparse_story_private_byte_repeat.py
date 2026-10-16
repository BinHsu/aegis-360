"""Two fresh native fixture captures for private byte-repeat evidence only."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .sparse_story_coordinator_cardinality import _audit_private_synthetic_cardinality
from .sparse_story_probe_denials import _ClaimedProbedBatch
from .sparse_story_raw_probe_transport import _verify_native_launch_event
from .sparse_story_runner_contract import PACKET
from .sparse_story_runner_contract import canonical_asset_manifest_shape_bytes
from .sparse_story_synthetic_plan import _fixed_stimulus_from_retained_claim


@dataclass(frozen=True, slots=True)
class _PrivateNativeByteRepeat:
    packet_id: str
    case_id: str
    first_stdout_sha256: str
    second_stdout_sha256: str
    equal: bool
    _first_claim: _ClaimedProbedBatch = field(repr=False, compare=False)
    _second_claim: _ClaimedProbedBatch = field(repr=False, compare=False)
    _frozen_row: dict = field(repr=False, compare=False)


def _observe_private_native_byte_repeat(*, first_claim, second_claim,
        frozen_row, repeat_packet_id):
    """Run one identical, frozen fd fixture row in two distinct live claims.

    This deliberately returns only private observations. It cannot produce a
    public repeatability result, case result, receipt or aggregate.
    """
    if (type(first_claim) is not _ClaimedProbedBatch
            or type(second_claim) is not _ClaimedProbedBatch
            or first_claim is second_claim
            or first_claim._session is second_claim._session
            or first_claim._session._candidate is second_claim._session._candidate):
        raise TypeError("byte repeat requires two distinct retained claims")
    if (type(repeat_packet_id) is not str
            or PACKET.fullmatch(repeat_packet_id) is None
            or type(frozen_row) is not dict
            or frozen_row.get("case_id") != "fd_hygiene"):
        raise ValueError("byte repeat packet or frozen row is invalid")
    request_shape = None
    for claim in (first_claim, second_claim):
        if claim._invoked or claim._session._invocation_started:
            raise ValueError("byte repeat claim was already invoked")
        claim.revalidate()
        stimulus = _fixed_stimulus_from_retained_claim(claim, "fd_hygiene")
        expected_stimulus = {
            "argv": list(stimulus["argv"]),
            "stdin_sha256": hashlib.sha256(stimulus["stdin"]).hexdigest(),
            "support_manifest_sha256": hashlib.sha256(
                canonical_asset_manifest_shape_bytes(
                    stimulus["support_manifest"])).hexdigest(),
        }
        if frozen_row.get("stimulus") != expected_stimulus:
            raise ValueError("byte repeat row differs from retained stimulus")
        request = json.loads(claim._session._candidate._request_bytes)
        if request.get("packet_id") != repeat_packet_id:
            raise ValueError("byte repeat packet differs from retained request")
        for role in ("model", "prompt_schema"):
            request[role].pop("root_path")
        if request_shape is None:
            request_shape = request
        elif request != request_shape:
            raise ValueError("byte repeat retained packet shapes differ")

    digests = []
    for claim in (first_claim, second_claim):
        capture = claim._run_fixed_synthetic_fd_case_once(frozen_row)
        evidence = _audit_private_synthetic_cardinality(
            claim=claim, frozen_row=frozen_row)
        if capture is not evidence.capture or not capture.stdout:
            raise ValueError("byte repeat native capture is incomplete")
        event = _verify_native_launch_event(capture,
            candidate=claim._session._candidate,
            suffix=("--aegis-synthetic-case", "fd_hygiene", "--"))
        if (event._ledger is not claim._launch_ledger
                or claim._launch_ledger.count != 1):
            raise ValueError("byte repeat native launch cardinality differs")
        claim.revalidate()
        if (claim._session._invocation_capture is not capture
                or json.loads(claim._session._candidate._request_bytes).get(
                    "packet_id") != repeat_packet_id):
            raise ValueError("byte repeat capture or packet changed")
        digests.append(hashlib.sha256(capture.stdout).hexdigest())
    result = _PrivateNativeByteRepeat(repeat_packet_id, "fd_hygiene",
        digests[0], digests[1], digests[0] == digests[1],
        first_claim, second_claim, frozen_row)
    _revalidate_private_native_byte_repeat(result)
    return result


def _revalidate_private_native_byte_repeat(proof):
    """Recheck both retained captures before using private repeat facts."""
    if (type(proof) is not _PrivateNativeByteRepeat
            or type(proof.packet_id) is not str
            or PACKET.fullmatch(proof.packet_id) is None
            or proof.case_id != "fd_hygiene"
            or type(proof._frozen_row) is not dict
            or proof._frozen_row.get("case_id") != "fd_hygiene"
            or proof._first_claim is proof._second_claim):
        raise ValueError("private byte repeat proof is invalid")
    digests = []
    for claim in (proof._first_claim, proof._second_claim):
        if type(claim) is not _ClaimedProbedBatch:
            raise ValueError("private byte repeat claim differs")
        claim.revalidate()
        capture = claim._session._invocation_capture
        facts = _audit_private_synthetic_cardinality(
            claim=claim, frozen_row=proof._frozen_row)
        if capture is not facts.capture or not capture.stdout:
            raise ValueError("private byte repeat capture differs")
        event = _verify_native_launch_event(capture,
            candidate=claim._session._candidate,
            suffix=("--aegis-synthetic-case", "fd_hygiene", "--"))
        if (event._ledger is not claim._launch_ledger
                or claim._launch_ledger.count != 1):
            raise ValueError("private byte repeat launch differs")
        packet_id = json.loads(claim._session._candidate._request_bytes).get(
            "packet_id")
        if packet_id != proof.packet_id:
            raise ValueError("private byte repeat packet differs")
        digests.append(hashlib.sha256(capture.stdout).hexdigest())
    if (proof.first_stdout_sha256 != digests[0]
            or proof.second_stdout_sha256 != digests[1]
            or proof.equal is not (digests[0] == digests[1])):
        raise ValueError("private byte repeat hashes differ")
    return proof
