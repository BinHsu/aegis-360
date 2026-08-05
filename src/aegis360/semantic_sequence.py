"""Combine bounded semantic lifecycles into one planner candidate timeline."""

from __future__ import annotations

from collections import defaultdict
import math
from typing import Iterable, Mapping

from .candidate_sequence import (
    AssociationProvenance,
    CandidateFrame,
    TemporalCandidate,
)
from .geometry import wrap_yaw
from .lifecycle_candidates import lifecycle_candidate_frames


def merge_lifecycle_candidate_sequences(
    sequences: Iterable[tuple],
    *,
    horizontal_fov: float,
    forward_yaw: float = 0.0,
    forward_pitch: float = 0.0,
) -> tuple[CandidateFrame, ...]:
    """Merge independently bounded lifecycles without manufacturing identity.

    Each input sequence retains its lifecycle-issued candidate ID. Forward
    context is rebuilt once per merged timestamp, so overlapping tracks do not
    create duplicate fallbacks. A terminated lifecycle contributes no later
    subject candidate through the existing fail-closed adapter.
    """

    if (
        not math.isfinite(horizontal_fov)
        or not 0 < horizontal_fov < math.pi
        or not math.isfinite(forward_yaw)
        or not math.isfinite(forward_pitch)
        or not -math.pi / 2 <= forward_pitch <= math.pi / 2
    ):
        raise ValueError("merged sequence geometry is invalid")

    by_timestamp: dict[float, list[TemporalCandidate]] = defaultdict(list)
    seen_ids: set[str] = set()
    sequence_count = 0
    for sequence in sequences:
        if len(sequence) not in (3, 4):
            raise ValueError("lifecycle sequence must contain three or four fields")
        lifecycle, tracking, candidate_type = sequence[:3]
        candidate_horizontal_fov = sequence[3] if len(sequence) == 4 else None
        if not isinstance(candidate_type, str) or not candidate_type.strip():
            raise ValueError("candidate type is required")
        track_id = lifecycle.get("track_id")
        if not isinstance(track_id, str) or not track_id or track_id in seen_ids:
            raise ValueError("lifecycle track IDs must be unique")
        seen_ids.add(track_id)
        sequence_count += 1
        frames = lifecycle_candidate_frames(
            lifecycle,
            tracking,
            horizontal_fov=horizontal_fov,
            candidate_horizontal_fov=candidate_horizontal_fov,
            candidate_type=candidate_type,
            forward_yaw=forward_yaw,
            forward_pitch=forward_pitch,
        )
        for frame in frames:
            by_timestamp[frame.timestamp].extend(
                candidate
                for candidate in frame.candidates
                if candidate.candidate_id != "context:forward"
            )

    if sequence_count == 0 or not by_timestamp:
        raise ValueError("at least one lifecycle sequence is required")

    output = []
    for frame_index, timestamp in enumerate(sorted(by_timestamp)):
        candidates = by_timestamp[timestamp]
        candidate_ids = [candidate.candidate_id for candidate in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("merged timestamp contains duplicate candidate IDs")
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
    return tuple(output)
