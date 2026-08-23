"""Bounded local-story context for one exact retained scene signal."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid
from .scene_story_packet import _unique_anchors


SCHEMA = "aegis360.scene-boundary-story-review-packet.v1"


def build_scene_boundary_story_packet(
    timeline: Mapping[str, object], grid: Mapping[str, object], *,
    event_id: str, signal_id: str, timeline_sha256: str, grid_sha256: str,
    far_context_seconds: float = 15.0, near_context_seconds: float = 3.0,
    boundary_offset_seconds: float = 0.25,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None
           for value in (timeline_sha256, grid_sha256)):
        raise ValueError("scene-boundary story checksums are invalid")
    if (timeline.get("schema_version") != "aegis360.event-timeline.v2"
            or timeline.get("source_id") != grid["source_id"]
            or timeline.get("window") != grid["window"]
            or timeline.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256):
        raise ValueError("scene-boundary story lineage is invalid")
    if not (0 < boundary_offset_seconds < near_context_seconds < far_context_seconds <= 30):
        raise ValueError("scene-boundary story context policy is invalid")
    events = [item for item in timeline["events"] if item["event_id"] == event_id]
    if len(events) != 1:
        raise ValueError("scene-boundary story packet requires one declared event")
    event = events[0]
    matches = [item for item in event["signals"]
               if item["signal_id"] == signal_id and item["signal_type"] == "scene_change"]
    if len(matches) != 1:
        raise ValueError("scene-boundary story packet requires one exact scene signal")
    timestamp = float(matches[0]["evidence"]["timestamp_seconds"])
    window_start = float(grid["window"]["start_seconds"])
    window_end = window_start + float(grid["window"]["duration_seconds"])
    clamp = lambda value: max(window_start, min(window_end, value))
    samples = _unique_anchors([
        ("far_before", clamp(timestamp - far_context_seconds)),
        ("near_before", clamp(timestamp - near_context_seconds)),
        ("boundary_before", clamp(timestamp - boundary_offset_seconds)),
        ("boundary_after", clamp(timestamp + boundary_offset_seconds)),
        ("near_after", clamp(timestamp + near_context_seconds)),
        ("far_after", clamp(timestamp + far_context_seconds)),
    ])
    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    if len(candidate_ids) != 4 or not 2 <= len(samples) <= 6:
        raise ValueError("scene-boundary story cardinal scope is invalid")
    for sample in samples:
        sample["representation"] = "four_cardinal_contact_sheet"
        sample["candidate_ids"] = candidate_ids
    ordered_signals = [signal for item in timeline["events"] for signal in item["signals"]
                       if signal["signal_type"] == "scene_change"]
    signal_index = next(index for index, signal in enumerate(ordered_signals)
                        if signal["signal_id"] == signal_id)
    return {
        "schema_version": SCHEMA, "source_id": timeline["source_id"],
        "event_id": event_id, "signal_id": signal_id,
        "inputs": {"event_timeline_sha256": timeline_sha256,
                   "context_view_grid_sha256": grid_sha256},
        "boundary": {"timestamp_seconds": timestamp, "signal": matches[0],
                     "signal_index": signal_index,
                     "signal_count": len(ordered_signals)},
        "sampling_policy": {"policy_id": "exact_scene_signal_six_anchor_cardinal_v1",
                            "far_context_seconds": float(far_context_seconds),
                            "near_context_seconds": float(near_context_seconds),
                            "boundary_offset_seconds": float(boundary_offset_seconds),
                            "maximum_composite_frames": 6,
                            "maximum_source_viewports": 24},
        "samples": samples,
        "temporary_media_policy": {"durable_pixels_allowed": False,
                                   "render_only_declared_candidates": True,
                                   "delete_after_adapter_completion": True},
        "limitations": ["one signal packet does not establish the whole chapter map",
                        "story review cannot select a view or renderer command"],
    }


def validate_scene_boundary_story_packet(
    document: Mapping[str, object], timeline: Mapping[str, object],
    grid: Mapping[str, object], *, timeline_sha256: str, grid_sha256: str,
) -> None:
    policy = document.get("sampling_policy", {})
    expected = build_scene_boundary_story_packet(
        timeline, grid, event_id=document.get("event_id", ""),
        signal_id=document.get("signal_id", ""), timeline_sha256=timeline_sha256,
        grid_sha256=grid_sha256,
        far_context_seconds=policy.get("far_context_seconds", -1),
        near_context_seconds=policy.get("near_context_seconds", -1),
        boundary_offset_seconds=policy.get("boundary_offset_seconds", -1),
    )
    if document != expected:
        raise ValueError("scene-boundary story packet must exactly derive from inputs")
