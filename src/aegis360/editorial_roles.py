"""Closed semantic roles bound to geometry-owned context-view candidates."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.editorial-view-roles.v1"
ROLES = {"primary_performance", "audience_reaction", "neutral_context"}
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")


def build_editorial_roles(
    grid: Mapping[str, object], *, grid_sha256: str,
    primary_candidate_id: str, reaction_candidate_id: str,
    adapter_id: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if not re.fullmatch(r"[0-9a-f]{64}", grid_sha256):
        raise ValueError("context-view grid SHA-256 is invalid")
    if not isinstance(adapter_id, str) or not SAFE_ID.fullmatch(adapter_id):
        raise ValueError("adapter_id must be privacy-safe")
    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    if primary_candidate_id == reaction_candidate_id or {
        primary_candidate_id, reaction_candidate_id
    } - set(candidate_ids):
        raise ValueError("primary and reaction roles require distinct declared candidates")
    assignments = [
        {
            "candidate_id": candidate_id,
            "role": (
                "primary_performance" if candidate_id == primary_candidate_id else
                "audience_reaction" if candidate_id == reaction_candidate_id else
                "neutral_context"
            ),
        }
        for candidate_id in candidate_ids
    ]
    return {
        "schema_version": SCHEMA,
        "source_id": grid["source_id"],
        "window": dict(grid["window"]),
        "context_view_grid": {"schema_version": grid["schema_version"], "sha256": grid_sha256},
        "provenance": {"reviewer_kind": "human", "adapter_id": adapter_id},
        "assignments": assignments,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_names": False, "contains_identity": False},
        "limitations": [
            "roles do not establish person identity or active speaker",
            "roles cannot create or alter camera geometry",
        ],
    }


def validate_editorial_roles(document: Mapping[str, object], grid: Mapping[str, object], *, grid_sha256: str) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "context_view_grid",
        "provenance", "assignments", "privacy", "limitations",
    }:
        raise ValueError("editorial-role fields must match the closed schema")
    assignments = document.get("assignments")
    if not isinstance(assignments, list):
        raise ValueError("editorial-role assignments must be an array")
    by_role = {item.get("role"): item.get("candidate_id") for item in assignments if isinstance(item, Mapping)}
    if set(item.get("role") for item in assignments if isinstance(item, Mapping)) - ROLES:
        raise ValueError("editorial role is unsupported")
    expected = build_editorial_roles(
        grid, grid_sha256=grid_sha256,
        primary_candidate_id=by_role.get("primary_performance", ""),
        reaction_candidate_id=by_role.get("audience_reaction", ""),
        adapter_id=document.get("provenance", {}).get("adapter_id", ""),
    )
    if document != expected:
        raise ValueError("editorial roles must exactly bind the declared grid")
