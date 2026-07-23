"""Deterministic temporal association and bounded candidate generation.

The association is intentionally small and model independent.  It uses only
candidate kind and great-circle distance; detector confidence is neither a
match input nor an ordering key.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable

from .geometry import spherical_distance, wrap_yaw
from .perception import PerceptionResult


@dataclass(frozen=True)
class AssociationConfig:
    max_distance: float = math.radians(25.0)
    grace_frames: int = 2
    forward_yaw: float = 0.0
    forward_pitch: float = 0.0
    forward_h_fov: float = math.radians(90.0)

    def __post_init__(self) -> None:
        if not math.isfinite(self.max_distance) or not 0 <= self.max_distance < math.pi:
            raise ValueError("max_distance must be finite and in [0, pi)")
        if self.grace_frames < 0:
            raise ValueError("grace_frames must be nonnegative")
        if not all(
            math.isfinite(value)
            for value in (self.forward_yaw, self.forward_pitch, self.forward_h_fov)
        ):
            raise ValueError("forward geometry must be finite")
        if not -math.pi / 2 <= self.forward_pitch <= math.pi / 2:
            raise ValueError("forward_pitch must remain between the poles")
        if not 0 < self.forward_h_fov < math.pi:
            raise ValueError("forward_h_fov must be between zero and pi")


class AssociationProvenance(str, Enum):
    """Strength of the evidence used to continue a temporal candidate."""

    TRACKER_IDENTITY = "tracker_identity"
    HUMAN_GEOMETRIC = "human_geometric"
    GEOMETRIC_ONLY = "geometric_only"
    SYNTHETIC_CONTEXT = "synthetic_context"

    @property
    def grants_editorial_persistence(self) -> bool:
        return self in {
            AssociationProvenance.TRACKER_IDENTITY,
            AssociationProvenance.HUMAN_GEOMETRIC,
        }


@dataclass(frozen=True)
class TemporalCandidate:
    candidate_id: str
    track_id: str | None
    yaw: float
    pitch: float
    h_fov: float
    candidate_type: str
    observed: bool
    observed_frames: int
    age_frames: int
    missing_frames: int
    source_candidate_id: str | None
    association_provenance: AssociationProvenance

    @property
    def editorial_persistence_valid(self) -> bool:
        return self.association_provenance.grants_editorial_persistence


@dataclass(frozen=True)
class CandidateFrame:
    timestamp: float
    frame_index: int
    candidates: tuple[TemporalCandidate, ...]


@dataclass
class _Track:
    track_id: str
    yaw: float
    pitch: float
    h_fov: float
    candidate_type: str
    first_frame: int
    last_frame: int
    observed_frames: int
    association_provenance: AssociationProvenance
    upstream_track_id: str | None
    missing_frames: int = 0


def _observation_key(candidate) -> tuple:
    # Geometry and a backend-issued ID are stable under input index reordering.
    return (
        candidate.candidate_type,
        round(candidate.yaw, 12),
        round(candidate.pitch, 12),
        round(candidate.h_fov, 12),
        candidate.candidate_id,
    )


def associate_candidate_sequence(
    results: Iterable[PerceptionResult],
    config: AssociationConfig = AssociationConfig(),
) -> tuple[CandidateFrame, ...]:
    """Associate spherical observations and add a forward/context fallback.

    Matching is a deterministic global greedy assignment over all valid
    track/observation pairs. Explicit upstream track IDs require exact matches;
    otherwise association is geometric and does not imply identity. Tracks
    survive ``grace_frames`` absent samples.
    A context candidate is present on every frame so downstream planning never
    receives an empty choice set.
    """

    ordered_results = tuple(results)
    previous_index = -1
    active: dict[str, _Track] = {}
    next_track = 1
    output: list[CandidateFrame] = []

    for sequence_index, result in enumerate(ordered_results):
        frame_index = result.sample.frame_index
        if frame_index <= previous_index:
            raise ValueError("frame indices must increase monotonically")
        previous_index = frame_index
        observations = tuple(sorted(result.candidates, key=_observation_key))

        pairs: list[tuple[float, str, tuple, int]] = []
        for index, observation in enumerate(observations):
            for track_id, track in active.items():
                if observation.track_id is not None:
                    if (
                        track.upstream_track_id == observation.track_id
                        and track.candidate_type == observation.candidate_type
                    ):
                        pairs.append((0.0, track_id, _observation_key(observation), index))
                    continue
                if track.upstream_track_id is not None:
                    continue
                if track.candidate_type != observation.candidate_type:
                    continue
                distance = spherical_distance(
                    (track.yaw, track.pitch), (observation.yaw, observation.pitch)
                )
                if distance <= config.max_distance:
                    pairs.append((distance, track_id, _observation_key(observation), index))
        pairs.sort()

        matched_tracks: set[str] = set()
        matched_observations: set[int] = set()
        assignments: dict[int, str] = {}
        for _, track_id, _, index in pairs:
            if track_id in matched_tracks or index in matched_observations:
                continue
            matched_tracks.add(track_id)
            matched_observations.add(index)
            assignments[index] = track_id

        for track_id in tuple(active):
            if track_id not in matched_tracks:
                active[track_id].missing_frames += 1
                if active[track_id].missing_frames > config.grace_frames:
                    del active[track_id]

        frame_candidates: list[TemporalCandidate] = []
        for index, observation in enumerate(observations):
            track_id = assignments.get(index)
            if track_id is None:
                track_id = f"track:{next_track:06d}"
                next_track += 1
                active[track_id] = _Track(
                    track_id,
                    observation.yaw,
                    observation.pitch,
                    observation.h_fov,
                    observation.candidate_type,
                    frame_index,
                    frame_index,
                    1,
                    (
                        AssociationProvenance.TRACKER_IDENTITY
                        if observation.track_id is not None
                        else AssociationProvenance.HUMAN_GEOMETRIC
                        if observation.candidate_type == "human"
                        else AssociationProvenance.GEOMETRIC_ONLY
                    ),
                    observation.track_id,
                )
            else:
                track = active[track_id]
                track.yaw = observation.yaw
                track.pitch = observation.pitch
                track.h_fov = observation.h_fov
                track.last_frame = frame_index
                track.observed_frames += 1
                track.missing_frames = 0
            track = active[track_id]
            frame_candidates.append(
                TemporalCandidate(
                    candidate_id=track_id,
                    track_id=track_id,
                    yaw=track.yaw,
                    pitch=track.pitch,
                    h_fov=track.h_fov,
                    candidate_type=track.candidate_type,
                    observed=True,
                    observed_frames=track.observed_frames,
                    age_frames=frame_index - track.first_frame + 1,
                    missing_frames=0,
                    source_candidate_id=observation.candidate_id,
                    association_provenance=track.association_provenance,
                )
            )

        # Keep grace candidates available for a continuity-aware planner.
        for track_id, track in sorted(active.items()):
            if track.missing_frames and track.missing_frames <= config.grace_frames:
                frame_candidates.append(
                    TemporalCandidate(
                        candidate_id=track_id,
                        track_id=track_id,
                        yaw=track.yaw,
                        pitch=track.pitch,
                        h_fov=track.h_fov,
                        candidate_type=track.candidate_type,
                        observed=False,
                        observed_frames=track.observed_frames,
                        age_frames=frame_index - track.first_frame + 1,
                        missing_frames=track.missing_frames,
                        source_candidate_id=None,
                        association_provenance=track.association_provenance,
                    )
                )

        frame_candidates.append(
            TemporalCandidate(
                candidate_id="context:forward",
                track_id=None,
                yaw=wrap_yaw(config.forward_yaw),
                pitch=config.forward_pitch,
                h_fov=config.forward_h_fov,
                candidate_type="context",
                observed=True,
                observed_frames=sequence_index + 1,
                age_frames=sequence_index + 1,
                missing_frames=0,
                source_candidate_id=None,
                association_provenance=AssociationProvenance.SYNTHETIC_CONTEXT,
            )
        )
        frame_candidates.sort(key=lambda item: item.candidate_id)
        output.append(
            CandidateFrame(result.sample.timestamp, frame_index, tuple(frame_candidates))
        )
    return tuple(output)
