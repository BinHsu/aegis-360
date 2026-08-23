"""Partition a whole-video window at every retained scene boundary."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.story-segment-timeline.v1"


def build_story_segment_timeline(
    timeline: Mapping[str, object], *, timeline_sha256: str,
) -> dict[str, object]:
    if (timeline.get("schema_version") != "aegis360.event-timeline.v2"
            or re.fullmatch(r"[0-9a-f]{64}", timeline_sha256 or "") is None):
        raise ValueError("story-segment timeline input is invalid")
    window = timeline.get("window", {})
    window_start = window.get("start_seconds")
    duration = window.get("duration_seconds")
    if not isinstance(window_start, (int, float)) or not isinstance(duration, (int, float)) or duration <= 0:
        raise ValueError("story-segment window is invalid")
    window_end = window_start + duration
    boundaries = []
    for event in timeline.get("events", []):
        for signal in event.get("signals", []):
            if signal.get("signal_type") != "scene_change":
                continue
            timestamp = signal.get("evidence", {}).get("timestamp_seconds")
            if not isinstance(timestamp, (int, float)) or not window_start < timestamp < window_end:
                raise ValueError("story-segment boundary is outside the open window")
            boundaries.append({"timestamp_seconds": float(timestamp),
                               "event_id": event["event_id"],
                               "signal_id": signal["signal_id"]})
    boundaries.sort(key=lambda item: (item["timestamp_seconds"], item["event_id"],
                                      item["signal_id"]))
    if not boundaries or any(
        left["timestamp_seconds"] == right["timestamp_seconds"]
        for left, right in zip(boundaries, boundaries[1:])
    ):
        raise ValueError("story-segment boundaries must be nonempty and unique")
    points = [float(window_start), *[item["timestamp_seconds"] for item in boundaries],
              float(window_end)]
    segments = []
    for index, (start, end) in enumerate(zip(points, points[1:])):
        if end <= start:
            raise ValueError("story segment duration must be positive")
        segments.append({
            "segment_id": f"segment:story:{index:04d}",
            "start_seconds": start, "end_seconds": end,
            "left_boundary": None if index == 0 else boundaries[index - 1],
            "right_boundary": None if index == len(boundaries) else boundaries[index],
        })
    return {
        "schema_version": SCHEMA, "source_id": timeline["source_id"],
        "window": dict(window),
        "input": {"event_timeline_sha256": timeline_sha256},
        "segments": segments,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False, "contains_editorial_decision": False},
        "limitations": [
            "high-recall boundaries may over-segment the source",
            "segments define sampling scope but do not establish importance or a view",
            "story constraints decide whether adjacent segments prefer continuity",
        ],
    }


def validate_story_segment_timeline(
    document: Mapping[str, object], timeline: Mapping[str, object], *,
    timeline_sha256: str,
) -> None:
    expected = build_story_segment_timeline(timeline, timeline_sha256=timeline_sha256)
    if document != expected:
        raise ValueError("story-segment timeline must exactly derive from input")
