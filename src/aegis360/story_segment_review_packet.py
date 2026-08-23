"""Candidate-view review scoped strictly inside one story segment."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.story-segment-review-packet.v1"


def build_story_segment_review_packet(
    segment_timeline: Mapping[str, object], grid: Mapping[str, object], *,
    segment_id: str, segment_timeline_sha256: str, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None
           for value in (segment_timeline_sha256, grid_sha256)):
        raise ValueError("story-segment review checksums are invalid")
    if (segment_timeline.get("schema_version") != "aegis360.story-segment-timeline.v1"
            or segment_timeline.get("source_id") != grid["source_id"]
            or segment_timeline.get("window") != grid["window"]):
        raise ValueError("story-segment review lineage is invalid")
    matches = [item for item in segment_timeline["segments"]
               if item["segment_id"] == segment_id]
    if len(matches) != 1:
        raise ValueError("story-segment review requires one declared segment")
    segment = matches[0]
    duration = segment["end_seconds"] - segment["start_seconds"]
    if duration <= 0:
        raise ValueError("story-segment duration is invalid")
    ids = [candidate["candidate_id"] for candidate in grid["candidates"]]
    fractions = (.2, .5, .8)
    samples = [{
        "sample_id": f"sample:{index:02d}",
        "temporal_role": role,
        "timestamp_seconds": round(segment["start_seconds"] + duration * fraction, 6),
        "representation": "four_cardinal_contact_sheet", "candidate_ids": ids,
    } for index, (role, fraction) in enumerate(zip(("early", "middle", "late"), fractions))]
    return {
        "schema_version": SCHEMA, "source_id": segment_timeline["source_id"],
        "segment_id": segment_id,
        "inputs": {"story_segment_timeline_sha256": segment_timeline_sha256,
                   "context_view_grid_sha256": grid_sha256},
        "segment": dict(segment),
        "sampling_policy": {"policy_id": "segment_interior_quintiles_v1",
                            "fractions": list(fractions),
                            "maximum_composite_frames": 3,
                            "maximum_source_viewports": 12},
        "samples": samples,
        "temporary_media_policy": {"durable_pixels_allowed": False,
                                   "render_only_declared_candidates": True,
                                   "delete_after_adapter_completion": True},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False, "contains_editorial_decision": False},
        "limitations": [
            "high-recall boundaries can create short or over-segmented review scopes",
            "three interior samples do not establish identity",
            "candidate observations remain evidence; the planner selects the view",
        ],
    }


def validate_story_segment_review_packet(
    document: Mapping[str, object], segment_timeline: Mapping[str, object],
    grid: Mapping[str, object], *, segment_timeline_sha256: str, grid_sha256: str,
) -> None:
    expected = build_story_segment_review_packet(
        segment_timeline, grid, segment_id=document.get("segment_id", ""),
        segment_timeline_sha256=segment_timeline_sha256, grid_sha256=grid_sha256,
    )
    if document != expected:
        raise ValueError("story-segment review packet must exactly derive from inputs")
