"""Bind reaction timing to declared editorial roles and visual availability."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

from .candidate_availability import validate_candidate_availability
from .context_views import validate_context_view_grid
from .editorial_roles import validate_editorial_roles
from .reaction_intervals import validate_reaction_intervals
from .reaction_view_gain import validate_reaction_view_gain


LEGACY_INPUT_KEYS = {
    "context_view_grid_sha256", "editorial_roles_sha256",
    "reaction_intervals_sha256", "live_scene_intervals_sha256",
}
INPUT_KEYS = {
    "context_view_grid_sha256", "editorial_roles_sha256",
    "reaction_intervals_sha256", "candidate_availability_sha256",
}
V4_INPUT_KEYS = INPUT_KEYS | {"reaction_view_gain_sha256"}
SHA256 = re.compile(r"[0-9a-f]{64}")


def canonical_sha256(document: Mapping[str, object]) -> str:
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest()


def build_reaction_plan(
    grid: Mapping[str, object], roles: Mapping[str, object],
    reactions: Mapping[str, object], availability: Mapping[str, object],
    gain: Mapping[str, object],
    *, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    validate_editorial_roles(roles, grid, grid_sha256=grid_sha256)
    validate_reaction_intervals(reactions)
    validate_candidate_availability(availability, grid, grid_sha256=grid_sha256)
    validate_reaction_view_gain(
        gain, grid, roles, reactions, grid_sha256=grid_sha256,
        roles_sha256=canonical_sha256(roles),
        reactions_sha256=canonical_sha256(reactions),
    )
    source_id = grid["source_id"]
    if any(item["source_id"] != source_id for item in (roles, reactions, availability, gain)):
        raise ValueError("reaction-plan sources must match")
    assignments = {item["role"]: item["candidate_id"] for item in roles["assignments"]}
    primary = assignments["primary_performance"]
    reaction = assignments["audience_reaction"]
    start = grid["window"]["start_seconds"]
    end = start + grid["window"]["duration_seconds"]
    visible_ranges = next((item["intervals"] for item in availability["candidates"]
                           if item["candidate_id"] == reaction), [])
    gain_by_event = {
        (item["reaction_start_seconds"], item["reaction_end_seconds"]): item["decision"]
        for item in gain["decisions"]
    }
    reaction_ranges = []
    for event in reactions["intervals"]:
        if gain_by_event.get((event["start_seconds"], event["end_seconds"]), "abstain") != "promote":
            continue
        for visible in visible_ranges:
            if not visible["start_seconds"] <= event["start_seconds"] < visible["end_seconds"]:
                continue
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
                         "candidate_id": reaction,
                         "reason": "reaction_event_candidate_available_and_gain_promoted"})
        cursor = overlap_end
    if cursor < end:
        segments.append({"start_seconds": cursor, "end_seconds": end,
                         "candidate_id": primary, "reason": "primary_performance_default"})
    return {
        "schema_version": "aegis360.reaction-shot-plan.v4",
        "source_id": source_id,
        "window": dict(grid["window"]),
        "inputs": {
            "context_view_grid_sha256": grid_sha256,
            "editorial_roles_sha256": canonical_sha256(roles),
            "reaction_intervals_sha256": canonical_sha256(reactions),
            "candidate_availability_sha256": canonical_sha256(availability),
            "reaction_view_gain_sha256": canonical_sha256(gain),
        },
        "segments": segments,
        "transition_policy": "hard_cut_only_when_candidate_available_and_gain_promoted_v4",
        "limitations": [
            "the plan tests an owner-stated directing rule on one performance",
            "audio thresholds and role assignments are not generic accuracy evidence",
        ],
    }


def validate_reaction_plan(
    document: Mapping[str, object], grid: Mapping[str, object], *, grid_sha256: str,
    roles: Mapping[str, object] | None = None,
    reactions: Mapping[str, object] | None = None,
    availability: Mapping[str, object] | None = None,
    gain: Mapping[str, object] | None = None,
) -> None:
    validate_context_view_grid(grid)
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "inputs", "segments",
        "transition_policy", "limitations",
    } or document["schema_version"] not in {
        "aegis360.reaction-shot-plan.v1", "aegis360.reaction-shot-plan.v2",
        "aegis360.reaction-shot-plan.v3",
        "aegis360.reaction-shot-plan.v4",
    }:
        raise ValueError("reaction-shot plan fields or schema are invalid")
    if document["source_id"] != grid["source_id"] or document["window"] != grid["window"]:
        raise ValueError("reaction-shot plan window must match its grid")
    expected_transition = {
        "aegis360.reaction-shot-plan.v1": "hard_cut_between_role_changes_v1",
        "aegis360.reaction-shot-plan.v2": "hard_cut_only_when_reaction_onset_is_live_v2",
        "aegis360.reaction-shot-plan.v3": "hard_cut_only_when_reaction_candidate_is_available_v3",
        "aegis360.reaction-shot-plan.v4": "hard_cut_only_when_candidate_available_and_gain_promoted_v4",
    }[document["schema_version"]]
    if document["transition_policy"] != expected_transition:
        raise ValueError("reaction-shot transition policy conflicts with schema")
    inputs = document["inputs"]
    expected_input_keys = (
        V4_INPUT_KEYS if document["schema_version"].endswith(".v4") else
        INPUT_KEYS if document["schema_version"].endswith(".v3") else
        LEGACY_INPUT_KEYS
    )
    if not isinstance(inputs, Mapping) or set(inputs) != expected_input_keys or any(
        not isinstance(value, str) or SHA256.fullmatch(value) is None
        for value in inputs.values()
    ):
        raise ValueError("reaction-shot plan inputs must be closed SHA-256 bindings")
    if inputs["context_view_grid_sha256"] != grid_sha256:
        raise ValueError("reaction-shot plan grid checksum mismatch")
    supplied = (roles, reactions, availability, gain)
    if any(item is not None for item in supplied) and not all(item is not None for item in supplied):
        raise ValueError("all reaction-shot evidence artifacts must be supplied together")
    if all(item is not None for item in supplied):
        if document["schema_version"] != "aegis360.reaction-shot-plan.v4":
            raise ValueError("raw evidence verification requires reaction-shot plan v4")
        assert roles is not None and reactions is not None and availability is not None and gain is not None
        validate_editorial_roles(roles, grid, grid_sha256=grid_sha256)
        validate_reaction_intervals(reactions)
        validate_candidate_availability(availability, grid, grid_sha256=grid_sha256)
        validate_reaction_view_gain(
            gain, grid, roles, reactions, grid_sha256=grid_sha256,
            roles_sha256=canonical_sha256(roles),
            reactions_sha256=canonical_sha256(reactions),
        )
        if any(item["source_id"] != grid["source_id"] for item in supplied):
            raise ValueError("reaction-plan sources must match")
        expected = {
            "editorial_roles_sha256": canonical_sha256(roles),
            "reaction_intervals_sha256": canonical_sha256(reactions),
            "candidate_availability_sha256": canonical_sha256(availability),
            "reaction_view_gain_sha256": canonical_sha256(gain),
        }
        if any(inputs[key] != value for key, value in expected.items()):
            raise ValueError("reaction-shot plan evidence checksum mismatch")
        rebuilt = build_reaction_plan(
            grid, roles, reactions, availability, gain, grid_sha256=grid_sha256,
        )
        if document != rebuilt:
            raise ValueError("reaction-shot plan must exactly derive from its evidence")
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
