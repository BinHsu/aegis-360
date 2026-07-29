"""Apply detector-refresh outcomes to the bounded track lifecycle."""

from __future__ import annotations

from .detector_refresh import RefreshOutcome
from .tracking_policy import (
    ObservationKind,
    TrackEvent,
    TrackPolicyState,
    TrackingPolicy,
    advance_track,
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
