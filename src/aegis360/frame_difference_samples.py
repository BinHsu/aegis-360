"""Deterministic frame-difference samples parsed from FFmpeg metadata."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Mapping


SCHEMA = "aegis360.frame-difference-samples.v1"
CONFIG_SCHEMA = "aegis360.frame-difference-acquisition-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
FRAME = re.compile(r"^frame:\d+\s+pts:\S+\s+pts_time:(\S+)$")
YAVG = re.compile(r"^lavfi\.signalstats\.YAVG=(\S+)$")


def _finite_number(value: object, label: str) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value)):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _validate_config(config: Mapping[str, object]) -> None:
    if (not isinstance(config, Mapping) or set(config) != {
        "schema_version", "config_id", "pts_origin", "metadata_key",
        "normalization_divisor",
    } or config.get("schema_version") != CONFIG_SCHEMA
            or not isinstance(config.get("config_id"), str)
            or SAFE_ID.fullmatch(config["config_id"]) is None
            or config.get("pts_origin") != "interval_local"
            or config.get("metadata_key") != "lavfi.signalstats.YAVG"):
        raise ValueError("frame-difference acquisition config is invalid")
    divisor = _finite_number(config["normalization_divisor"], "normalization divisor")
    if divisor != 255.0:
        raise ValueError("frame-difference normalization divisor must be 255")


def parse_frame_difference_metadata(
    metadata_text: str, *, window_start_seconds: float,
    window_duration_seconds: float,
) -> list[dict[str, float]]:
    """Parse paired interval-local PTS/YAVG rows into absolute samples."""
    start = _finite_number(window_start_seconds, "window start")
    duration = _finite_number(window_duration_seconds, "window duration")
    if start < 0 or duration <= 0 or not isinstance(metadata_text, str):
        raise ValueError("frame-difference parse window or metadata is invalid")

    samples = []
    pending_pts: float | None = None
    previous_local = -math.inf
    for raw_line in metadata_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        frame = FRAME.fullmatch(line)
        if frame:
            if pending_pts is not None:
                raise ValueError("frame metadata is missing its YAVG pair")
            try:
                local = float(frame.group(1))
            except ValueError as error:
                raise ValueError("frame PTS is malformed") from error
            if (not math.isfinite(local) or local < 0 or local > duration
                    or local <= previous_local):
                raise ValueError("frame PTS must be finite, unique, ordered and inside the interval")
            pending_pts = local
            continue
        yavg = YAVG.fullmatch(line)
        if yavg:
            if pending_pts is None:
                raise ValueError("YAVG metadata has no frame pair")
            try:
                raw_value = float(yavg.group(1))
            except ValueError as error:
                raise ValueError("YAVG metadata is malformed") from error
            if not math.isfinite(raw_value) or not 0 <= raw_value <= 255:
                raise ValueError("YAVG must be finite and in [0, 255]")
            samples.append({
                "interval_pts_seconds": pending_pts,
                "pts_seconds": start + pending_pts,
                "normalized_difference": raw_value / 255.0,
            })
            previous_local = pending_pts
            pending_pts = None
            continue
        if line.startswith("frame:") or line.startswith("lavfi.signalstats.YAVG"):
            raise ValueError("frame-difference metadata line is malformed")
    if pending_pts is not None:
        raise ValueError("frame metadata is missing its YAVG pair")
    if not samples:
        raise ValueError("frame-difference metadata contains no paired samples")
    return samples


def build_frame_difference_samples(
    *, source_id: str, window: Mapping[str, object], source_sha256: str,
    config: Mapping[str, object], config_sha256: str, metadata_text: str,
) -> dict[str, object]:
    """Build one path-free, pixel-free exact acquisition artifact."""
    if (not isinstance(source_id, str) or SAFE_ID.fullmatch(source_id) is None
            or not isinstance(source_sha256, str) or SHA256.fullmatch(source_sha256) is None
            or not isinstance(config_sha256, str) or SHA256.fullmatch(config_sha256) is None):
        raise ValueError("frame-difference source or config provenance is invalid")
    if not isinstance(window, Mapping) or set(window) != {
        "start_seconds", "duration_seconds",
    }:
        raise ValueError("frame-difference window is invalid")
    start = _finite_number(window["start_seconds"], "window start")
    duration = _finite_number(window["duration_seconds"], "window duration")
    if start < 0 or duration <= 0:
        raise ValueError("frame-difference window is invalid")
    _validate_config(config)
    samples = parse_frame_difference_metadata(
        metadata_text, window_start_seconds=start,
        window_duration_seconds=duration,
    )
    return {
        "schema_version": SCHEMA,
        "source_id": source_id,
        "window": {"start_seconds": start, "duration_seconds": duration},
        "inputs": {
            "source_sha256": source_sha256,
            "acquisition_config_sha256": config_sha256,
            "metadata_sha256": hashlib.sha256(metadata_text.encode("utf-8")).hexdigest(),
        },
        "acquisition": {
            "config_id": config["config_id"],
            "pts_origin": "interval_local",
            "metadata_key": "lavfi.signalstats.YAVG",
            "normalization_divisor": 255.0,
        },
        "samples": samples,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_identity": False},
        "limitations": [
            "normalized frame difference is acquisition evidence, not editorial utility",
            "the future runner must define the exact upstream difference-filter contract",
        ],
    }


def validate_frame_difference_samples(
    document: Mapping[str, object], *, source_id: str,
    window: Mapping[str, object], source_sha256: str,
    config: Mapping[str, object], config_sha256: str, metadata_text: str,
) -> None:
    expected = build_frame_difference_samples(
        source_id=source_id, window=window, source_sha256=source_sha256,
        config=config, config_sha256=config_sha256, metadata_text=metadata_text,
    )
    if document != expected:
        raise ValueError("frame-difference samples must exactly derive from inputs")
