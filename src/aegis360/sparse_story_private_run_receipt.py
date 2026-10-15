"""Private adapter run-receipt bytes from one retained synthetic invocation.

This is an in-memory coordinator prerequisite. It publishes nothing and does
not open the public authority-bearing receipt APIs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from .sparse_story_coordinator_cardinality import _audit_private_synthetic_cardinality
from .sparse_story_probe_denials import _ClaimedProbedBatch
from .sparse_story_raw_probe_transport import _verify_native_launch_event
from .sparse_story_receipt_inputs import _derive_private_receipt_inputs
from .sparse_story_runner_contract import (
    PACKET, PRIVACY, RECEIPT_AUTHORITY, RECEIPT_SCHEMA,
    canonical_run_receipt_shape_bytes,
)


class _PrivateRunReceipt:
    """Exact bytes bound to a live claim; no publication or case outcome."""

    __slots__ = ("_claim", "_capture", "bytes")

    def __init__(self, claim, capture, encoded):
        if (type(claim) is not _ClaimedProbedBatch or type(encoded) is not bytes):
            raise TypeError("private run receipt requires exact facts")
        self._claim = claim
        self._capture = capture
        self.bytes = encoded

    def __copy__(self):
        raise TypeError("private run receipts cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("private run receipts cannot be copied")

    def __reduce__(self):
        raise TypeError("private run receipts cannot be pickled")


def _attested_synthetic_run_facts(*, claim, frozen_row):
    """Revalidate the live candidate, exact event, row and six input hashes."""
    cardinality = _audit_private_synthetic_cardinality(
        claim=claim, frozen_row=frozen_row)
    session = claim._session
    candidate = session._candidate
    capture = cardinality.capture
    suffix = ("--aegis-synthetic-case", frozen_row["case_id"], "--",
        *frozen_row["stimulus"]["argv"])
    event = _verify_native_launch_event(capture, candidate=candidate,
        suffix=suffix)
    if (event._ledger is not claim._launch_ledger
            or claim._launch_ledger.count != 1
            or session._invocation_capture is not capture):
        raise ValueError("synthetic capture is not from the claimed launch")
    request = json.loads(candidate._request_bytes)
    packet_id = request.get("packet_id")
    if type(packet_id) is not str or PACKET.fullmatch(packet_id) is None:
        raise ValueError("retained packet ID is invalid")
    inputs = _derive_private_receipt_inputs(candidate)
    claim.revalidate()
    if (session._invocation_capture is not capture
            or capture.launch_event is not event):
        raise ValueError("synthetic capture changed during receipt derivation")
    return packet_id, inputs, capture


def _build_private_synthetic_run_receipt(*, claim, frozen_row):
    """Construct canonical bytes once from an attested synthetic capture."""
    packet_id, inputs, capture = _attested_synthetic_run_facts(
        claim=claim, frozen_row=frozen_row)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "packet_id": packet_id,
        "inputs": asdict(inputs),
        "execution": {
            "invocation_count": 1,
            "stdout_present": bool(capture.stdout),
            "stdout_sha256": hashlib.sha256(capture.stdout).hexdigest(),
            "invocation_failed": False,
        },
        "privacy": dict(PRIVACY),
        "authority": dict(RECEIPT_AUTHORITY),
    }
    encoded = canonical_run_receipt_shape_bytes(receipt)
    claim.revalidate()
    return _PrivateRunReceipt(claim, capture, encoded)


def _rebuild_private_synthetic_run_receipt(*, receipt, frozen_row):
    """Re-derive every field and independently compare exact canonical bytes."""
    if type(receipt) is not _PrivateRunReceipt:
        raise TypeError("rebuild requires a private run receipt")
    claim = receipt._claim
    packet_id, inputs, capture = _attested_synthetic_run_facts(
        claim=claim, frozen_row=frozen_row)
    if capture is not receipt._capture or type(receipt.bytes) is not bytes:
        raise ValueError("private receipt capture or bytes changed")
    try:
        parsed = json.loads(receipt.bytes)
    except (UnicodeError, ValueError) as error:
        raise ValueError("private receipt bytes are invalid") from error
    canonical_run_receipt_shape_bytes(parsed)
    # Build a fresh object from retained facts; do not compare a parsed receipt
    # to itself or call the initial builder as the purported independent proof.
    rebuilt = canonical_run_receipt_shape_bytes({
        "schema_version": RECEIPT_SCHEMA,
        "packet_id": packet_id,
        "inputs": {
            "adapter_projection_sha256": inputs.adapter_projection_sha256,
            "sanitized_media_result_sha256": inputs.sanitized_media_result_sha256,
            "runtime_manifest_sha256": inputs.runtime_manifest_sha256,
            "model_manifest_sha256": inputs.model_manifest_sha256,
            "prompt_schema_manifest_sha256": inputs.prompt_schema_manifest_sha256,
            "runner_policy_sha256": inputs.runner_policy_sha256,
        },
        "execution": {
            "invocation_count": 1,
            "stdout_present": len(capture.stdout) > 0,
            "stdout_sha256": hashlib.sha256(capture.stdout).hexdigest(),
            "invocation_failed": False,
        },
        "privacy": dict(PRIVACY),
        "authority": dict(RECEIPT_AUTHORITY),
    })
    if receipt.bytes != rebuilt:
        raise ValueError("private adapter run receipt does not exactly rebuild")
    claim.revalidate()
    return rebuilt
