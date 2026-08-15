"""Pixel-free sparse semantic review requests for one timeline event."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid
from .event_timeline import SCHEMA as EVENT_TIMELINE_SCHEMA


SCHEMA = "aegis360.event-review-packet.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
TEMPORAL_ROLES = ("before", "event_early", "event_mid", "event_late", "after")


def _candidate_ids_at(event: Mapping[str, object], timestamp: float) -> list[str]:
    context = event["view_context"]
    candidate_ids = [context["current_candidate_id"]]
    if any(
        interval["start_seconds"] <= timestamp < interval["end_seconds"]
        for interval in context["proposed_available_intervals"]
    ):
        candidate_ids.append(context["proposed_candidate_id"])
    return candidate_ids


def build_event_review_packet(
    timeline: Mapping[str, object], grid: Mapping[str, object], *,
    event_id: str, timeline_sha256: str, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if not isinstance(timeline, Mapping) or set(timeline) != {
        "schema_version", "source_id", "window", "inputs", "events",
        "privacy", "limitations",
    } or timeline["schema_version"] != EVENT_TIMELINE_SCHEMA:
        raise ValueError("event-review timeline is invalid")
    if any(
        not isinstance(value, str) or SHA256.fullmatch(value) is None
        for value in (timeline_sha256, grid_sha256)
    ):
        raise ValueError("event-review checksums are invalid")
    if timeline.get("source_id") != grid["source_id"]:
        raise ValueError("event-review sources must match")
    if timeline.get("window") != grid["window"]:
        raise ValueError("event-review windows must match")
    if timeline.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256:
        raise ValueError("event-review grid checksum must match timeline lineage")
    events = [event for event in timeline.get("events", []) if event.get("event_id") == event_id]
    if len(events) != 1:
        raise ValueError("event-review requires one declared event")
    event = events[0]
    if not isinstance(event, Mapping) or set(event) != {
        "event_id", "event_type", "start_seconds", "end_seconds",
        "audio_evidence", "view_context",
    }:
        raise ValueError("event-review event is invalid")
    declared_ids = {candidate["candidate_id"] for candidate in grid["candidates"]}
    context = event["view_context"]
    if {context["current_candidate_id"], context["proposed_candidate_id"]} - declared_ids:
        raise ValueError("event-review candidates must exist in the grid")

    start = event["start_seconds"]
    end = event["end_seconds"]
    duration = end - start
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    timestamps = (
        max(window_start, start - 2.0) if start > window_start else None,
        start + duration * 0.25,
        start + duration * 0.5,
        start + duration * 0.75,
        min(window_end, end + 2.0) if end < window_end else None,
    )
    samples = []
    for index, (role, timestamp) in enumerate(zip(TEMPORAL_ROLES, timestamps)):
        samples.append({
            "sample_id": f"sample:{index:02d}",
            "temporal_role": role,
            "timestamp_seconds": None if timestamp is None else float(timestamp),
            "candidate_ids": [] if timestamp is None else _candidate_ids_at(event, timestamp),
        })

    return {
        "schema_version": SCHEMA,
        "source_id": timeline["source_id"],
        "event_id": event_id,
        "inputs": {
            "event_timeline_sha256": timeline_sha256,
            "context_view_grid_sha256": grid_sha256,
        },
        "event_evidence": {
            "event_type": event["event_type"],
            "start_seconds": float(start),
            "end_seconds": float(end),
            "audio_evidence": dict(event["audio_evidence"]),
            "current_candidate_id": context["current_candidate_id"],
            "proposed_candidate_id": context["proposed_candidate_id"],
        },
        "sampling_policy": {
            "policy_id": "bounded_before_quartiles_after_v1",
            "context_offset_seconds": 2.0,
            "missing_boundary_context": "null_timestamp_and_empty_candidates",
        },
        "samples": samples,
        "temporary_media_policy": {
            "durable_pixels_allowed": False,
            "render_only_declared_candidates": True,
            "delete_after_adapter_completion": True,
        },
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_audio": False, "contains_names": False,
            "contains_identity": False, "contains_editorial_decision": False,
        },
        "limitations": [
            "the packet schedules sparse review but contains no rendered media",
            "semantic evidence may abstain and cannot create geometry, identity or candidates",
        ],
    }


def validate_event_review_packet(
    document: Mapping[str, object], timeline: Mapping[str, object],
    grid: Mapping[str, object], *, timeline_sha256: str, grid_sha256: str,
) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "event_id", "inputs", "event_evidence",
        "sampling_policy", "samples", "temporary_media_policy", "privacy",
        "limitations",
    } or document["schema_version"] != SCHEMA:
        raise ValueError("event-review fields or schema are invalid")
    expected = build_event_review_packet(
        timeline, grid, event_id=document["event_id"],
        timeline_sha256=timeline_sha256, grid_sha256=grid_sha256,
    )
    if document != expected:
        raise ValueError("event-review packet must exactly derive from timeline and grid")
