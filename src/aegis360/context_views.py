"""Deterministic geometry-owned context views for semantic role binding."""

from __future__ import annotations

import math
import re
from typing import Mapping


SCHEMA = "aegis360.context-view-grid.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
CARDINAL_YAWS = (0.0, 90.0, -180.0, -90.0)


def build_context_view_grid(
    *, source_id: str, start_seconds: float, duration_seconds: float,
    pitch_degrees: float = 0.0, horizontal_fov_degrees: float = 110.0,
) -> dict[str, object]:
    if not isinstance(source_id, str) or not SAFE_ID.fullmatch(source_id):
        raise ValueError("source_id must be privacy-safe")
    values = (start_seconds, duration_seconds, pitch_degrees, horizontal_fov_degrees)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in values):
        raise ValueError("context-view geometry must be finite")
    if start_seconds < 0 or duration_seconds <= 0:
        raise ValueError("context-view window is invalid")
    if not -90 <= pitch_degrees <= 90 or not 0 < horizontal_fov_degrees < 180:
        raise ValueError("context-view pitch or HFOV is invalid")
    candidates = [
        {
            "candidate_id": f"context:cardinal:{index}",
            "candidate_type": "context",
            "yaw_degrees": yaw,
            "pitch_degrees": float(pitch_degrees),
            "horizontal_fov_degrees": float(horizontal_fov_degrees),
        }
        for index, yaw in enumerate(CARDINAL_YAWS)
    ]
    return {
        "schema_version": SCHEMA,
        "source_id": source_id,
        "window": {"start_seconds": float(start_seconds), "duration_seconds": float(duration_seconds)},
        "generation_policy": {
            "policy_id": "four_cardinal_context_views_v1",
            "yaw_degrees": list(CARDINAL_YAWS),
            "pitch_degrees": float(pitch_degrees),
            "horizontal_fov_degrees": float(horizontal_fov_degrees),
        },
        "candidates": candidates,
        "privacy": {"contains_source_path": False, "contains_pixels": False},
        "limitations": [
            "context views are geometry coverage proposals without semantic roles",
            "cardinal coverage does not prove acceptable composition",
        ],
    }


def validate_context_view_grid(document: Mapping[str, object]) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "generation_policy",
        "candidates", "privacy", "limitations",
    }:
        raise ValueError("context-view fields must match the closed schema")
    expected = build_context_view_grid(
        source_id=document["source_id"],
        start_seconds=document["window"]["start_seconds"],
        duration_seconds=document["window"]["duration_seconds"],
        pitch_degrees=document["generation_policy"]["pitch_degrees"],
        horizontal_fov_degrees=document["generation_policy"]["horizontal_fov_degrees"],
    )
    if document != expected:
        raise ValueError("context-view grid must match deterministic generation")
