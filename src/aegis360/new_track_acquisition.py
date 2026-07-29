"""Bounded post-termination acquisition of a fresh semantic track."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True)
class AcquisitionPolicy:
    consecutive_compatible: int = 2

    def __post_init__(self) -> None:
        if (
            isinstance(self.consecutive_compatible, bool)
            or not isinstance(self.consecutive_compatible, int)
            or self.consecutive_compatible < 2
        ):
            raise ValueError("acquisition requires at least two confirmations")


def evaluate_new_track_acquisition(
    refresh_trace: Mapping[str, object],
    *,
    terminated_at: float,
    new_track_id: str,
    policy: AcquisitionPolicy = AcquisitionPolicy(),
) -> dict[str, object]:
    """Evaluate later detections without linking them to the terminated ID."""

    if refresh_trace.get("schema_version") != "aegis360.detector-refresh-trace.v1":
        raise ValueError("unsupported refresh trace schema")
    if (
        not isinstance(terminated_at, (int, float))
        or not math.isfinite(terminated_at)
        or not isinstance(new_track_id, str)
        or not new_track_id
    ):
        raise ValueError("termination time and fresh track ID are required")
    events = refresh_trace.get("events")
    if not isinstance(events, list):
        raise ValueError("refresh events are required")

    old_ids = {
        row.get("track_id")
        for row in events
        if isinstance(row, Mapping)
    }
    if new_track_id in old_ids:
        raise ValueError("new acquisition cannot reuse a prior track ID")
    consecutive = 0
    acquired_at = None
    rows = []
    previous = float(terminated_at)
    for row in events:
        if not isinstance(row, Mapping):
            raise ValueError("refresh event must be an object")
        timestamp = row.get("timestamp")
        if (
            not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
        ):
            raise ValueError("refresh timestamp is invalid")
        timestamp = float(timestamp)
        if timestamp <= terminated_at:
            continue
        if timestamp <= previous:
            raise ValueError("post-terminal refresh timestamps must increase")
        outcome = row.get("outcome")
        if outcome == "compatible_not_identity_verified":
            consecutive += 1
        elif outcome in (
            "no_compatible_detection",
            "ambiguous_multiple_compatible",
        ):
            consecutive = 0
        else:
            raise ValueError("refresh outcome is invalid")
        if acquired_at is None and consecutive >= policy.consecutive_compatible:
            acquired_at = timestamp
        rows.append({
            "timestamp": timestamp,
            "outcome": outcome,
            "consecutive_compatible": consecutive,
            "acquired": acquired_at == timestamp,
        })
        previous = timestamp
    return {
        "schema_version": "aegis360.new-track-acquisition.v1",
        "new_track_id": new_track_id if acquired_at is not None else None,
        "acquired_at": acquired_at,
        "policy": {
            "consecutive_compatible": policy.consecutive_compatible,
            "identity_verified": False,
            "editorial_persistence_allowed": False,
        },
        "events": rows,
        "limitation": (
            "A fresh semantic track does not establish identity continuity "
            "with any terminated track."
        ),
    }
