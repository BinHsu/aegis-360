"""Privacy-safe sparse scene-change evidence from FFmpeg metadata output."""

from __future__ import annotations

import math
import re
from typing import Mapping


FRAME = re.compile(r"^frame:\d+\s+pts:\S+\s+pts_time:([0-9.eE+-]+)$")
SCORE = re.compile(r"^lavfi\.scene_score=([0-9.eE+-]+)$")


def parse_scene_metadata(output: str) -> list[dict[str, float]]:
    events = []
    timestamp = None
    for line in output.splitlines():
        frame = FRAME.fullmatch(line.strip())
        if frame:
            timestamp = float(frame.group(1))
            continue
        score = SCORE.fullmatch(line.strip())
        if score and timestamp is not None:
            value = float(score.group(1))
            if not math.isfinite(timestamp) or timestamp < 0 or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("scene metadata value is invalid")
            events.append({"timestamp_seconds": timestamp, "scene_score": value})
            timestamp = None
    return events


def build_scene_events(
    *, source_id: str, source_sha256: str, threshold: float,
    sample_fps: float, proxy_width: int, ffmpeg_version: str,
    metadata_output: str,
) -> dict[str, object]:
    if re.fullmatch(r"[A-Za-z0-9._:-]+", source_id or "") is None or re.fullmatch(r"[0-9a-f]{64}", source_sha256 or "") is None:
        raise ValueError("scene-event source provenance is invalid")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0 for value in (sample_fps, proxy_width)) or not 0 < threshold <= 1:
        raise ValueError("scene-event configuration is invalid")
    if not isinstance(proxy_width, int) or proxy_width > 1920 or not ffmpeg_version:
        raise ValueError("scene-event runtime is invalid")
    events = parse_scene_metadata(metadata_output)
    if any(event["scene_score"] < threshold for event in events):
        raise ValueError("scene-event output contains a below-threshold event")
    return {
        "schema_version": "aegis360.ffmpeg-scene-events.v1",
        "source_id": source_id, "source_sha256": source_sha256,
        "config": {"threshold": float(threshold), "sample_fps": float(sample_fps),
                   "proxy_width": proxy_width, "filter": "ffmpeg_scene_score_v1"},
        "runtime": {"ffmpeg_version": ffmpeg_version},
        "events": events,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False},
        "limitations": [
            "scene score detects visual change and does not establish editorial importance",
            "360 camera motion and projection content may produce scene-score peaks",
        ],
    }
