"""Apply detector-refresh outcomes to the bounded track lifecycle."""

from __future__ import annotations

import json
import math

from .detector_refresh import RefreshOutcome
from .tracking_policy import (
    ObservationKind,
    TrackEvent,
    TrackPolicyState,
    TrackingPolicy,
    advance_track,
    start_track,
)


def refresh_track_event(
    frame_index: int,
    outcome: RefreshOutcome,
    *,
    tracker_confidence: float | None,
) -> TrackEvent:
    """Convert refresh evidence without treating ambiguity as observation."""

    if outcome is RefreshOutcome.COMPATIBLE:
        return TrackEvent(
            frame_index, ObservationKind.OBSERVED, tracker_confidence
        )
    return TrackEvent(frame_index, ObservationKind.NOT_OBSERVED)


def advance_refresh_lifecycle(
    state: TrackPolicyState,
    *,
    frame_index: int,
    outcome: RefreshOutcome,
    tracker_confidence: float | None,
    policy: TrackingPolicy,
) -> TrackPolicyState:
    return advance_track(
        state,
        refresh_track_event(
            frame_index, outcome, tracker_confidence=tracker_confidence
        ),
        policy,
    )


def build_refresh_lifecycle_trace(
    refresh_trace: dict[str, object],
    tracker_confidences: dict[float, float],
    *,
    policy: TrackingPolicy,
) -> dict[str, object]:
    """Materialize bounded lifecycle states without retaining native paths."""

    if refresh_trace.get("schema_version") != "aegis360.detector-refresh-trace.v1":
        raise ValueError("unsupported refresh trace schema")
    source_id = refresh_trace.get("source_id")
    events = refresh_trace.get("events")
    if not isinstance(source_id, str) or not source_id or not isinstance(events, list):
        raise ValueError("refresh trace source and events are required")

    state = None
    rows: list[dict[str, object]] = []
    previous_timestamp = -math.inf
    track_id = None
    for frame_index, row in enumerate(events):
        if not isinstance(row, dict):
            raise ValueError("refresh event must be an object")
        timestamp = row.get("timestamp")
        current_track_id = row.get("track_id")
        try:
            outcome = RefreshOutcome(row.get("outcome"))
        except (TypeError, ValueError) as error:
            raise ValueError("refresh outcome is invalid") from error
        if (
            not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
            or timestamp <= previous_timestamp
            or not isinstance(current_track_id, str)
            or not current_track_id
            or row.get("editorial_persistence_allowed") is not False
        ):
            raise ValueError("refresh event contract is invalid")
        if track_id is None:
            track_id = current_track_id
        elif current_track_id != track_id:
            raise ValueError("lifecycle trace cannot change track ID")

        confidence = tracker_confidences.get(float(timestamp))
        if outcome is RefreshOutcome.COMPATIBLE:
            if confidence is None:
                raise ValueError("compatible refresh requires tracker confidence")
        else:
            confidence = None

        if state is None:
            if outcome is not RefreshOutcome.COMPATIBLE:
                raise ValueError("lifecycle must start with compatible refresh")
            state = start_track(
                track_id,
                refresh_track_event(
                    frame_index, outcome, tracker_confidence=confidence
                ),
            )
        else:
            state = advance_refresh_lifecycle(
                state,
                frame_index=frame_index,
                outcome=outcome,
                tracker_confidence=confidence,
                policy=policy,
            )
        rows.append({
            "timestamp": timestamp,
            "outcome": outcome.value,
            "phase": state.phase.value,
            "confidence": state.confidence,
            "consecutive_missing": state.consecutive_missing,
            "termination_reason": (
                state.termination_reason.value
                if state.termination_reason is not None else None
            ),
            "editorial_persistence_allowed": False,
            "identity_verified": False,
        })
        previous_timestamp = timestamp

    if not rows:
        raise ValueError("at least one refresh event is required")
    return {
        "schema_version": "aegis360.refresh-lifecycle-trace.v1",
        "source_id": source_id,
        "track_id": track_id,
        "policy": {
            "missing_grace_refreshes": policy.missing_grace_frames,
            "confidence_decay": policy.confidence_decay,
        },
        "states": rows,
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "limitation": (
            "Operational continuity only; semantic identity and editorial "
            "persistence remain unverified."
        ),
    }


def dumps_refresh_lifecycle_trace(document: dict[str, object]) -> str:
    return json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
