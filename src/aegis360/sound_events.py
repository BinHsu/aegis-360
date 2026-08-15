"""Closed validation for path-free Apple SoundAnalysis event evidence."""

from __future__ import annotations

import math
import re
from typing import Mapping


SCHEMA = "aegis360.apple-sound-events.v1"
LABELS = ("music", "applause", "clapping", "cheering")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
LIMITATIONS = (
    "classification confidence is model evidence, not editorial utility",
    "labels do not identify a sound source or direction",
)


def _finite_number(value: object, label: str, *, positive: bool = False) -> float:
    if (
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not math.isfinite(value) or value < 0 or (positive and value <= 0)
    ):
        raise ValueError(f"{label} must be a finite {'positive' if positive else 'nonnegative'} number")
    return float(value)


def validate_sound_events(document: Mapping[str, object]) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "classifier", "windows",
        "privacy", "limitations",
    }:
        raise ValueError("sound-event fields must match the closed schema")
    if document["schema_version"] != SCHEMA:
        raise ValueError("unsupported sound-event schema")
    source_id = document["source_id"]
    if not isinstance(source_id, str) or not SAFE_ID.fullmatch(source_id):
        raise ValueError("source_id must be privacy-safe")
    window = document["window"]
    if not isinstance(window, Mapping) or set(window) != {
        "start_seconds", "duration_seconds", "analysis_channel_count",
        "analysis_sample_rate_hz",
    }:
        raise ValueError("analysis window fields must match the closed schema")
    start = _finite_number(window["start_seconds"], "start_seconds")
    duration = _finite_number(window["duration_seconds"], "duration_seconds", positive=True)
    if window["analysis_channel_count"] != 1 or window["analysis_sample_rate_hz"] != 44100:
        raise ValueError("analysis PCM contract must be mono 44100 Hz")
    classifier = document["classifier"]
    if not isinstance(classifier, Mapping) or classifier != {
        "allowed_labels": list(LABELS),
        "framework": "Apple SoundAnalysis",
        "identifier": "SNClassifierIdentifierVersion1",
        "overlap_factor": 0.5,
    }:
        raise ValueError("classifier contract is invalid")
    rows = document["windows"]
    if not isinstance(rows, list):
        raise ValueError("classification windows must be an array")
    previous = -1.0
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "start_seconds", "duration_seconds", "classifications",
        }:
            raise ValueError("classification window fields are invalid")
        row_start = _finite_number(row["start_seconds"], "classification start")
        row_duration = _finite_number(row["duration_seconds"], "classification duration", positive=True)
        if row_start < start or row_start + row_duration > start + duration + 1e-3 or row_start < previous:
            raise ValueError("classification windows must be ordered inside the requested window")
        previous = row_start
        values = row["classifications"]
        if not isinstance(values, list) or [item.get("label") for item in values if isinstance(item, Mapping)] != list(LABELS):
            raise ValueError("classifications must retain the ordered allowlist")
        for item in values:
            if not isinstance(item, Mapping) or set(item) != {"label", "confidence"}:
                raise ValueError("classification fields are invalid")
            confidence = _finite_number(item["confidence"], "classification confidence")
            if confidence > 1:
                raise ValueError("classification confidence must be in [0, 1]")
    if document["privacy"] != {
        "contains_source_path": False, "contains_audio": False,
        "contains_transcript": False,
    }:
        raise ValueError("sound-event privacy declaration is invalid")
    if document["limitations"] != list(LIMITATIONS):
        raise ValueError("sound-event limitations are invalid")
