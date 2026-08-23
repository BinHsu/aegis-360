"""Checksummed union of scene evidence measured at multiple time scales."""

from __future__ import annotations

import re
from typing import Mapping, Sequence


SCHEMA = "aegis360.ffmpeg-scene-event-pyramid.v1"


def build_scene_event_pyramid(
    documents: Sequence[Mapping[str, object]], *, sha256s: Sequence[str],
) -> dict[str, object]:
    if len(documents) < 2 or len(documents) != len(sha256s):
        raise ValueError("scene-event pyramid requires two or more matched inputs")
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None for value in sha256s):
        raise ValueError("scene-event pyramid checksums are invalid")
    first = documents[0]
    if first.get("schema_version") != "aegis360.ffmpeg-scene-events.v1":
        raise ValueError("scene-event pyramid input is invalid")
    source_id = first.get("source_id")
    source_sha256 = first.get("source_sha256")
    inputs = []
    events = []
    cadences = set()
    for document, sha256 in zip(documents, sha256s, strict=True):
        if (document.get("schema_version") != "aegis360.ffmpeg-scene-events.v1"
                or document.get("source_id") != source_id
                or document.get("source_sha256") != source_sha256):
            raise ValueError("scene-event pyramid inputs must describe one source")
        config = document.get("config", {})
        sample_fps = config.get("sample_fps")
        if sample_fps in cadences:
            raise ValueError("scene-event pyramid cadences must be unique")
        cadences.add(sample_fps)
        inputs.append({
            "scene_events_sha256": sha256,
            "sample_fps": sample_fps,
            "threshold": config.get("threshold"),
            "proxy_width": config.get("proxy_width"),
        })
        events.extend({
            "timestamp_seconds": event["timestamp_seconds"],
            "scene_score": event["scene_score"],
            "sample_fps": sample_fps,
        } for event in document.get("events", []))
    inputs.sort(key=lambda item: item["sample_fps"])
    events.sort(key=lambda item: (item["timestamp_seconds"], item["sample_fps"],
                                  -item["scene_score"]))
    return {
        "schema_version": SCHEMA,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "inputs": inputs,
        "events": events,
        "privacy": dict(first["privacy"]),
        "limitations": [
            "scene scores from different cadences are not calibrated probabilities",
            "the pyramid preserves boundaries but does not establish editorial importance",
        ],
    }
