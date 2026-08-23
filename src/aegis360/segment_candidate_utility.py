"""Deterministic candidate utilities from closed segment-view relevance."""

from __future__ import annotations

import math
import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.segment-candidate-utility.v1"
POLICY_SCHEMA = "aegis360.segment-candidate-utility-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def build_segment_candidate_utility(
    relevance: Mapping[str, object], grid: Mapping[str, object],
    policy: Mapping[str, object], *, relevance_sha256: str,
    grid_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    """Map one segment's closed observations to explainable numeric utility."""

    validate_context_view_grid(grid)
    if any(
        not isinstance(value, str) or SHA256.fullmatch(value) is None
        for value in (relevance_sha256, grid_sha256, policy_sha256)
    ):
        raise ValueError("segment-candidate utility checksums are invalid")
    if (
        relevance.get("schema_version") != "aegis360.segment-view-relevance.v1"
        or relevance.get("source_id") != grid.get("source_id")
    ):
        raise ValueError("segment-candidate utility lineage is invalid")

    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    required_policy = {
        "schema_version", "policy_id", "relevance_weights",
        "visibility_weights", "temporal_weights",
    }
    if (
        not isinstance(policy, Mapping) or set(policy) != required_policy
        or policy.get("schema_version") != POLICY_SCHEMA
        or not isinstance(policy.get("policy_id"), str) or not policy["policy_id"]
    ):
        raise ValueError("segment-candidate utility policy is invalid")
    expected_labels = {
        "relevance_weights": {"primary", "supporting", "low", "unrelated"},
        "visibility_weights": {"clear", "partial", "obstructed"},
        "temporal_weights": {"stable", "changing"},
    }
    for key, labels in expected_labels.items():
        weights = policy[key]
        if (
            not isinstance(weights, Mapping) or set(weights) != labels
            or any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in weights.values()
            )
        ):
            raise ValueError("segment-candidate utility weights are invalid")

    evidence = relevance.get("evidence")
    if not isinstance(evidence, Mapping) or set(evidence) != {
        "status", "candidate_observations",
    }:
        raise ValueError("segment-candidate relevance evidence is invalid")
    status = evidence["status"]
    observations = evidence["candidate_observations"]
    if status == "abstain":
        if observations != []:
            raise ValueError("segment-candidate abstention cannot carry claims")
        by_id: dict[str, Mapping[str, object]] = {}
    elif status == "observed":
        if (
            not isinstance(observations, list)
            or [item.get("candidate_id") for item in observations
                if isinstance(item, Mapping)] != candidate_ids
        ):
            raise ValueError("segment observations must match context-grid order")
        by_id = {item["candidate_id"]: item for item in observations}
        allowed = {
            "visibility": expected_labels["visibility_weights"],
            "segment_relevance": expected_labels["relevance_weights"],
            "temporal_consistency": expected_labels["temporal_weights"],
        }
        for item in observations:
            if (
                not isinstance(item, Mapping)
                or set(item) != {"candidate_id", *allowed}
                or any(item[field] not in labels for field, labels in allowed.items())
            ):
                raise ValueError("segment candidate observation is invalid")
    else:
        raise ValueError("segment-candidate relevance status is invalid")

    utilities = []
    for candidate_id in candidate_ids:
        eligible = status == "observed"
        components = {
            "segment_relevance": 0.0,
            "visibility": 0.0,
            "temporal_consistency": 0.0,
        }
        if status == "observed":
            observation = by_id[candidate_id]
            components = {
                "segment_relevance": float(policy["relevance_weights"][observation["segment_relevance"]]),
                "visibility": float(policy["visibility_weights"][observation["visibility"]]),
                "temporal_consistency": float(policy["temporal_weights"][observation["temporal_consistency"]]),
            }
        utilities.append({
            "candidate_id": candidate_id,
            "eligible": eligible,
            "components": components,
            "total": float(sum(components.values())),
        })

    return {
        "schema_version": SCHEMA,
        "source_id": grid["source_id"],
        "segment_id": relevance["segment_id"],
        "inputs": {
            "segment_view_relevance_sha256": relevance_sha256,
            "context_view_grid_sha256": grid_sha256,
            "utility_policy_sha256": policy_sha256,
        },
        "policy_id": policy["policy_id"],
        "evidence_status": status,
        "utilities": utilities,
        "planner_authority": {
            "candidate_selected": False,
            "transition_costs_applied": False,
            "minimum_dwell_applied": False,
        },
        "limitations": [
            "utility components are tunable hypotheses, not calibrated probabilities",
            "abstention exposes no eligible alternative; the planner retains its state",
            "the global planner retains candidate selection and transition authority",
        ],
    }


def validate_segment_candidate_utility(
    document: Mapping[str, object], relevance: Mapping[str, object],
    grid: Mapping[str, object], policy: Mapping[str, object], *,
    relevance_sha256: str, grid_sha256: str, policy_sha256: str,
) -> None:
    expected = build_segment_candidate_utility(
        relevance, grid, policy, relevance_sha256=relevance_sha256,
        grid_sha256=grid_sha256, policy_sha256=policy_sha256,
    )
    if document != expected:
        raise ValueError("segment candidate utility must exactly derive from inputs")
