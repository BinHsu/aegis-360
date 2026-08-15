"""Build broad live-scene availability without asserting identity or roles."""

from __future__ import annotations

import math
import statistics
from typing import Mapping

from .semantic_events import build_semantic_event_artifact


def build_live_scene_intervals(
    semantic: Mapping[str, object], *, maximum_gap_seconds: float = 1.5,
    minimum_supporting_timestamps: int = 2,
) -> dict[str, object]:
    canonical = build_semantic_event_artifact(
        source_id=semantic.get("source_id"), model_id=semantic.get("model_id"),
        viewports=semantic.get("viewports", []), events=semantic.get("events", []),
    )
    if semantic != canonical:
        raise ValueError("semantic event input must be canonical v2")
    if not isinstance(maximum_gap_seconds, (int, float)) or isinstance(maximum_gap_seconds, bool) or not math.isfinite(maximum_gap_seconds) or maximum_gap_seconds <= 0:
        raise ValueError("maximum gap must be finite and positive")
    if isinstance(minimum_supporting_timestamps, bool) or minimum_supporting_timestamps < 1:
        raise ValueError("minimum supporting timestamps must be positive")
    all_timestamps = sorted({row["timestamp_seconds"] for row in semantic["events"]})
    if len(all_timestamps) < 2:
        raise ValueError("at least two semantic timestamps are required")
    cadence = statistics.median(b - a for a, b in zip(all_timestamps, all_timestamps[1:]))
    person_timestamps = sorted({
        row["timestamp_seconds"] for row in semantic["events"]
        if any(item["class_name"] == "person" for item in row["detections"])
    })
    groups = []
    for timestamp in person_timestamps:
        if not groups or timestamp - groups[-1][-1] > maximum_gap_seconds:
            groups.append([timestamp])
        else:
            groups[-1].append(timestamp)
    intervals = [
        {"start_seconds": group[0], "end_seconds": group[-1] + cadence,
         "supporting_timestamp_count": len(group)}
        for group in groups if len(group) >= minimum_supporting_timestamps
    ]
    return {
        "schema_version": "aegis360.live-scene-intervals.v1",
        "source_id": semantic["source_id"],
        "source_semantic_schema": semantic["schema_version"],
        "policy": {"maximum_gap_seconds": float(maximum_gap_seconds),
                   "minimum_supporting_timestamps": minimum_supporting_timestamps,
                   "status": "broad_person_presence_not_role_or_identity"},
        "intervals": intervals,
        "privacy": dict(semantic["privacy"]),
        "limitations": [
            "any-view person presence only bounds live-scene availability",
            "availability does not prove performer, audience, identity or shot quality",
        ],
    }


def validate_live_scene_intervals(document: Mapping[str, object]) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "source_semantic_schema", "policy",
        "intervals", "privacy", "limitations",
    } or document["schema_version"] != "aegis360.live-scene-intervals.v1":
        raise ValueError("live-scene fields or schema are invalid")
    previous_end = -1.0
    for item in document["intervals"]:
        if not isinstance(item, Mapping) or set(item) != {
            "start_seconds", "end_seconds", "supporting_timestamp_count",
        } or item["start_seconds"] < previous_end or item["end_seconds"] <= item["start_seconds"]:
            raise ValueError("live-scene intervals must be ordered and disjoint")
        previous_end = item["end_seconds"]
