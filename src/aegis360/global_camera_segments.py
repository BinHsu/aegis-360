"""Resolve selected global events to a complete geometry-owned segment plan."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid


def build_global_camera_segments(
    plan: Mapping[str, object], timeline: Mapping[str, object],
    grid: Mapping[str, object], *, plan_sha256: str, timeline_sha256: str,
    grid_sha256: str,
) -> dict[str, object]:
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None for value in (
        plan_sha256, timeline_sha256, grid_sha256,
    )):
        raise ValueError("global-camera-segment checksums are invalid")
    validate_context_view_grid(grid)
    if plan.get("schema_version") != "aegis360.global-event-plan.v1" or timeline.get("schema_version") != "aegis360.event-timeline.v1":
        raise ValueError("global-camera-segment inputs are invalid")
    if plan.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256 or plan.get("decisions") is None:
        raise ValueError("global-camera-segment grid lineage is invalid")
    if timeline.get("source_id") != grid["source_id"] or plan.get("decisions") is None:
        raise ValueError("global-camera-segment source is invalid")
    events = {event["event_id"]: event for event in timeline["events"]}
    decisions = plan["decisions"]
    if [item["event_id"] for item in decisions] != list(events):
        raise ValueError("global-camera-segment decisions must cover timeline events in order")
    candidates = {item["candidate_id"]: item for item in grid["candidates"]}
    overlays = []
    primary_ids = set()
    for decision in decisions:
        event = events[decision["event_id"]]
        context = event["view_context"]
        primary_ids.add(context["current_candidate_id"])
        selected = decision["selected_candidate_id"]
        if selected not in {context["current_candidate_id"], context["proposed_candidate_id"]}:
            raise ValueError("global-camera-segment selection is not declared")
        if selected == context["proposed_candidate_id"]:
            overlays.extend((interval["start_seconds"], interval["end_seconds"], selected, event["event_id"]) for interval in context["proposed_available_intervals"])
    if len(primary_ids) != 1:
        raise ValueError("global-camera-segment v1 requires one primary candidate")
    primary = next(iter(primary_ids))
    if primary not in candidates or any(candidate_id not in candidates for _, _, candidate_id, _ in overlays):
        raise ValueError("global-camera-segment candidate geometry is missing")
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    boundaries = sorted({window_start, window_end, *(value for row in overlays for value in row[:2])})
    segments = []
    for start, end in zip(boundaries, boundaries[1:]):
        matching = [row for row in overlays if row[0] <= start and end <= row[1]]
        if len(matching) > 1:
            raise ValueError("global-camera-segment overlays must not overlap")
        candidate_id = matching[0][2] if matching else primary
        event_id = matching[0][3] if matching else None
        if segments and segments[-1]["candidate_id"] == candidate_id:
            segments[-1]["end_seconds"] = float(end)
            if event_id is not None and event_id not in segments[-1]["event_ids"]:
                segments[-1]["event_ids"].append(event_id)
            continue
        geometry = candidates[candidate_id]
        segments.append({
            "start_seconds": float(start), "end_seconds": float(end),
            "candidate_id": candidate_id,
            "yaw_degrees": geometry["yaw_degrees"],
            "pitch_degrees": geometry["pitch_degrees"],
            "horizontal_fov_degrees": geometry["horizontal_fov_degrees"],
            "event_ids": [] if event_id is None else [event_id],
        })
    return {
        "schema_version": "aegis360.global-camera-segments.v1",
        "source_id": grid["source_id"], "window": dict(grid["window"]),
        "inputs": {"global_event_plan_sha256": plan_sha256,
                   "event_timeline_sha256": timeline_sha256,
                   "context_view_grid_sha256": grid_sha256},
        "segments": segments,
        "transition_policy": "hard_cut_at_declared_availability_boundary_v1",
        "limitations": [
            "v1 emits hard-cut static segments and not a continuous camera path",
            "selected proposed views are clipped to exact timeline availability",
        ],
    }
