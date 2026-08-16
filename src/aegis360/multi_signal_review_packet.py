"""Bounded review packets for neutral or role-scoped Event Timeline v2 events."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid


def build_multi_signal_review_packet(
    timeline: Mapping[str, object], grid: Mapping[str, object], *,
    event_id: str, timeline_sha256: str, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None for value in (timeline_sha256, grid_sha256)):
        raise ValueError("multi-signal review checksums are invalid")
    if timeline.get("schema_version") != "aegis360.event-timeline.v2" or timeline.get("source_id") != grid["source_id"] or timeline.get("window") != grid["window"] or timeline.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256:
        raise ValueError("multi-signal review lineage is invalid")
    matches = [event for event in timeline["events"] if event["event_id"] == event_id]
    if len(matches) != 1:
        raise ValueError("multi-signal review requires one declared event")
    event = matches[0]
    scope = event["review_scope"]
    declared_ids = {candidate["candidate_id"] for candidate in grid["candidates"]}
    if scope["mode"] == "all_declared_candidates":
        candidate_ids = scope["candidate_ids"]
        if candidate_ids != [item["candidate_id"] for item in grid["candidates"]]:
            raise ValueError("neutral review scope must retain the declared grid order")
        samples = [
            {"sample_id": "sample:00", "temporal_role": "before_boundary",
             "timestamp_seconds": event["start_seconds"], "candidate_ids": candidate_ids},
            {"sample_id": "sample:01", "temporal_role": "after_boundary",
             "timestamp_seconds": event["end_seconds"], "candidate_ids": candidate_ids},
        ]
        policy_id = "all_candidates_before_after_v1"
    elif scope["mode"] == "current_and_available_proposed":
        current = scope["current_candidate_id"]
        proposed = scope["proposed_candidate_id"]
        if {current, proposed} - declared_ids:
            raise ValueError("role-scoped review candidates are not declared")
        duration = event["end_seconds"] - event["start_seconds"]
        samples = []
        for index, fraction in enumerate((0.0, 0.25, 0.5, 0.75, 1.0)):
            timestamp = event["start_seconds"] + duration * fraction
            candidates = [current]
            if any(interval["start_seconds"] <= timestamp < interval["end_seconds"] for interval in scope["proposed_available_intervals"]):
                candidates.append(proposed)
            samples.append({"sample_id": f"sample:{index:02d}",
                            "temporal_role": ("before", "early", "mid", "late", "after")[index],
                            "timestamp_seconds": timestamp, "candidate_ids": candidates})
        policy_id = "role_pair_quartiles_v1"
    else:
        raise ValueError("multi-signal review scope is unsupported")
    if sum(len(sample["candidate_ids"]) for sample in samples) > 10:
        raise ValueError("multi-signal review exceeds the ten-frame bound")
    return {
        "schema_version": "aegis360.event-review-packet.v2",
        "source_id": timeline["source_id"], "event_id": event_id,
        "inputs": {"event_timeline_sha256": timeline_sha256,
                   "context_view_grid_sha256": grid_sha256},
        "event": {"start_seconds": event["start_seconds"],
                  "end_seconds": event["end_seconds"],
                  "signals": event["signals"], "review_scope": scope},
        "sampling_policy": {"policy_id": policy_id, "maximum_rendered_frames": 10},
        "samples": samples,
        "temporary_media_policy": {"durable_pixels_allowed": False,
                                   "render_only_declared_candidates": True,
                                   "delete_after_adapter_completion": True},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False,
                    "contains_editorial_decision": False},
        "limitations": [
            "neutral scene packets expose candidate coverage but do not assign roles",
            "two boundary timestamps may miss short activity between them",
        ],
    }


def validate_multi_signal_review_packet(
    document: Mapping[str, object], timeline: Mapping[str, object],
    grid: Mapping[str, object], *, timeline_sha256: str, grid_sha256: str,
) -> None:
    expected = build_multi_signal_review_packet(
        timeline, grid, event_id=document.get("event_id", ""),
        timeline_sha256=timeline_sha256, grid_sha256=grid_sha256,
    )
    if document != expected:
        raise ValueError("multi-signal review packet must exactly derive from inputs")
