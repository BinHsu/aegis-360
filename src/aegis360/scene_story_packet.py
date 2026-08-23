"""Bounded local-story context for one neutral scene event."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.scene-story-review-packet.v1"


def _unique_anchors(values: list[tuple[str, float]]) -> list[dict[str, object]]:
    result = []
    seen = set()
    for role, timestamp in values:
        rounded = round(timestamp, 6)
        if rounded in seen:
            continue
        seen.add(rounded)
        result.append({"sample_id": f"sample:{len(result):02d}",
                       "temporal_role": role,
                       "timestamp_seconds": float(rounded)})
    return result


def build_scene_story_packet(
    timeline: Mapping[str, object], grid: Mapping[str, object], *,
    event_id: str, timeline_sha256: str, grid_sha256: str,
    far_context_seconds: float = 15.0, near_context_seconds: float = 3.0,
    boundary_offset_seconds: float = 0.25,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None
           for value in (timeline_sha256, grid_sha256)):
        raise ValueError("scene-story checksums are invalid")
    if (timeline.get("schema_version") != "aegis360.event-timeline.v2"
            or timeline.get("source_id") != grid["source_id"]
            or timeline.get("window") != grid["window"]
            or timeline.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256):
        raise ValueError("scene-story lineage is invalid")
    if not (0 < boundary_offset_seconds < near_context_seconds < far_context_seconds <= 30):
        raise ValueError("scene-story context policy is invalid")
    matches = [(index, event) for index, event in enumerate(timeline["events"])
               if event["event_id"] == event_id]
    if len(matches) != 1:
        raise ValueError("scene-story packet requires one declared event")
    index, event = matches[0]
    if event["review_scope"].get("mode") != "all_declared_candidates":
        raise ValueError("scene-story packet requires a neutral scene event")
    declared_ids = [candidate["candidate_id"] for candidate in grid["candidates"]]
    if event["review_scope"].get("candidate_ids") != declared_ids:
        raise ValueError("scene-story scope must preserve declared grid order")
    scene_times = [signal["evidence"]["timestamp_seconds"]
                   for signal in event["signals"]
                   if signal["signal_type"] == "scene_change"]
    if not scene_times:
        raise ValueError("scene-story event has no scene boundary")
    first, last = min(scene_times), max(scene_times)
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    clamp = lambda value: max(window_start, min(window_end, value))
    samples = _unique_anchors([
        ("far_before", clamp(first - far_context_seconds)),
        ("near_before", clamp(first - near_context_seconds)),
        ("boundary_before", clamp(first - boundary_offset_seconds)),
        ("boundary_after", clamp(last + boundary_offset_seconds)),
        ("near_after", clamp(last + near_context_seconds)),
        ("far_after", clamp(last + far_context_seconds)),
    ])
    if not 2 <= len(samples) <= 6:
        raise ValueError("scene-story sample count is outside the bound")
    for sample in samples:
        sample["representation"] = "four_cardinal_contact_sheet"
        sample["candidate_ids"] = declared_ids
    center = (first + last) / 2
    duration = grid["window"]["duration_seconds"]
    neighbors = []
    for relation, neighbor_index in (("previous", index - 1), ("next", index + 1)):
        if 0 <= neighbor_index < len(timeline["events"]):
            neighbor = timeline["events"][neighbor_index]
            neighbors.append({"relation": relation, "event_id": neighbor["event_id"],
                              "start_seconds": neighbor["start_seconds"],
                              "end_seconds": neighbor["end_seconds"],
                              "signal_types": sorted({item["signal_type"]
                                                      for item in neighbor["signals"]})})
    return {
        "schema_version": SCHEMA, "source_id": timeline["source_id"],
        "event_id": event_id,
        "inputs": {"event_timeline_sha256": timeline_sha256,
                   "context_view_grid_sha256": grid_sha256},
        "event": {"start_seconds": event["start_seconds"],
                  "end_seconds": event["end_seconds"],
                  "boundary_timestamps_seconds": scene_times,
                  "signals": event["signals"]},
        "whole_video_context": {
            "window_start_seconds": window_start, "window_end_seconds": window_end,
            "event_position_fraction": (center - window_start) / duration,
            "event_index": index, "event_count": len(timeline["events"]),
            "neighbors": neighbors,
        },
        "sampling_policy": {
            "policy_id": "local_story_six_anchor_cardinal_composite_v1",
            "far_context_seconds": float(far_context_seconds),
            "near_context_seconds": float(near_context_seconds),
            "boundary_offset_seconds": float(boundary_offset_seconds),
            "maximum_composite_frames": 6, "maximum_source_viewports": 24,
        },
        "samples": samples,
        "temporary_media_policy": {"durable_pixels_allowed": False,
                                   "render_only_declared_candidates": True,
                                   "delete_after_adapter_completion": True},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False, "contains_editorial_decision": False},
        "limitations": [
            "local context classifies event role but does not determine the whole story",
            "the global planner must compare every event in chronology",
            "cardinal contact sheets establish coverage but do not select a view",
        ],
    }


def validate_scene_story_packet(
    document: Mapping[str, object], timeline: Mapping[str, object],
    grid: Mapping[str, object], *, timeline_sha256: str, grid_sha256: str,
) -> None:
    policy = document.get("sampling_policy", {})
    expected = build_scene_story_packet(
        timeline, grid, event_id=document.get("event_id", ""),
        timeline_sha256=timeline_sha256, grid_sha256=grid_sha256,
        far_context_seconds=policy.get("far_context_seconds", -1),
        near_context_seconds=policy.get("near_context_seconds", -1),
        boundary_offset_seconds=policy.get("boundary_offset_seconds", -1),
    )
    if document != expected:
        raise ValueError("scene-story packet must exactly derive from inputs")
