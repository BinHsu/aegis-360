"""Deterministic lifecycle policy for temporarily missing viewport tracks.

This module does not perform tracking or cross-viewport association.  It
consumes an upstream classification of each expected observation and makes
the bounded grace/termination decision explicit and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math


class ObservationKind(str, Enum):
    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    OUTSIDE_VIEWPORT = "outside_viewport"


class TrackPhase(str, Enum):
    ACTIVE = "active"
    MISSING_GRACE = "missing_grace"
    VIEWPORT_EXIT = "viewport_exit"
    TERMINATED = "terminated"


class TerminationReason(str, Enum):
    MISSING_TIMEOUT = "missing_timeout"
    VIEWPORT_EXIT_TIMEOUT = "viewport_exit_timeout"


@dataclass(frozen=True)
class TrackingPolicy:
    """Frame-count policy independent of detector frame rate and wall clock."""

    missing_grace_frames: int = 2
    viewport_exit_grace_frames: int = 1
    confidence_decay: float = 0.75

    def __post_init__(self) -> None:
        if self.missing_grace_frames < 0:
            raise ValueError("missing_grace_frames must be nonnegative")
        if self.viewport_exit_grace_frames < 0:
            raise ValueError("viewport_exit_grace_frames must be nonnegative")
        if not math.isfinite(self.confidence_decay) or not 0 <= self.confidence_decay <= 1:
            raise ValueError("confidence_decay must be finite and in [0, 1]")


@dataclass(frozen=True)
class TrackEvent:
    frame_index: int
    kind: ObservationKind
    confidence: float | None = None

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise ValueError("frame_index must be nonnegative")
        if self.kind is ObservationKind.OBSERVED:
            if (
                self.confidence is None
                or not math.isfinite(self.confidence)
                or not 0 <= self.confidence <= 1
            ):
                raise ValueError("observed events require confidence in [0, 1]")
        elif self.confidence is not None:
            raise ValueError("unobserved events cannot report confidence")


@dataclass(frozen=True)
class TrackPolicyState:
    track_id: str
    frame_index: int
    phase: TrackPhase
    confidence: float
    consecutive_missing: int = 0
    consecutive_outside: int = 0
    termination_reason: TerminationReason | None = None

    def __post_init__(self) -> None:
        if not self.track_id.strip():
            raise ValueError("track_id must be nonempty")
        if self.frame_index < 0:
            raise ValueError("frame_index must be nonnegative")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be finite and in [0, 1]")
        if self.consecutive_missing < 0 or self.consecutive_outside < 0:
            raise ValueError("consecutive counters must be nonnegative")
        if (self.phase is TrackPhase.TERMINATED) != (self.termination_reason is not None):
            raise ValueError("only terminated states have a termination reason")


def start_track(track_id: str, event: TrackEvent) -> TrackPolicyState:
    """Start a lifecycle from a real observation."""

    if event.kind is not ObservationKind.OBSERVED:
        raise ValueError("a track must start with an observed event")
    return TrackPolicyState(
        track_id=track_id,
        frame_index=event.frame_index,
        phase=TrackPhase.ACTIVE,
        confidence=event.confidence,
    )


def advance_track(
    state: TrackPolicyState, event: TrackEvent, policy: TrackingPolicy
) -> TrackPolicyState:
    """Advance one frame without inventing re-identification or handoff."""

    if state.phase is TrackPhase.TERMINATED:
        raise ValueError("terminated tracks cannot be advanced")
    if event.frame_index <= state.frame_index:
        raise ValueError("event frame_index must increase monotonically")

    if event.kind is ObservationKind.OBSERVED:
        return TrackPolicyState(
            state.track_id,
            event.frame_index,
            TrackPhase.ACTIVE,
            event.confidence,
        )

    decayed = state.confidence * policy.confidence_decay
    if event.kind is ObservationKind.NOT_OBSERVED:
        missing = state.consecutive_missing + 1
        if missing <= policy.missing_grace_frames:
            return TrackPolicyState(
                state.track_id,
                event.frame_index,
                TrackPhase.MISSING_GRACE,
                decayed,
                consecutive_missing=missing,
            )
        return TrackPolicyState(
            state.track_id,
            event.frame_index,
            TrackPhase.TERMINATED,
            decayed,
            consecutive_missing=missing,
            termination_reason=TerminationReason.MISSING_TIMEOUT,
        )

    outside = state.consecutive_outside + 1
    if outside <= policy.viewport_exit_grace_frames:
        return TrackPolicyState(
            state.track_id,
            event.frame_index,
            TrackPhase.VIEWPORT_EXIT,
            decayed,
            consecutive_outside=outside,
        )
    return TrackPolicyState(
        state.track_id,
        event.frame_index,
        TrackPhase.TERMINATED,
        decayed,
        consecutive_outside=outside,
        termination_reason=TerminationReason.VIEWPORT_EXIT_TIMEOUT,
    )
