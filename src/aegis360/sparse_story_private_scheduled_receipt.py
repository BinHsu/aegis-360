"""Private receipt for one ordinary schedule-bound synthetic packet call."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from .sparse_story_private_packet_schedule import _PrivateSyntheticPacketSchedule
from .sparse_story_raw_probe_transport import (
    _RawProbeCapture, _verify_native_launch_event,
)
from .sparse_story_receipt_inputs import _derive_private_receipt_inputs
from .sparse_story_runner_contract import (
    PRIVACY, RECEIPT_AUTHORITY, RECEIPT_SCHEMA,
    canonical_run_receipt_shape_bytes,
)
from .sparse_story_semantics import _strict_raw


class _PrivateScheduledRunReceipt:
    """Live receipt bytes; no published result or aggregate authority."""

    __slots__ = ("_schedule", "_capture", "bytes")

    def __init__(self, schedule, capture, encoded):
        if (type(schedule) is not _PrivateSyntheticPacketSchedule
                or type(capture) is not _RawProbeCapture
                or type(encoded) is not bytes):
            raise TypeError("scheduled receipt requires exact private facts")
        self._schedule = schedule
        self._capture = capture
        self.bytes = encoded


def _attested_scheduled_capture(schedule):
    if type(schedule) is not _PrivateSyntheticPacketSchedule:
        raise TypeError("scheduled receipt requires a retained private schedule")
    schedule.revalidate(allow_invoked=True)
    claim = schedule._claim
    capture = claim._session._invocation_capture
    if (type(capture) is not _RawProbeCapture or not capture.completed
            or capture.group_gone is not True
            or capture.postcheck_passed is not True
            or capture.returncode != 0
            or type(capture.stdout) is not bytes or not capture.stdout):
        raise ValueError("scheduled packet capture is incomplete")
    event = _verify_native_launch_event(capture,
        candidate=schedule._candidate, suffix=())
    if (event._ledger is not claim._launch_ledger
            or claim._launch_ledger.count != 1
            or event.mode != "adapter"):
        raise ValueError("scheduled packet native launch differs")
    _strict_raw(capture.stdout)
    inputs = _derive_private_receipt_inputs(schedule._candidate)
    schedule.revalidate(allow_invoked=True)
    if claim._session._invocation_capture is not capture:
        raise ValueError("scheduled packet capture changed")
    return capture, inputs


def _scheduled_receipt_bytes(schedule, capture, inputs):
    return canonical_run_receipt_shape_bytes({
        "schema_version": RECEIPT_SCHEMA,
        "packet_id": schedule.packet_id,
        "inputs": asdict(inputs),
        "execution": {
            "invocation_count": 1,
            "stdout_present": bool(capture.stdout),
            "stdout_sha256": hashlib.sha256(capture.stdout).hexdigest(),
            "invocation_failed": False,
        },
        "privacy": dict(PRIVACY),
        "authority": dict(RECEIPT_AUTHORITY),
    })


def _build_private_scheduled_run_receipt(schedule):
    capture, inputs = _attested_scheduled_capture(schedule)
    encoded = _scheduled_receipt_bytes(schedule, capture, inputs)
    schedule.revalidate(allow_invoked=True)
    return _PrivateScheduledRunReceipt(schedule, capture, encoded)


def _rebuild_private_scheduled_run_receipt(receipt):
    if type(receipt) is not _PrivateScheduledRunReceipt:
        raise TypeError("scheduled receipt must retain its native proof")
    capture, inputs = _attested_scheduled_capture(receipt._schedule)
    if capture is not receipt._capture or type(receipt.bytes) is not bytes:
        raise ValueError("scheduled receipt capture or bytes changed")
    try:
        parsed = json.loads(receipt.bytes)
    except (UnicodeError, ValueError) as error:
        raise ValueError("scheduled receipt bytes are invalid") from error
    if (canonical_run_receipt_shape_bytes(parsed) != receipt.bytes
            or _scheduled_receipt_bytes(receipt._schedule, capture, inputs)
                != receipt.bytes):
        raise ValueError("scheduled receipt does not exactly rebuild")
    return receipt.bytes
