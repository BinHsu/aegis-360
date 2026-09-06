"""Closed semantic evidence bound to one continuous-onset review packet."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.continuous-onset-semantic-evidence.v1"
CONFIG_SCHEMA = "aegis360.continuous-onset-semantic-evidence-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")


def build_continuous_onset_semantic_evidence(
    config: Mapping[str, object], packet: Mapping[str, object], *,
    config_sha256: str, packet_sha256: str,
) -> dict[str, object]:
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (config_sha256, packet_sha256)):
        raise ValueError("continuous-onset semantic evidence checksums are invalid")
    required = {"schema_version", "reviewer_type", "reviewer_id",
                "reviewer_asset_sha256", "status", "classification",
                "structural_role", "change_type", "narrative_function",
                "viewer_value"}
    if (not isinstance(config, Mapping) or set(config) != required
            or config.get("schema_version") != CONFIG_SCHEMA
            or packet.get("schema_version") !=
            "aegis360.continuous-onset-semantic-packet.v1"
            or packet.get("onset", {}).get("hard_cut_claimed") is not False):
        raise ValueError("continuous-onset semantic evidence input is invalid")
    reviewer_type = config["reviewer_type"]
    reviewer_id = config["reviewer_id"]
    asset = config["reviewer_asset_sha256"]
    if (reviewer_type not in {"human", "agent", "local_model"}
            or not isinstance(reviewer_id, str)
            or SAFE_ID.fullmatch(reviewer_id) is None):
        raise ValueError("continuous-onset reviewer provenance is invalid")
    if reviewer_type == "local_model":
        if not isinstance(asset, str) or SHA256.fullmatch(asset) is None:
            raise ValueError("local onset reviewer requires an asset checksum")
    elif asset is not None:
        raise ValueError("human or agent onset reviewer cannot claim a model asset")
    status = config["status"]
    classification = config["classification"]
    labels = (config["structural_role"], config["change_type"],
              config["narrative_function"], config["viewer_value"])
    if status == "abstain":
        if classification != "unknown" or labels != ("unknown",) * 4:
            raise ValueError("continuous-onset abstention must be wholly unknown")
    elif status == "observed":
        if classification == "story_change":
            if (config["structural_role"] not in {
                    "chapter_boundary", "within_chapter_cut", "ending_transition"}
                    or config["change_type"] not in {
                        "gradual_transition", "motion_peak"}
                    or config["narrative_function"] not in {
                        "establish_context", "action_continuation",
                        "activity_transition", "tension_build", "tension_release",
                        "closing"}
                    or config["viewer_value"] not in {
                        "primary", "supporting", "low"}):
                raise ValueError("story-change onset labels must be complete")
        elif classification in {"capture_artifact", "no_semantic_change"}:
            if labels != ("unknown",) * 4:
                raise ValueError("non-story onset classifications cannot carry labels")
        else:
            raise ValueError("continuous-onset classification is invalid")
    else:
        raise ValueError("continuous-onset semantic status is invalid")
    return {
        "schema_version": SCHEMA, "source_id": packet["source_id"],
        "candidate_id": packet["candidate_id"],
        "inputs": {"continuous_onset_semantic_packet_sha256": packet_sha256,
                   "review_config_sha256": config_sha256},
        "provenance": {"reviewer_type": reviewer_type,
                       "reviewer_id": reviewer_id,
                       "reviewer_asset_sha256": asset},
        "evidence": {"status": status, "classification": classification,
                     "structural_role": config["structural_role"],
                     "change_type": config["change_type"],
                     "narrative_function": config["narrative_function"],
                     "viewer_value": config["viewer_value"],
                     "hard_cut_claimed": False},
        "planner_authority": {"story_boundary_emitted": False,
                              "candidate_selected": False,
                              "renderer_command_emitted": False,
                              "production_eligible": False},
        "privacy": {"contains_timestamp": False, "contains_view": False,
                    "contains_confidence": False, "contains_free_text": False,
                    "contains_identity": False},
        "limitations": ["closed labels are observations, not edit commands",
                        "typed story boundaries remain unimplemented"],
    }


def validate_continuous_onset_semantic_evidence(
    document: Mapping[str, object], config: Mapping[str, object],
    packet: Mapping[str, object], *, config_sha256: str,
    packet_sha256: str,
) -> None:
    expected = build_continuous_onset_semantic_evidence(
        config, packet, config_sha256=config_sha256,
        packet_sha256=packet_sha256,
    )
    if document != expected:
        raise ValueError("continuous-onset semantic evidence must exactly derive from inputs")
