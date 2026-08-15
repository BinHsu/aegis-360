"""Conservatively group overlapping sound-classifier reaction evidence."""

from __future__ import annotations

import math
from typing import Mapping

from .sound_events import validate_sound_events


def build_reaction_intervals(
    sound_events: Mapping[str, object],
    *,
    applause_threshold: float = 0.5,
    clapping_threshold: float = 0.5,
    minimum_supporting_windows: int = 2,
) -> dict[str, object]:
    validate_sound_events(sound_events)
    if not all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and 0 <= value <= 1
        for value in (applause_threshold, clapping_threshold)
    ):
        raise ValueError("reaction thresholds must be finite values in [0, 1]")
    if isinstance(minimum_supporting_windows, bool) or minimum_supporting_windows < 1:
        raise ValueError("minimum supporting windows must be positive")
    eligible = []
    for row in sound_events["windows"]:
        scores = {item["label"]: item["confidence"] for item in row["classifications"]}
        if scores["applause"] >= applause_threshold and scores["clapping"] >= clapping_threshold:
            eligible.append({
                "start_seconds": row["start_seconds"],
                "end_seconds": row["start_seconds"] + row["duration_seconds"],
                "applause_confidence": scores["applause"],
                "clapping_confidence": scores["clapping"],
            })
    merged = []
    for row in eligible:
        if not merged or row["start_seconds"] > merged[-1]["end_seconds"] + 1e-9:
            merged.append({
                "start_seconds": row["start_seconds"],
                "end_seconds": row["end_seconds"],
                "supporting_window_count": 1,
                "peak_applause_confidence": row["applause_confidence"],
                "peak_clapping_confidence": row["clapping_confidence"],
            })
        else:
            current = merged[-1]
            current["end_seconds"] = max(current["end_seconds"], row["end_seconds"])
            current["supporting_window_count"] += 1
            current["peak_applause_confidence"] = max(
                current["peak_applause_confidence"], row["applause_confidence"]
            )
            current["peak_clapping_confidence"] = max(
                current["peak_clapping_confidence"], row["clapping_confidence"]
            )
    intervals = [
        item for item in merged
        if item["supporting_window_count"] >= minimum_supporting_windows
    ]
    return {
        "schema_version": "aegis360.reaction-intervals.v1",
        "source_id": sound_events["source_id"],
        "source_sound_event_schema": sound_events["schema_version"],
        "policy": {
            "applause_threshold": float(applause_threshold),
            "clapping_threshold": float(clapping_threshold),
            "minimum_supporting_windows": minimum_supporting_windows,
            "status": "poc_hypothesis_not_editorial_ground_truth",
        },
        "intervals": intervals,
        "privacy": dict(sound_events["privacy"]),
        "limitations": [
            "applause and clapping labels come from one classifier and are not independent evidence",
            "candidate intervals do not identify an audience view or authorize a camera cut",
        ],
    }


def validate_reaction_intervals(document: Mapping[str, object]) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "source_sound_event_schema", "policy",
        "intervals", "privacy", "limitations",
    }:
        raise ValueError("reaction-interval fields must match the closed schema")
    if document["schema_version"] != "aegis360.reaction-intervals.v1":
        raise ValueError("unsupported reaction-interval schema")
    policy = document["policy"]
    if not isinstance(policy, Mapping) or set(policy) != {
        "applause_threshold", "clapping_threshold", "minimum_supporting_windows", "status",
    } or policy["status"] != "poc_hypothesis_not_editorial_ground_truth":
        raise ValueError("reaction policy is invalid")
    previous_end = -1.0
    intervals = document["intervals"]
    if not isinstance(intervals, list):
        raise ValueError("reaction intervals must be an array")
    for item in intervals:
        if not isinstance(item, Mapping) or set(item) != {
            "start_seconds", "end_seconds", "supporting_window_count",
            "peak_applause_confidence", "peak_clapping_confidence",
        }:
            raise ValueError("reaction interval fields are invalid")
        start, end = item["start_seconds"], item["end_seconds"]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) for value in (start, end)) or start < previous_end or end <= start:
            raise ValueError("reaction intervals must be finite, ordered and disjoint")
        previous_end = end
        if not isinstance(item["supporting_window_count"], int) or item["supporting_window_count"] < policy["minimum_supporting_windows"]:
            raise ValueError("reaction interval support is insufficient")
        if any(not 0 <= item[key] <= 1 for key in ("peak_applause_confidence", "peak_clapping_confidence")):
            raise ValueError("reaction peaks must be in [0, 1]")
