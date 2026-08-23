"""Closed candidate observations scoped to one story segment."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.segment-view-relevance.v1"
CONFIG_SCHEMA = "aegis360.segment-view-relevance-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
VISIBILITY = {"clear", "partial", "obstructed", "unknown"}
RELEVANCE = {"primary", "supporting", "low", "unrelated", "unknown"}
CONSISTENCY = {"stable", "changing", "unknown"}


def _candidate_ids(packet: Mapping[str, object]) -> list[str]:
    samples = packet.get("samples", [])
    if not samples:
        return []
    first = samples[0].get("candidate_ids", [])
    if any(sample.get("candidate_ids") != first for sample in samples):
        raise ValueError("segment-view packet candidates must be stable across samples")
    return first


def build_segment_view_relevance(
    config: Mapping[str, object], packet: Mapping[str, object], *,
    config_sha256: str, packet_sha256: str,
) -> dict[str, object]:
    required = {"schema_version", "reviewer_type", "reviewer_id",
                "reviewer_asset_sha256", "status", "candidate_observations"}
    if (not isinstance(config, Mapping) or set(config) != required
            or config.get("schema_version") != CONFIG_SCHEMA
            or packet.get("schema_version") != "aegis360.story-segment-review-packet.v1"):
        raise ValueError("segment-view relevance input is invalid")
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (config_sha256, packet_sha256)):
        raise ValueError("segment-view relevance checksums are invalid")
    reviewer_type = config["reviewer_type"]
    if (reviewer_type not in {"human", "agent", "local_model"}
            or not isinstance(config["reviewer_id"], str)
            or SAFE_ID.fullmatch(config["reviewer_id"]) is None):
        raise ValueError("segment-view reviewer provenance is invalid")
    asset_sha = config["reviewer_asset_sha256"]
    if reviewer_type == "local_model":
        if not isinstance(asset_sha, str) or SHA256.fullmatch(asset_sha) is None:
            raise ValueError("local segment-view model requires an exact checksum")
    elif asset_sha is not None:
        raise ValueError("human or agent segment review cannot claim a model asset")
    observations = config["candidate_observations"]
    if config["status"] == "abstain":
        if observations != []:
            raise ValueError("segment-view abstention cannot carry candidate claims")
    elif config["status"] == "observed":
        expected_ids = _candidate_ids(packet)
        if (not isinstance(observations, list)
                or [item.get("candidate_id") for item in observations
                    if isinstance(item, Mapping)] != expected_ids):
            raise ValueError("segment-view observations must cover candidates in order")
        primary_count = 0
        for item in observations:
            if (not isinstance(item, Mapping)
                    or set(item) != {"candidate_id", "visibility", "segment_relevance",
                                     "temporal_consistency"}
                    or item["visibility"] not in VISIBILITY
                    or item["segment_relevance"] not in RELEVANCE - {"unknown"}
                    or item["temporal_consistency"] not in CONSISTENCY - {"unknown"}):
                raise ValueError("segment-view candidate observation is invalid")
            primary_count += item["segment_relevance"] == "primary"
        if primary_count != 1:
            raise ValueError("observed segment-view evidence requires exactly one primary")
    else:
        raise ValueError("segment-view relevance status is invalid")
    return {
        "schema_version": SCHEMA, "source_id": packet["source_id"],
        "segment_id": packet["segment_id"],
        "inputs": {"story_segment_review_packet_sha256": packet_sha256,
                   "review_config_sha256": config_sha256},
        "provenance": {"reviewer_type": reviewer_type,
                       "reviewer_id": config["reviewer_id"],
                       "reviewer_asset_sha256": asset_sha},
        "evidence": {"status": config["status"],
                     "candidate_observations": observations},
        "planner_authority": {"candidate_selected": False,
                              "transition_costs_applied": False},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False, "contains_free_text": False,
                    "contains_editorial_decision": False},
        "limitations": [
            "candidate observations are segment-scoped and establish no identity",
            "the global planner retains candidate selection and transition authority",
            "agent labels are benchmark evidence, not product-time dependencies",
        ],
    }
