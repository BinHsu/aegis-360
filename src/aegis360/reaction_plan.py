"""Bind reaction timing to declared editorial roles and visual availability."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

from .context_views import validate_context_view_grid
from .editorial_roles import validate_editorial_roles
from .live_scene import validate_live_scene_intervals
from .reaction_intervals import validate_reaction_intervals


def canonical_sha256(document: Mapping[str, object]) -> str:
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest()


def build_reaction_plan(
    grid: Mapping[str, object], roles: Mapping[str, object],
    reactions: Mapping[str, object], availability: Mapping[str, object],
    *, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    validate_editorial_roles(roles, grid, grid_sha256=grid_sha256)
    validate_reaction_intervals(reactions)
    validate_live_scene_intervals(availability)
    source_id = grid["source_id"]
    if any(item["source_id"] != source_id for item in (roles, reactions, availability)):
        raise ValueError("reaction-plan sources must match")
    assignments = {item["role"]: item["candidate_id"] for item in roles["assignments"]}
    primary = assignments["primary_performance"]
    reaction = assignments["audience_reaction"]
    start = grid["window"]["start_seconds"]
    end = start + grid["window"]["duration_seconds"]
    reaction_ranges = []
    for event in reactions["intervals"]:
        for visible in availability["intervals"]:
            overlap_start = max(start, event["start_seconds"], visible["start_seconds"])
            overlap_end = min(end, event["end_seconds"], visible["end_seconds"])
            if overlap_end > overlap_start:
                reaction_ranges.append((overlap_start, overlap_end))
    segments = []
    cursor = start
    for overlap_start, overlap_end in reaction_ranges:
        if overlap_start > cursor:
            segments.append({"start_seconds": cursor, "end_seconds": overlap_start,
                             "candidate_id": primary, "reason": "primary_performance_default"})
        segments.append({"start_seconds": overlap_start, "end_seconds": overlap_end,
                         "candidate_id": reaction, "reason": "reaction_event_and_live_scene"})
        cursor = overlap_end
    if cursor < end:
        segments.append({"start_seconds": cursor, "end_seconds": end,
                         "candidate_id": primary, "reason": "primary_performance_default"})
    return {
        "schema_version": "aegis360.reaction-shot-plan.v1",
        "source_id": source_id,
        "window": dict(grid["window"]),
        "inputs": {
            "context_view_grid_sha256": grid_sha256,
            "editorial_roles_sha256": canonical_sha256(roles),
            "reaction_intervals_sha256": canonical_sha256(reactions),
            "live_scene_intervals_sha256": canonical_sha256(availability),
        },
        "segments": segments,
        "transition_policy": "hard_cut_between_role_changes_v1",
        "limitations": [
            "the plan tests an owner-stated directing rule on one performance",
            "audio thresholds and role assignments are not generic accuracy evidence",
        ],
    }


def validate_reaction_plan(document: Mapping[str, object], grid: Mapping[str, object], *, grid_sha256: str) -> None:
    validate_context_view_grid(grid)
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "inputs", "segments",
        "transition_policy", "limitations",
    } or document["schema_version"] != "aegis360.reaction-shot-plan.v1":
        raise ValueError("reaction-shot plan fields or schema are invalid")
    if document["source_id"] != grid["source_id"] or document["window"] != grid["window"]:
        raise ValueError("reaction-shot plan window must match its grid")
    if document["inputs"].get("context_view_grid_sha256") != grid_sha256:
        raise ValueError("reaction-shot plan grid checksum mismatch")
    candidates = {item["candidate_id"] for item in grid["candidates"]}
    cursor = grid["window"]["start_seconds"]
    end = cursor + grid["window"]["duration_seconds"]
    for segment in document["segments"]:
        if not isinstance(segment, Mapping) or set(segment) != {
            "start_seconds", "end_seconds", "candidate_id", "reason",
        } or segment["start_seconds"] != cursor or segment["end_seconds"] <= cursor or segment["candidate_id"] not in candidates:
            raise ValueError("reaction-shot segments must form a contiguous declared path")
        cursor = segment["end_seconds"]
    if cursor != end:
        raise ValueError("reaction-shot segments must cover the complete grid window")
