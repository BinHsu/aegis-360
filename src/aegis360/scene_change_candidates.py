"""Deterministic temporal suppression for raw scene-score peaks."""

from __future__ import annotations

import math
import re
from typing import Mapping


def build_scene_change_candidates(
    scene_events: Mapping[str, object], *, scene_events_sha256: str,
    score_floor: float = 0.4, minimum_separation_seconds: float = 10.0,
) -> dict[str, object]:
    if scene_events.get("schema_version") != "aegis360.ffmpeg-scene-events.v1" or re.fullmatch(r"[0-9a-f]{64}", scene_events_sha256 or "") is None:
        raise ValueError("scene-change candidate input is invalid")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 for value in (score_floor, minimum_separation_seconds)) or score_floor > 1:
        raise ValueError("scene-change candidate policy is invalid")
    eligible = [event for event in scene_events["events"] if event["scene_score"] >= score_floor]
    selected = []
    for event in sorted(eligible, key=lambda item: (-item["scene_score"], item["timestamp_seconds"])):
        if all(abs(event["timestamp_seconds"] - kept["timestamp_seconds"]) >= minimum_separation_seconds for kept in selected):
            selected.append(event)
    selected.sort(key=lambda item: item["timestamp_seconds"])
    return {
        "schema_version": "aegis360.scene-change-candidates.v1",
        "source_id": scene_events["source_id"],
        "input": {"scene_events_sha256": scene_events_sha256},
        "policy": {"score_floor": float(score_floor),
                   "minimum_separation_seconds": float(minimum_separation_seconds),
                   "selection": "descending_score_temporal_nms_v1"},
        "candidates": [
            {"event_id": f"event:scene-change:{index:04d}",
             "timestamp_seconds": event["timestamp_seconds"],
             "scene_score": event["scene_score"]}
            for index, event in enumerate(selected)
        ],
        "privacy": dict(scene_events["privacy"]),
        "limitations": [
            "temporal suppression reduces duplicate review but does not establish importance",
            "score floor and separation are tunable POC thresholds",
        ],
    }
