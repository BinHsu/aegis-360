"""Deterministic, explainable utility features from closed event semantics."""

from __future__ import annotations

import math
import re
from typing import Mapping


SCHEMA = "aegis360.event-candidate-utility.v1"
POLICY_SCHEMA = "aegis360.event-utility-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def build_event_candidate_utility(
    semantics: Mapping[str, object], packet: Mapping[str, object],
    policy: Mapping[str, object], *, semantics_sha256: str,
    packet_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None for value in (
        semantics_sha256, packet_sha256, policy_sha256,
    )):
        raise ValueError("event-utility checksums are invalid")
    if semantics.get("schema_version") != "aegis360.event-semantic-evidence.v1" or packet.get("schema_version") != "aegis360.event-review-packet.v1":
        raise ValueError("event-utility inputs are invalid")
    if semantics.get("source_id") != packet.get("source_id") or semantics.get("event_id") != packet.get("event_id") or semantics.get("inputs", {}).get("event_review_packet_sha256") != packet_sha256:
        raise ValueError("event-utility lineage does not match")
    required_policy = {
        "schema_version", "policy_id", "relevance_weights", "visibility_weights",
        "temporal_weights", "relationship_weights",
    }
    if not isinstance(policy, Mapping) or set(policy) != required_policy or policy.get("schema_version") != POLICY_SCHEMA:
        raise ValueError("event-utility policy is invalid")
    expected_labels = {
        "relevance_weights": {"primary", "supporting", "unrelated", "unknown"},
        "visibility_weights": {"clear", "partial", "obstructed", "unknown"},
        "temporal_weights": {"stable", "changing", "unknown"},
        "relationship_weights": {"complements_current", "duplicates_current", "unrelated", "unknown"},
    }
    for key, labels in expected_labels.items():
        weights = policy[key]
        if not isinstance(weights, Mapping) or set(weights) != labels or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in weights.values()
        ):
            raise ValueError("event-utility weights are invalid")

    current_id = packet["event_evidence"]["current_candidate_id"]
    proposed_id = packet["event_evidence"]["proposed_candidate_id"]
    evidence = semantics["evidence"]
    observations = {item["candidate_id"]: item for item in evidence["candidate_observations"]}
    utilities = []
    for candidate_id in (current_id, proposed_id):
        eligible = candidate_id == current_id or evidence["status"] == "observed"
        components = {
            "event_relevance": 0.0,
            "visibility": 0.0,
            "temporal_consistency": 0.0,
            "view_relationship": 0.0,
        }
        if eligible and evidence["status"] == "observed":
            observation = observations[candidate_id]
            components = {
                "event_relevance": float(policy["relevance_weights"][observation["event_relevance"]]),
                "visibility": float(policy["visibility_weights"][observation["visibility"]]),
                "temporal_consistency": float(policy["temporal_weights"][observation["temporal_consistency"]]),
                "view_relationship": float(policy["relationship_weights"][evidence["view_relationship"]]) if candidate_id == proposed_id else 0.0,
            }
        utilities.append({
            "candidate_id": candidate_id, "eligible": eligible,
            "components": components, "total": float(sum(components.values())),
        })
    return {
        "schema_version": SCHEMA,
        "source_id": packet["source_id"], "event_id": packet["event_id"],
        "inputs": {
            "event_semantic_evidence_sha256": semantics_sha256,
            "event_review_packet_sha256": packet_sha256,
            "event_utility_policy_sha256": policy_sha256,
        },
        "policy_id": policy["policy_id"], "utilities": utilities,
        "planner_authority": {
            "candidate_selected": False,
            "transition_costs_applied": False,
            "minimum_dwell_applied": False,
        },
        "limitations": [
            "utility components are tunable POC hypotheses, not calibrated probabilities",
            "the global planner retains selection and transition authority",
        ],
    }
