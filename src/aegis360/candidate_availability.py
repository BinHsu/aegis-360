"""Closed candidate-scoped visual availability bound to declared geometry."""

from __future__ import annotations

import math
import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.candidate-availability.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")


def build_candidate_availability(
    config: Mapping[str, object], grid: Mapping[str, object], *,
    config_sha256: str, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if not isinstance(config, Mapping) or set(config) != {
        "schema_version", "config_id", "reviewer_kind", "adapter_id", "candidates",
    } or config["schema_version"] != "aegis360.candidate-availability-config.v1":
        raise ValueError("candidate-availability config is invalid")
    if config["reviewer_kind"] not in {"human", "local_vlm"}:
        raise ValueError("candidate-availability reviewer is invalid")
    for value, label in ((config["config_id"], "config_id"), (config["adapter_id"], "adapter_id")):
        if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
            raise ValueError(f"{label} must be privacy-safe")
    if not all(re.fullmatch(r"[0-9a-f]{64}", value) for value in (config_sha256, grid_sha256)):
        raise ValueError("candidate-availability checksums are invalid")
    declared = {item["candidate_id"] for item in grid["candidates"]}
    rows = config["candidates"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("candidate availability must declare at least one candidate")
    seen = set()
    canonical = []
    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"candidate_id", "intervals"}:
            raise ValueError("candidate-availability row is invalid")
        candidate_id = row["candidate_id"]
        if candidate_id not in declared or candidate_id in seen:
            raise ValueError("candidate availability must reference unique declared candidates")
        seen.add(candidate_id)
        intervals = row["intervals"]
        if not isinstance(intervals, list):
            raise ValueError("candidate intervals must be an array")
        previous_end = window_start
        canonical_intervals = []
        for interval in intervals:
            if not isinstance(interval, Mapping) or set(interval) != {"start_seconds", "end_seconds"}:
                raise ValueError("candidate interval fields are invalid")
            start, end = interval["start_seconds"], interval["end_seconds"]
            if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (start, end)) or start < previous_end or end <= start or end > window_end:
                raise ValueError("candidate intervals must be finite, ordered and within the grid window")
            canonical_intervals.append({"start_seconds": float(start), "end_seconds": float(end)})
            previous_end = end
        canonical.append({"candidate_id": candidate_id, "intervals": canonical_intervals})
    return {
        "schema_version": SCHEMA,
        "source_id": grid["source_id"],
        "window": dict(grid["window"]),
        "context_view_grid": {"schema_version": grid["schema_version"], "sha256": grid_sha256},
        "provenance": {"reviewer_kind": config["reviewer_kind"], "adapter_id": config["adapter_id"],
                       "config_id": config["config_id"], "config_sha256": config_sha256},
        "candidates": canonical,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_names": False, "contains_identity": False},
        "limitations": [
            "availability is candidate visibility evidence, not identity or editorial utility",
            "unlisted candidates have no availability and must fail closed",
        ],
    }


def validate_candidate_availability(
    document: Mapping[str, object], grid: Mapping[str, object], *, grid_sha256: str,
) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "context_view_grid", "provenance",
        "candidates", "privacy", "limitations",
    } or document["schema_version"] != SCHEMA:
        raise ValueError("candidate-availability fields or schema are invalid")
    provenance = document["provenance"]
    if not isinstance(provenance, Mapping) or set(provenance) != {
        "reviewer_kind", "adapter_id", "config_id", "config_sha256",
    }:
        raise ValueError("candidate-availability provenance is invalid")
    config = {
        "schema_version": "aegis360.candidate-availability-config.v1",
        "config_id": provenance["config_id"], "reviewer_kind": provenance["reviewer_kind"],
        "adapter_id": provenance["adapter_id"], "candidates": document["candidates"],
    }
    expected = build_candidate_availability(
        config, grid, config_sha256=provenance["config_sha256"], grid_sha256=grid_sha256,
    )
    if document != expected:
        raise ValueError("candidate availability must exactly bind the declared grid")
