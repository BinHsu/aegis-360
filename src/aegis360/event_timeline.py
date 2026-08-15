"""Closed sparse event timeline derived from immutable low-cost evidence."""

from __future__ import annotations

import re
from typing import Mapping

from .candidate_availability import validate_candidate_availability
from .context_views import validate_context_view_grid
from .editorial_roles import validate_editorial_roles
from .reaction_intervals import validate_reaction_intervals


SCHEMA = "aegis360.event-timeline.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
INPUT_KEYS = {
    "context_view_grid_sha256", "editorial_roles_sha256",
    "reaction_intervals_sha256", "candidate_availability_sha256",
}


def build_event_timeline(
    grid: Mapping[str, object], roles: Mapping[str, object],
    reactions: Mapping[str, object], availability: Mapping[str, object], *,
    grid_sha256: str, roles_sha256: str, reactions_sha256: str,
    availability_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    validate_editorial_roles(roles, grid, grid_sha256=grid_sha256)
    validate_reaction_intervals(reactions)
    validate_candidate_availability(availability, grid, grid_sha256=grid_sha256)
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None for value in (
        grid_sha256, roles_sha256, reactions_sha256, availability_sha256,
    )):
        raise ValueError("event-timeline checksums are invalid")
    source_id = grid["source_id"]
    if any(item["source_id"] != source_id for item in (roles, reactions, availability)):
        raise ValueError("event-timeline sources must match")
    assignments = {item["role"]: item["candidate_id"] for item in roles["assignments"]}
    current = assignments["primary_performance"]
    proposed = assignments["audience_reaction"]
    available = next((item["intervals"] for item in availability["candidates"]
                      if item["candidate_id"] == proposed), [])
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    events = []
    for reaction in reactions["intervals"]:
        start = max(window_start, reaction["start_seconds"])
        end = min(window_end, reaction["end_seconds"])
        if end <= start:
            continue
        overlaps = [{
            "start_seconds": max(start, interval["start_seconds"]),
            "end_seconds": min(end, interval["end_seconds"]),
        } for interval in available if min(end, interval["end_seconds"]) >
        max(start, interval["start_seconds"])]
        onset_available = any(
            interval["start_seconds"] <= reaction["start_seconds"] < interval["end_seconds"]
            for interval in available
        )
        events.append({
            "event_id": f"event:reaction:{len(events):04d}",
            "event_type": "reaction_candidate",
            "start_seconds": float(start),
            "end_seconds": float(end),
            "audio_evidence": {
                "source_event_start_seconds": float(reaction["start_seconds"]),
                "source_event_end_seconds": float(reaction["end_seconds"]),
                "supporting_window_count": reaction["supporting_window_count"],
                "peak_applause_confidence": reaction["peak_applause_confidence"],
                "peak_clapping_confidence": reaction["peak_clapping_confidence"],
            },
            "view_context": {
                "current_candidate_id": current,
                "proposed_candidate_id": proposed,
                "proposed_available_at_event_onset": onset_available,
                "proposed_available_intervals": overlaps,
            },
        })
    return {
        "schema_version": SCHEMA,
        "source_id": source_id,
        "window": dict(grid["window"]),
        "inputs": {
            "context_view_grid_sha256": grid_sha256,
            "editorial_roles_sha256": roles_sha256,
            "reaction_intervals_sha256": reactions_sha256,
            "candidate_availability_sha256": availability_sha256,
        },
        "events": events,
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_audio": False, "contains_names": False,
            "contains_identity": False, "contains_editorial_decision": False,
        },
        "limitations": [
            "v1 normalizes reaction candidates only and is not a complete story model",
            "event evidence does not authorize a cut or establish reaction source identity",
        ],
    }


def validate_event_timeline(
    document: Mapping[str, object], grid: Mapping[str, object],
    roles: Mapping[str, object], reactions: Mapping[str, object],
    availability: Mapping[str, object], *, grid_sha256: str,
    roles_sha256: str, reactions_sha256: str, availability_sha256: str,
) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "inputs", "events",
        "privacy", "limitations",
    } or document["schema_version"] != SCHEMA:
        raise ValueError("event-timeline fields or schema are invalid")
    if not isinstance(document["inputs"], Mapping) or set(document["inputs"]) != INPUT_KEYS:
        raise ValueError("event-timeline inputs are invalid")
    expected = build_event_timeline(
        grid, roles, reactions, availability, grid_sha256=grid_sha256,
        roles_sha256=roles_sha256, reactions_sha256=reactions_sha256,
        availability_sha256=availability_sha256,
    )
    if document != expected:
        raise ValueError("event timeline must exactly derive from immutable evidence")
