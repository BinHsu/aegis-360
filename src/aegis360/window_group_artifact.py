"""Build a path-free window-group proposal from spherical people and faces."""

from __future__ import annotations

from dataclasses import asdict
import math
import re
from typing import Mapping

from .group_shot import (
    CompositionAnchor, GroupMember, apply_vertical_composition_anchors,
    apply_vertical_extent_midpoint,
    build_group_shots,
)
from .window_group import build_window_group_shot, window_group_scene_candidates


SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")


def build_window_group_proposal_artifact(
    spherical: Mapping[str, object],
    faces: Mapping[str, object],
    *,
    source_id: str,
    window_id: str,
    start_seconds: float,
    duration_seconds: float,
    minimum_observation_ratio: float = 0.5,
    maximum_face_pitch_correction_degrees: float = 5.0,
    use_vertical_bounds_midpoint: bool = False,
) -> dict[str, object]:
    """Aggregate simultaneous groups before any human/VLM context selection."""

    if not SAFE_ID.fullmatch(source_id) or not SAFE_ID.fullmatch(window_id):
        raise ValueError("source and window IDs must be privacy-safe")
    if (
        not math.isfinite(start_seconds) or start_seconds < 0
        or not math.isfinite(duration_seconds) or duration_seconds <= 0
    ):
        raise ValueError("window timing is invalid")
    if (
        not math.isfinite(maximum_face_pitch_correction_degrees)
        or not 0 <= maximum_face_pitch_correction_degrees <= 25
    ):
        raise ValueError("face pitch correction must be within [0, 25] degrees")
    if spherical.get("schema_version") not in {
        "aegis360.semantic-spherical-dedup.v1",
        "aegis360.semantic-spherical-dedup.v2",
    }:
        raise ValueError("unsupported spherical evidence schema")
    if faces.get("schemaVersion") != 1:
        raise ValueError("unsupported face evidence schema")
    samples = spherical.get("samples")
    face_frames = faces.get("frames")
    if not isinstance(samples, list) or not isinstance(face_frames, list):
        raise ValueError("proposal evidence arrays are missing")

    end_seconds = start_seconds + duration_seconds
    face_by_timestamp: dict[float, list[CompositionAnchor]] = {}
    for frame in face_frames:
        if not isinstance(frame, Mapping):
            raise ValueError("face frame must be an object")
        timestamp = frame.get("timestampSeconds")
        candidates = frame.get("candidates")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError("face timestamp is invalid")
        if not isinstance(candidates, list):
            raise ValueError("face candidates are missing")
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise ValueError("face candidate must be an object")
            if candidate.get("kind") != "face_rectangle":
                continue
            yaw, pitch = candidate.get("yawRadians"), candidate.get("pitchRadians")
            if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (yaw, pitch)):
                raise ValueError("face geometry is invalid")
            face_by_timestamp.setdefault(round(float(timestamp), 9), []).append(
                CompositionAnchor(float(yaw), float(pitch))
            )

    timestamps = []
    observed_shots = []
    for sample in samples:
        if not isinstance(sample, Mapping):
            raise ValueError("spherical sample must be an object")
        timestamp = sample.get("timestamp_seconds")
        if not isinstance(timestamp, (int, float)) or not math.isfinite(timestamp):
            raise ValueError("spherical timestamp is invalid")
        timestamp = float(timestamp)
        if not start_seconds <= timestamp < end_seconds:
            continue
        timestamps.append(timestamp)
        clusters = sample.get("clusters")
        if not isinstance(clusters, list):
            raise ValueError("spherical clusters are missing")
        members = []
        for cluster in clusters:
            if not isinstance(cluster, Mapping) or cluster.get("class_name") != "person":
                continue
            candidate_id = cluster.get("candidate_id")
            yaw = cluster.get("yaw_radians")
            pitch = cluster.get("pitch_radians")
            extent = cluster.get("horizontal_extent_radians")
            pitch_min = cluster.get("pitch_min_radians")
            pitch_max = cluster.get("pitch_max_radians")
            if (
                not isinstance(candidate_id, str) or not candidate_id
                or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in (yaw, pitch, extent))
            ):
                raise ValueError("person cluster geometry is invalid")
            members.append(GroupMember(
                candidate_id, float(yaw), float(pitch), float(extent),
                None if pitch_min is None else float(pitch_min),
                None if pitch_max is None else float(pitch_max),
            ))
        groups = build_group_shots(members)
        if groups:
            group = groups[0]
            observed_shots.append(
                apply_vertical_extent_midpoint(group)
                if use_vertical_bounds_midpoint and group.pitch_min is not None else
                apply_vertical_composition_anchors(
                    group, face_by_timestamp.get(round(timestamp, 9), []),
                    maximum_pitch_correction=math.radians(
                        maximum_face_pitch_correction_degrees
                    ),
                )
            )
    if not timestamps:
        raise ValueError("window contains no spherical samples")
    if len(timestamps) != len(set(timestamps)) or timestamps != sorted(timestamps):
        raise ValueError("window timestamps must be unique and ordered")
    shot = build_window_group_shot(
        observed_shots,
        total_sample_count=len(timestamps),
        minimum_observation_ratio=minimum_observation_ratio,
    )
    if shot is None:
        raise ValueError("window group observation floor was not met")
    candidates = window_group_scene_candidates(shot)
    return {
        "schema_version": "aegis360.window-group-proposal.v1",
        "window": {
            "source_id": source_id,
            "window_id": window_id,
            "start_seconds": start_seconds,
            "duration_seconds": duration_seconds,
            "sample_timestamps_seconds": timestamps,
        },
        "geometry": asdict(shot),
        "composition_policy": {
            "maximum_face_pitch_correction_degrees": maximum_face_pitch_correction_degrees,
            "status": (
                "experimental_complete_vertical_bounds_union_midpoint"
                if use_vertical_bounds_midpoint and all(item.pitch_min is not None for item in observed_shots)
                else "tunable_poc_guard_not_validated_default"
            ),
        },
        "candidates": [asdict(candidate) for candidate in candidates],
        "selection": {"context_required": True, "selected_candidate_id": None},
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_names": False, "contains_embeddings": False,
        },
        "limitations": [
            "proposal-local person slots express coverage, not identity",
            "geometry proposal does not establish conversation or active speaker",
        ],
    }
