"""Adapt a bounded refresh lifecycle to planner candidate frames."""

from __future__ import annotations

import math
from typing import Mapping

from .candidate_sequence import (
    AssociationProvenance, CandidateFrame, TemporalCandidate,
)
from .geometry import wrap_yaw


def lifecycle_candidate_frames(
    lifecycle: Mapping[str, object],
    tracking: Mapping[str, object],
    *,
    horizontal_fov: float,
    candidate_type: str,
    forward_yaw: float = 0,
    forward_pitch: float = 0,
) -> tuple[CandidateFrame, ...]:
    """Expose a lifecycle candidate only before its terminal state.

    Operational detector/tracker compatibility remains geometric-only and
    never grants editorial persistence. Tracking observations after
    termination receive only the forward fallback; a later detection requires
    a separately acquired lifecycle and track ID.
    """

    if lifecycle.get("schema_version") != "aegis360.refresh-lifecycle-trace.v1":
        raise ValueError("unsupported lifecycle schema")
    if (
        not math.isfinite(horizontal_fov)
        or not 0 < horizontal_fov < math.pi
        or not isinstance(candidate_type, str)
        or not candidate_type.strip()
        or not math.isfinite(forward_yaw)
        or not math.isfinite(forward_pitch)
        or not -math.pi / 2 <= forward_pitch <= math.pi / 2
    ):
        raise ValueError("candidate or forward geometry is invalid")
    track_id = lifecycle.get("track_id")
    if (
        not isinstance(track_id, str)
        or not track_id
        or tracking.get("trackId") != track_id
    ):
        raise ValueError("lifecycle and tracking IDs must match")
    states = lifecycle.get("states")
    observations = tracking.get("observations")
    if not isinstance(states, list) or not states:
        raise ValueError("lifecycle states are required")
    if not isinstance(observations, list) or not observations:
        raise ValueError("tracking observations are required")
    state_by_timestamp = {}
    terminal_timestamp = None
    previous = -math.inf
    for state in states:
        if not isinstance(state, Mapping):
            raise ValueError("lifecycle state must be an object")
        timestamp = state.get("timestamp")
        phase = state.get("phase")
        if (
            not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
            or timestamp <= previous
            or phase not in ("active", "missing_grace", "terminated")
            or state.get("editorial_persistence_allowed") is not False
            or state.get("identity_verified") is not False
        ):
            raise ValueError("lifecycle state is invalid")
        if terminal_timestamp is not None:
            raise ValueError("lifecycle cannot continue after termination")
        state_by_timestamp[float(timestamp)] = state
        if phase == "terminated":
            terminal_timestamp = float(timestamp)
        previous = float(timestamp)

    output = []
    first_timestamp = float(states[0]["timestamp"])
    observed_frames = 0
    previous = -math.inf
    for frame_index, observation in enumerate(observations):
        if not isinstance(observation, Mapping):
            raise ValueError("tracking observation must be an object")
        timestamp = observation.get("timestampSeconds")
        if (
            not isinstance(timestamp, (int, float))
            or not math.isfinite(timestamp)
            or timestamp <= previous
        ):
            raise ValueError("tracking timestamps must increase")
        timestamp = float(timestamp)
        state = state_by_timestamp.get(timestamp)
        if timestamp < first_timestamp or (
            state is None
            and (terminal_timestamp is None or timestamp <= terminal_timestamp)
        ):
            raise ValueError("tracking and lifecycle timestamps must align")
        candidates = []
        if state is not None and state["phase"] != "terminated":
            yaw = observation.get("yawRadians")
            pitch = observation.get("pitchRadians")
            if (
                observation.get("state") != "tracked"
                or not isinstance(yaw, (int, float))
                or not math.isfinite(yaw)
                or not isinstance(pitch, (int, float))
                or not math.isfinite(pitch)
            ):
                raise ValueError("candidate requires tracked spherical geometry")
            observed = state["phase"] == "active"
            if observed:
                observed_frames += 1
            candidates.append(TemporalCandidate(
                candidate_id=f"lifecycle:{track_id}",
                track_id=track_id,
                yaw=wrap_yaw(float(yaw)),
                pitch=float(pitch),
                h_fov=horizontal_fov,
                candidate_type=candidate_type,
                observed=observed,
                observed_frames=observed_frames,
                age_frames=frame_index + 1,
                missing_frames=int(state["consecutive_missing"]),
                source_candidate_id=None,
                association_provenance=AssociationProvenance.GEOMETRIC_ONLY,
            ))
        candidates.append(TemporalCandidate(
            candidate_id="context:forward",
            track_id=None,
            yaw=wrap_yaw(forward_yaw),
            pitch=forward_pitch,
            h_fov=horizontal_fov,
            candidate_type="context",
            observed=True,
            observed_frames=frame_index + 1,
            age_frames=frame_index + 1,
            missing_frames=0,
            source_candidate_id=None,
            association_provenance=AssociationProvenance.SYNTHETIC_CONTEXT,
        ))
        output.append(CandidateFrame(
            timestamp,
            frame_index,
            tuple(sorted(candidates, key=lambda item: item.candidate_id)),
        ))
        previous = timestamp
    return tuple(output)
