"""Deterministic temporal suppression for raw scene-score peaks."""

from __future__ import annotations

import math
import re
from typing import Mapping


def build_scene_change_candidates(
    scene_events: Mapping[str, object], *, scene_events_sha256: str,
    score_floor: float = 0.25, minimum_separation_seconds: float = 1.0,
) -> dict[str, object]:
    accepted_schemas = {"aegis360.ffmpeg-scene-events.v1",
                        "aegis360.ffmpeg-scene-event-pyramid.v1"}
    if scene_events.get("schema_version") not in accepted_schemas or re.fullmatch(r"[0-9a-f]{64}", scene_events_sha256 or "") is None:
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
                   "selection": "high_recall_local_peak_nms_v2"},
        "candidates": [
            {"event_id": f"event:scene-change:{index:04d}",
             "timestamp_seconds": event["timestamp_seconds"],
             "scene_score": event["scene_score"]}
            for index, event in enumerate(selected)
        ],
        "privacy": dict(scene_events["privacy"]),
        "limitations": [
            "short-range temporal suppression removes duplicate peaks but does not establish importance",
            "distinct nearby cuts remain eligible for semantic review",
            "scores from different sampling cadences are ranking signals, not calibrated probabilities",
            "score floor and separation are tunable POC thresholds",
        ],
    }
