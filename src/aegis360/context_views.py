"""Deterministic geometry-owned context views for semantic role binding."""

from __future__ import annotations

import math
import re
from typing import Mapping


SCHEMA = "aegis360.context-view-grid.v1"
DECLARED_SCHEMA = "aegis360.context-view-grid.v2"
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
    if isinstance(document, Mapping) and document.get("schema_version") == DECLARED_SCHEMA:
        if set(document) != {
            "schema_version", "source_id", "window", "generation_policy",
            "candidates", "privacy", "limitations",
        }:
            raise ValueError("declared context-view fields must match the closed schema")
        source_id = document["source_id"]
        if not isinstance(source_id, str) or not SAFE_ID.fullmatch(source_id):
            raise ValueError("source_id must be privacy-safe")
        policy = document["generation_policy"]
        if not isinstance(policy, Mapping) or set(policy) != {"policy_id", "config_id", "config_sha256"} or policy["policy_id"] != "checksummed_declared_context_views_v2" or not isinstance(policy["config_id"], str) or not SAFE_ID.fullmatch(policy["config_id"]) or not re.fullmatch(r"[0-9a-f]{64}", policy["config_sha256"]):
            raise ValueError("declared context-view policy is invalid")
        window = document["window"]
        if not isinstance(window, Mapping) or set(window) != {"start_seconds", "duration_seconds"}:
            raise ValueError("declared context-view window is invalid")
        candidates = document["candidates"]
        if not isinstance(candidates, list) or not 2 <= len(candidates) <= 8:
            raise ValueError("declared context views must contain 2 to 8 candidates")
        ids = set()
        for item in candidates:
            if not isinstance(item, Mapping) or set(item) != {"candidate_id", "candidate_type", "yaw_degrees", "pitch_degrees", "horizontal_fov_degrees"} or item["candidate_type"] != "context" or not isinstance(item["candidate_id"], str) or not SAFE_ID.fullmatch(item["candidate_id"]) or item["candidate_id"] in ids:
                raise ValueError("declared context-view candidate is invalid")
            ids.add(item["candidate_id"])
            yaw, pitch, hfov = item["yaw_degrees"], item["pitch_degrees"], item["horizontal_fov_degrees"]
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (yaw, pitch, hfov)) or not -180 <= yaw < 180 or not -90 <= pitch <= 90 or not 0 < hfov < 180:
                raise ValueError("declared context-view geometry is invalid")
        if document["privacy"] != {"contains_source_path": False, "contains_pixels": False}:
            raise ValueError("declared context-view privacy is invalid")
        return
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


def build_declared_context_view_grid(
    config: Mapping[str, object], *, config_sha256: str,
    source_id: str, start_seconds: float, duration_seconds: float,
) -> dict[str, object]:
    if not isinstance(config, Mapping) or set(config) != {"schema_version", "config_id", "candidates"} or config["schema_version"] != "aegis360.context-view-config.v1":
        raise ValueError("declared context-view config is invalid")
    artifact = {
        "schema_version": DECLARED_SCHEMA,
        "source_id": source_id,
        "window": {"start_seconds": float(start_seconds), "duration_seconds": float(duration_seconds)},
        "generation_policy": {"policy_id": "checksummed_declared_context_views_v2", "config_id": config["config_id"], "config_sha256": config_sha256},
        "candidates": config["candidates"],
        "privacy": {"contains_source_path": False, "contains_pixels": False},
        "limitations": [
            "declared views are geometry proposals without semantic roles",
            "source-specific composition is not generic directing evidence",
        ],
    }
    validate_context_view_grid(artifact)
    return artifact
