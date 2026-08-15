"""Closed semantic observations bound to one sparse event-review packet."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.event-semantic-evidence.v1"
CONFIG_SCHEMA = "aegis360.event-semantic-evidence-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
EVENT_CLASSES = {"audience_reaction", "performance_continuation", "ambient_activity", "unknown"}
RELATIONSHIPS = {"complements_current", "duplicates_current", "unrelated", "unknown"}
VISIBILITY = {"clear", "partial", "obstructed", "unknown"}
RELEVANCE = {"primary", "supporting", "unrelated", "unknown"}
TEMPORAL = {"stable", "changing", "unknown"}


def _packet_candidate_ids(packet: Mapping[str, object]) -> list[str]:
    result = []
    for sample in packet["samples"]:
        for candidate_id in sample["candidate_ids"]:
            if candidate_id not in result:
                result.append(candidate_id)
    return result


def build_event_semantics(
    config: Mapping[str, object], packet: Mapping[str, object], *,
    config_sha256: str, packet_sha256: str,
) -> dict[str, object]:
    if not isinstance(config, Mapping) or set(config) != {
        "schema_version", "adapter_id", "model_id", "model_sha256", "status",
        "event_class", "view_relationship", "candidate_observations",
    } or config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError("event-semantic config is invalid")
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None for value in (
        config_sha256, packet_sha256, config.get("model_sha256"),
    )):
        raise ValueError("event-semantic checksum is invalid")
    if any(
        not isinstance(config.get(key), str) or SAFE_ID.fullmatch(config[key]) is None
        for key in ("adapter_id", "model_id")
    ):
        raise ValueError("event-semantic provenance is invalid")
    if packet.get("schema_version") != "aegis360.event-review-packet.v1":
        raise ValueError("event-semantic packet schema is invalid")
    status = config["status"]
    observations = config["candidate_observations"]
    if status == "abstain":
        if config["event_class"] != "unknown" or config["view_relationship"] != "unknown" or observations != []:
            raise ValueError("abstention cannot carry semantic claims")
    elif status == "observed":
        if config["event_class"] not in EVENT_CLASSES or config["view_relationship"] not in RELATIONSHIPS:
            raise ValueError("event-semantic labels are invalid")
        expected_ids = _packet_candidate_ids(packet)
        if not isinstance(observations, list) or [item.get("candidate_id") for item in observations if isinstance(item, Mapping)] != expected_ids:
            raise ValueError("event-semantic observations must cover packet candidates in order")
        for item in observations:
            if not isinstance(item, Mapping) or set(item) != {
                "candidate_id", "visibility", "event_relevance", "temporal_consistency",
            } or item["visibility"] not in VISIBILITY or item["event_relevance"] not in RELEVANCE or item["temporal_consistency"] not in TEMPORAL:
                raise ValueError("candidate semantic observation is invalid")
    else:
        raise ValueError("event-semantic status is invalid")
    return {
        "schema_version": SCHEMA,
        "source_id": packet["source_id"],
        "event_id": packet["event_id"],
        "inputs": {
            "event_review_packet_sha256": packet_sha256,
            "adapter_config_sha256": config_sha256,
        },
        "provenance": {
            "adapter_id": config["adapter_id"], "model_id": config["model_id"],
            "model_sha256": config["model_sha256"],
        },
        "evidence": {
            "status": status, "event_class": config["event_class"],
            "view_relationship": config["view_relationship"],
            "candidate_observations": observations,
        },
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_audio": False, "contains_names": False,
            "contains_identity": False, "contains_free_text": False,
            "contains_editorial_decision": False,
        },
        "limitations": [
            "semantic evidence is not a camera command or editorial decision",
            "the global planner must combine evidence with chronology and transition costs",
        ],
    }


def validate_event_semantics(
    document: Mapping[str, object], config: Mapping[str, object],
    packet: Mapping[str, object], *, config_sha256: str, packet_sha256: str,
) -> None:
    expected = build_event_semantics(
        config, packet, config_sha256=config_sha256, packet_sha256=packet_sha256,
    )
    if document != expected:
        raise ValueError("event-semantic evidence must exactly bind config and packet")
