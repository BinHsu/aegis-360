"""Closed story-role observations bound to one scene-story packet."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.scene-story-semantics.v1"
CONFIG_SCHEMA = "aegis360.scene-story-semantics-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
STRUCTURAL_ROLES = {"chapter_boundary", "within_chapter_cut", "ending_transition", "unknown"}
NARRATIVE_FUNCTIONS = {"establish_context", "action_continuation", "activity_transition",
                       "tension_build", "tension_release", "closing", "unknown"}
CHANGE_TYPES = {"hard_cut", "gradual_transition", "motion_peak", "unknown"}
VIEWER_VALUES = {"primary", "supporting", "low", "unknown"}


def build_scene_story_semantics(
    config: Mapping[str, object], packet: Mapping[str, object], *,
    config_sha256: str, packet_sha256: str,
) -> dict[str, object]:
    expected_keys = {"schema_version", "reviewer_type", "reviewer_id",
                     "reviewer_asset_sha256", "status", "structural_role",
                     "narrative_function", "change_type", "viewer_value"}
    if (not isinstance(config, Mapping) or set(config) != expected_keys
            or config.get("schema_version") != CONFIG_SCHEMA
            or packet.get("schema_version") != "aegis360.scene-story-review-packet.v1"):
        raise ValueError("scene-story semantic input is invalid")
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (config_sha256, packet_sha256)):
        raise ValueError("scene-story semantic checksums are invalid")
    reviewer_type = config["reviewer_type"]
    if (reviewer_type not in {"human", "agent", "local_model"}
            or not isinstance(config["reviewer_id"], str)
            or SAFE_ID.fullmatch(config["reviewer_id"]) is None):
        raise ValueError("scene-story reviewer provenance is invalid")
    asset_sha = config["reviewer_asset_sha256"]
    if reviewer_type == "local_model":
        if not isinstance(asset_sha, str) or SHA256.fullmatch(asset_sha) is None:
            raise ValueError("local story model requires an exact asset checksum")
    elif asset_sha is not None:
        raise ValueError("human or agent story review cannot claim a model asset")
    labels = (config["structural_role"], config["narrative_function"],
              config["change_type"], config["viewer_value"])
    if config["status"] == "abstain":
        if labels != ("unknown", "unknown", "unknown", "unknown"):
            raise ValueError("scene-story abstention cannot carry claims")
    elif config["status"] == "observed":
        if (labels[0] not in STRUCTURAL_ROLES or labels[1] not in NARRATIVE_FUNCTIONS
                or labels[2] not in CHANGE_TYPES or labels[3] not in VIEWER_VALUES
                or "unknown" in labels):
            raise ValueError("observed scene-story labels must be closed and complete")
    else:
        raise ValueError("scene-story semantic status is invalid")
    return {
        "schema_version": SCHEMA, "source_id": packet["source_id"],
        "event_id": packet["event_id"],
        "inputs": {"scene_story_review_packet_sha256": packet_sha256,
                   "review_config_sha256": config_sha256},
        "provenance": {"reviewer_type": reviewer_type,
                       "reviewer_id": config["reviewer_id"],
                       "reviewer_asset_sha256": asset_sha},
        "evidence": {"status": config["status"],
                     "structural_role": labels[0],
                     "narrative_function": labels[1],
                     "change_type": labels[2], "viewer_value": labels[3]},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False, "contains_free_text": False,
                    "contains_editorial_decision": False},
        "limitations": [
            "story labels are observations, not camera or cut commands",
            "the global planner must compare all event labels in chronology",
            "agent and human labels are benchmark evidence, not product dependencies",
        ],
    }


def validate_scene_story_semantics(
    document: Mapping[str, object], config: Mapping[str, object],
    packet: Mapping[str, object], *, config_sha256: str, packet_sha256: str,
) -> None:
    expected = build_scene_story_semantics(
        config, packet, config_sha256=config_sha256, packet_sha256=packet_sha256,
    )
    if document != expected:
        raise ValueError("scene-story semantics must exactly bind config and packet")
