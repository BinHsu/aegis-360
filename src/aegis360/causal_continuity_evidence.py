"""Closed narrative associations across adjacent reviewed story segments."""

from __future__ import annotations

import re
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid
from .story_segment_review_packet import validate_story_segment_review_packet


SCHEMA = "aegis360.causal-continuity-evidence.v1"
CONFIG_SCHEMA = "aegis360.causal-continuity-evidence-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
CUES = {"transport_context", "actor_presence", "action_onset",
        "terrain_destination", "environmental_context"}
RELATIONS = {"establishes_expectation", "continues_activity_or_context",
             "reveals_destination", "breaks_established_expectation", "unrelated"}
ASSESSABILITY = {"clear", "partial"}
CUE_MATCH = {"present", "absent"}
PRESERVATION = {"preserves", "partial", "breaks"}


def build_causal_continuity_evidence(
    config: Mapping[str, object], timeline: Mapping[str, object],
    packets: Sequence[Mapping[str, object]], grid: Mapping[str, object], *,
    config_sha256: str, timeline_sha256: str,
    packet_sha256s: Sequence[str], grid_sha256: str,
) -> dict[str, object]:
    """Bind complete adjacent-edge observations without applying utility."""
    validate_context_view_grid(grid)
    hashes = (config_sha256, timeline_sha256, *packet_sha256s, grid_sha256)
    if (len(packets) != len(packet_sha256s)
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in hashes)):
        raise ValueError("causal-continuity checksums are invalid")
    required = {"schema_version", "reviewer_type", "reviewer_id",
                "reviewer_asset_sha256", "edges"}
    if (not isinstance(config, Mapping) or set(config) != required
            or config.get("schema_version") != CONFIG_SCHEMA
            or timeline.get("schema_version") != "aegis360.story-segment-timeline.v1"
            or timeline.get("source_id") != grid.get("source_id")
            or timeline.get("window") != grid.get("window")):
        raise ValueError("causal-continuity inputs are invalid")
    reviewer_type = config["reviewer_type"]
    reviewer_id = config["reviewer_id"]
    asset_sha = config["reviewer_asset_sha256"]
    if (reviewer_type not in {"human", "agent", "local_model"}
            or not isinstance(reviewer_id, str) or SAFE_ID.fullmatch(reviewer_id) is None):
        raise ValueError("causal-continuity provenance is invalid")
    if reviewer_type == "local_model":
        if not isinstance(asset_sha, str) or SHA256.fullmatch(asset_sha) is None:
            raise ValueError("local continuity reviewer requires an asset checksum")
    elif asset_sha is not None:
        raise ValueError("human or agent continuity reviewer cannot claim a model asset")

    segments = timeline.get("segments", [])
    if (not isinstance(segments, list) or len(segments) < 2
            or [packet.get("segment_id") for packet in packets]
            != [segment.get("segment_id") for segment in segments]):
        raise ValueError("continuity packets must cover timeline segments in order")
    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    packet_by_segment = {}
    for packet in packets:
        if (packet.get("schema_version") != "aegis360.story-segment-review-packet.v1"
                or packet.get("source_id") != grid["source_id"]
                or packet.get("inputs", {}).get("story_segment_timeline_sha256") != timeline_sha256
                or packet.get("inputs", {}).get("context_view_grid_sha256") != grid_sha256
                or any(sample.get("candidate_ids") != candidate_ids
                       for sample in packet.get("samples", []))):
            raise ValueError("causal-continuity packet lineage is invalid")
        validate_story_segment_review_packet(
            packet, timeline, grid, segment_timeline_sha256=timeline_sha256,
            grid_sha256=grid_sha256,
        )
        packet_by_segment[packet["segment_id"]] = packet

    expected_pairs = [(left["segment_id"], right["segment_id"])
                      for left, right in zip(segments, segments[1:])]
    edges = config["edges"]
    if (not isinstance(edges, list)
            or [(edge.get("from_segment_id"), edge.get("to_segment_id"))
                for edge in edges if isinstance(edge, Mapping)] != expected_pairs):
        raise ValueError("continuity edges must cover adjacent segments in order")
    durable_edges = []
    for edge in edges:
        required_edge = {"from_segment_id", "to_segment_id", "status",
                         "from_cue", "to_cue", "narrative_relation",
                         "from_support", "to_support", "candidate_observations"}
        if not isinstance(edge, Mapping) or set(edge) != required_edge:
            raise ValueError("causal-continuity edge shape is invalid")
        pair = (edge["from_segment_id"], edge["to_segment_id"])
        if edge["status"] == "abstain":
            if (edge["from_cue"] != "unknown" or edge["to_cue"] != "unknown"
                    or edge["narrative_relation"] != "unknown"
                    or edge["from_support"] != [] or edge["to_support"] != []
                    or edge["candidate_observations"] != []):
                raise ValueError("continuity abstention cannot carry claims")
        elif edge["status"] == "observed":
            if (edge["from_cue"] not in CUES or edge["to_cue"] not in CUES
                    or edge["narrative_relation"] not in RELATIONS):
                raise ValueError("continuity observed labels are invalid")
            for field, segment_id in (("from_support", pair[0]), ("to_support", pair[1])):
                declared = {(sample["sample_id"], sample["timestamp_seconds"])
                            for sample in packet_by_segment[segment_id]["samples"]}
                support = edge[field]
                pairs = [(item.get("sample_id"), item.get("timestamp_seconds"))
                         for item in support if isinstance(item, Mapping)]
                if (not isinstance(support, list) or not support
                        or any(not isinstance(item, Mapping)
                               or set(item) != {"sample_id", "timestamp_seconds"}
                               for item in support)
                        or len(pairs) != len(set(pairs)) or any(item not in declared for item in pairs)):
                    raise ValueError("continuity support must reference declared samples")
            observations = edge["candidate_observations"]
            if (not isinstance(observations, list)
                    or [item.get("candidate_id") for item in observations
                        if isinstance(item, Mapping)] != candidate_ids):
                raise ValueError("continuity observations must cover candidates in grid order")
            for observation in observations:
                if (not isinstance(observation, Mapping)
                        or set(observation) != {"candidate_id", "from_assessability",
                                                "to_assessability", "from_cue_match",
                                                "to_cue_match", "relationship_preservation"}
                        or observation["from_assessability"] not in ASSESSABILITY
                        or observation["to_assessability"] not in ASSESSABILITY
                        or observation["from_cue_match"] not in CUE_MATCH
                        or observation["to_cue_match"] not in CUE_MATCH
                        or (observation["from_cue_match"] == "absent"
                            and observation["from_assessability"] != "clear")
                        or (observation["to_cue_match"] == "absent"
                            and observation["to_assessability"] != "clear")
                        or observation["relationship_preservation"] not in PRESERVATION):
                    raise ValueError("continuity candidate observation is invalid")
        else:
            raise ValueError("causal-continuity edge status is invalid")
        durable_edges.append(dict(edge))

    return {
        "schema_version": SCHEMA, "source_id": grid["source_id"],
        "inputs": {"review_config_sha256": config_sha256,
                   "story_segment_timeline_sha256": timeline_sha256,
                   "story_segment_review_packet_sha256s": list(packet_sha256s),
                   "context_view_grid_sha256": grid_sha256},
        "provenance": {"reviewer_type": reviewer_type, "reviewer_id": reviewer_id,
                       "reviewer_asset_sha256": asset_sha},
        "edges": durable_edges,
        "planner_authority": {"candidate_selected": False,
                              "numeric_utility_applied": False,
                              "transition_costs_applied": False,
                              "renderer_command_emitted": False},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False, "contains_free_text": False,
                    "contains_editorial_decision": False},
        "limitations": [
            "relations are narrative associations, not proven physical causality",
            "candidate observations establish no subject identity or camera choice",
            "cue absence requires a clearly assessable declared sample",
            "abstention is not negative evidence",
        ],
    }


def validate_causal_continuity_evidence(
    document: Mapping[str, object], config: Mapping[str, object],
    timeline: Mapping[str, object], packets: Sequence[Mapping[str, object]],
    grid: Mapping[str, object], *, config_sha256: str,
    timeline_sha256: str, packet_sha256s: Sequence[str], grid_sha256: str,
) -> None:
    expected = build_causal_continuity_evidence(
        config, timeline, packets, grid, config_sha256=config_sha256,
        timeline_sha256=timeline_sha256, packet_sha256s=packet_sha256s,
        grid_sha256=grid_sha256,
    )
    if document != expected:
        raise ValueError("causal continuity evidence must exactly derive from inputs")
