"""Aggregate observed group geometry under an explicit window context."""

from __future__ import annotations

from dataclasses import dataclass
import math
import statistics

from .candidate_sequence import AssociationProvenance, CandidateFrame, TemporalCandidate
from .geometry import wrap_yaw
from .group_shot import GroupShot
from .scene_context import SceneContextCandidate, SceneContextDecision


@dataclass(frozen=True)
class WindowGroupShot:
    yaw: float
    pitch: float
    horizontal_fov: float
    required_horizontal_fov: float
    observed_sample_count: int
    total_sample_count: int
    observation_ratio: float
    minimum_observed_member_count: int
    maximum_observed_member_count: int
    fully_contains_observed_groups: bool
    association_provenance: str = "simultaneous_group_geometry_nonidentity"
    discarded_observed_sample_count: int = 0


def window_group_scene_candidates(
    shot: WindowGroupShot,
    *,
    group_candidate_id: str = "group:window:1",
) -> tuple[SceneContextCandidate, ...]:
    """Declare nonidentity member slots and one geometry-owned group proposal."""

    if shot.minimum_observed_member_count < 2:
        raise ValueError("window group requires at least two observed members")
    members = tuple(
        SceneContextCandidate(f"person-slot:{index + 1}", "person", ())
        for index in range(shot.minimum_observed_member_count)
    )
    return members + (
        SceneContextCandidate(
            group_candidate_id, "group",
            tuple(candidate.candidate_id for candidate in members),
        ),
        SceneContextCandidate("context:forward", "context", ()),
    )


def window_group_candidate_frames(
    context: SceneContextDecision,
    shot: WindowGroupShot,
    timestamps: list[float],
    *,
    forward_yaw: float = 0.0,
    forward_pitch: float = 0.0,
    forward_horizontal_fov: float = math.radians(110),
) -> tuple[CandidateFrame, ...]:
    """Expose a selected group plus fallback, or fallback alone on abstention."""

    selected = next(
        (
            candidate for candidate in context.candidates
            if candidate.candidate_id == context.selected_candidate_id
        ),
        None,
    )
    abstained = context.subject_scope == "uncertain" and selected is None
    selected_group = (
        context.subject_scope == "group" and selected is not None
        and selected.candidate_type == "group"
        and len(selected.member_candidate_ids) >= 2
    )
    if not abstained and not selected_group:
        raise ValueError("window candidate requires a selected group proposal")
    if len(timestamps) != shot.total_sample_count:
        raise ValueError("timestamps must cover the complete context window")
    if (
        not math.isfinite(forward_yaw) or not math.isfinite(forward_pitch)
        or not math.isfinite(forward_horizontal_fov)
        or not -math.pi / 2 <= forward_pitch <= math.pi / 2
        or not 0 < forward_horizontal_fov < math.pi
    ):
        raise ValueError("forward geometry is invalid")
    frames = []
    previous = -math.inf
    for index, timestamp in enumerate(timestamps):
        if not math.isfinite(timestamp) or timestamp <= previous:
            raise ValueError("timestamps must be finite and strictly increasing")
        candidates = []
        if selected_group:
            candidates.append(TemporalCandidate(
                candidate_id=selected.candidate_id,
                track_id=None,
                yaw=shot.yaw,
                pitch=shot.pitch,
                h_fov=shot.required_horizontal_fov,
                candidate_type="group_context",
                observed=True,
                observed_frames=index + 1,
                age_frames=index + 1,
                missing_frames=0,
                source_candidate_id=None,
                association_provenance=AssociationProvenance.GEOMETRIC_ONLY,
                covered_candidate_ids=selected.member_candidate_ids,
            ))
        if abstained:
            candidates.append(TemporalCandidate(
                candidate_id="context:forward",
                track_id=None,
                yaw=wrap_yaw(forward_yaw),
                pitch=forward_pitch,
                h_fov=forward_horizontal_fov,
                candidate_type="context",
                observed=True,
                observed_frames=index + 1,
                age_frames=index + 1,
                missing_frames=0,
                source_candidate_id=None,
                association_provenance=AssociationProvenance.SYNTHETIC_CONTEXT,
            ))
        frames.append(CandidateFrame(timestamp, index, tuple(candidates)))
        previous = timestamp
    return tuple(frames)


def build_window_group_shot(
    observed_shots: list[GroupShot],
    *,
    total_sample_count: int,
    minimum_observation_ratio: float = 0.5,
    maximum_horizontal_fov: float = math.radians(110),
) -> WindowGroupShot | None:
    """Hold a group pose across bounded misses without merging identities."""

    if not isinstance(total_sample_count, int) or isinstance(total_sample_count, bool) or total_sample_count < 1:
        raise ValueError("total sample count must be a positive integer")
    if len(observed_shots) > total_sample_count:
        raise ValueError("observed shots cannot exceed total samples")
    if (
        not math.isfinite(minimum_observation_ratio)
        or not 0 < minimum_observation_ratio <= 1
        or not math.isfinite(maximum_horizontal_fov)
        or not 0 < maximum_horizontal_fov < math.pi
    ):
        raise ValueError("window group bounds are invalid")
    if not observed_shots:
        return None
    for shot in observed_shots:
        if len(shot.member_ids) < 2:
            raise ValueError("each observation must be a group shot")

    minimum_count = math.ceil(minimum_observation_ratio * total_sample_count)
    if len(observed_shots) < minimum_count:
        return None
    retained = list(observed_shots)
    discarded = 0
    while True:
        x = statistics.median(math.sin(shot.yaw) for shot in retained)
        z = statistics.median(math.cos(shot.yaw) for shot in retained)
        if math.hypot(x, z) <= 1e-9:
            return None
        yaw = wrap_yaw(math.atan2(x, z))
        contributions = [
            2 * abs(wrap_yaw(shot.yaw - yaw)) + shot.required_horizontal_fov
            for shot in retained
        ]
        required = max(contributions)
        if required <= maximum_horizontal_fov:
            break
        if len(retained) <= minimum_count:
            return None
        worst = max(
            range(len(retained)),
            key=lambda index: (contributions[index], retained[index].member_ids),
        )
        del retained[worst]
        discarded += 1
    pitch = statistics.median(shot.pitch for shot in retained)
    ratio = len(retained) / total_sample_count
    horizontal_fov = min(
        maximum_horizontal_fov,
        max(max(shot.horizontal_fov for shot in retained), required),
    )
    return WindowGroupShot(
        yaw=yaw,
        pitch=pitch,
        horizontal_fov=horizontal_fov,
        required_horizontal_fov=required,
        observed_sample_count=len(retained),
        total_sample_count=total_sample_count,
        observation_ratio=ratio,
        minimum_observed_member_count=min(len(shot.member_ids) for shot in retained),
        maximum_observed_member_count=max(len(shot.member_ids) for shot in retained),
        fully_contains_observed_groups=True,
        discarded_observed_sample_count=discarded,
    )
