"""Closed relative editorial-gain decisions for proposed reaction views."""

from __future__ import annotations

import math
import re
from typing import Mapping

from .context_views import validate_context_view_grid
from .editorial_roles import validate_editorial_roles
from .reaction_intervals import validate_reaction_intervals


SCHEMA = "aegis360.reaction-view-gain.v1"
CONFIG_SCHEMA = "aegis360.reaction-view-gain-config.v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
SHA256 = re.compile(r"[0-9a-f]{64}")
DECISIONS = {"promote", "abstain"}


def build_reaction_view_gain(
    config: Mapping[str, object], grid: Mapping[str, object],
    roles: Mapping[str, object], reactions: Mapping[str, object], *,
    config_sha256: str, grid_sha256: str, roles_sha256: str,
    reactions_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    validate_editorial_roles(roles, grid, grid_sha256=grid_sha256)
    validate_reaction_intervals(reactions)
    if roles["source_id"] != grid["source_id"] or reactions["source_id"] != grid["source_id"]:
        raise ValueError("reaction-view-gain sources must match")
    if not isinstance(config, Mapping) or set(config) != {
        "schema_version", "config_id", "reviewer_kind", "adapter_id", "decisions",
    } or config["schema_version"] != CONFIG_SCHEMA:
        raise ValueError("reaction-view-gain config is invalid")
    if config["reviewer_kind"] not in {"human", "local_vlm"}:
        raise ValueError("reaction-view-gain reviewer is invalid")
    for value, label in ((config["config_id"], "config_id"), (config["adapter_id"], "adapter_id")):
        if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
            raise ValueError(f"{label} must be privacy-safe")
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None for value in (
        config_sha256, grid_sha256, roles_sha256, reactions_sha256,
    )):
        raise ValueError("reaction-view-gain checksums are invalid")
    assignments = {item["role"]: item["candidate_id"] for item in roles["assignments"]}
    current = assignments["primary_performance"]
    proposed = assignments["audience_reaction"]
    event_keys = {
        (float(item["start_seconds"]), float(item["end_seconds"]))
        for item in reactions["intervals"]
    }
    rows = config["decisions"]
    if not isinstance(rows, list):
        raise ValueError("reaction-view-gain decisions must be an array")
    seen = set()
    decisions = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {
            "reaction_start_seconds", "reaction_end_seconds", "decision",
        }:
            raise ValueError("reaction-view-gain decision fields are invalid")
        start, end = row["reaction_start_seconds"], row["reaction_end_seconds"]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or
               not math.isfinite(value) for value in (start, end)):
            raise ValueError("reaction-view-gain timing must be finite")
        key = (float(start), float(end))
        if key not in event_keys or key in seen or row["decision"] not in DECISIONS:
            raise ValueError("reaction-view-gain must uniquely reference a declared event")
        seen.add(key)
        decisions.append({
            "reaction_start_seconds": key[0],
            "reaction_end_seconds": key[1],
            "current_candidate_id": current,
            "proposed_candidate_id": proposed,
            "decision": row["decision"],
        })
    decisions.sort(key=lambda item: (item["reaction_start_seconds"], item["reaction_end_seconds"]))
    return {
        "schema_version": SCHEMA,
        "source_id": grid["source_id"],
        "window": dict(grid["window"]),
        "inputs": {
            "context_view_grid_sha256": grid_sha256,
            "editorial_roles_sha256": roles_sha256,
            "reaction_intervals_sha256": reactions_sha256,
            "config_sha256": config_sha256,
        },
        "provenance": {
            "reviewer_kind": config["reviewer_kind"],
            "adapter_id": config["adapter_id"],
            "config_id": config["config_id"],
        },
        "decisions": decisions,
        "default_decision": "abstain",
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_names": False, "contains_identity": False,
            "contains_free_text": False,
        },
        "limitations": [
            "relative gain is bounded editorial evidence, not identity or reaction-source proof",
            "unreviewed reaction intervals abstain and cannot authorize a cut",
        ],
    }


def validate_reaction_view_gain(
    document: Mapping[str, object], grid: Mapping[str, object],
    roles: Mapping[str, object], reactions: Mapping[str, object], *,
    grid_sha256: str, roles_sha256: str, reactions_sha256: str,
) -> None:
    if not isinstance(document, Mapping) or set(document) != {
        "schema_version", "source_id", "window", "inputs", "provenance",
        "decisions", "default_decision", "privacy", "limitations",
    } or document["schema_version"] != SCHEMA:
        raise ValueError("reaction-view-gain fields or schema are invalid")
    inputs = document["inputs"]
    provenance = document["provenance"]
    if not isinstance(inputs, Mapping) or set(inputs) != {
        "context_view_grid_sha256", "editorial_roles_sha256",
        "reaction_intervals_sha256", "config_sha256",
    } or not isinstance(provenance, Mapping) or set(provenance) != {
        "reviewer_kind", "adapter_id", "config_id",
    }:
        raise ValueError("reaction-view-gain bindings are invalid")
    if not isinstance(document["decisions"], list) or any(
        not isinstance(item, Mapping) for item in document["decisions"]
    ):
        raise ValueError("reaction-view-gain decisions must be an array of objects")
    config = {
        "schema_version": CONFIG_SCHEMA,
        "config_id": provenance["config_id"],
        "reviewer_kind": provenance["reviewer_kind"],
        "adapter_id": provenance["adapter_id"],
        "decisions": [{
            "reaction_start_seconds": item.get("reaction_start_seconds"),
            "reaction_end_seconds": item.get("reaction_end_seconds"),
            "decision": item.get("decision"),
        } for item in document["decisions"]],
    }
    expected = build_reaction_view_gain(
        config, grid, roles, reactions,
        config_sha256=inputs.get("config_sha256", ""),
        grid_sha256=grid_sha256, roles_sha256=roles_sha256,
        reactions_sha256=reactions_sha256,
    )
    if document != expected:
        raise ValueError("reaction view gain must exactly bind its evidence")
