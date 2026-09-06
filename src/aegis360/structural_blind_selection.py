"""Self-proving, label-free selection for structural chapter replication."""

from __future__ import annotations

import hashlib
import re
from fractions import Fraction
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid
from .scene_boundary_story_packet import (
    build_scene_boundary_story_packet, validate_scene_boundary_story_packet,
)


SCHEMA = "aegis360.structural-chapter-blind-selection-proof.v1"
CONFIG_SCHEMA = "aegis360.structural-chapter-blind-selection-config.v1"
CONFIG_SHA256 = "c4a1f411e26de8061c46f49e7db43474b4aeb75839d7d7f140cc38bd5df2e6cb"
TIMELINE_SOURCE_ID = "old_ghost_road_360.webm"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EVENT_ID = re.compile(r"^event:multi:[0-9]{4}$")
SIGNAL_ID = re.compile(r"^event:scene-change:[0-9]{4}$")
LIMITATIONS = [
    "selection is deterministic and label-free but remains within-source",
    "legacy proof packets establish lineage only and are not review packets",
    "selection grants no semantic, boundary, camera, or render authority",
]


def _fraction(value: object) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("signal time is invalid")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        return Fraction(str(value))
    raise ValueError("signal time is invalid")


def _rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def validate_selection_config(config: Mapping[str, object]) -> None:
    if not isinstance(config, Mapping) or set(config) != {
        "schema_version", "config_id", "source", "timeline",
        "proof_packet_contract", "development_exclusion", "selection",
        "descriptor_contract",
    }:
        raise ValueError("structural blind selection config is invalid")
    invalid = (
        config.get("schema_version") != CONFIG_SCHEMA
        or config.get("config_id") != "old-ghost-road-structural-chapter-blind-selection-v1"
        or config.get("source") != {"id": "old_ghost_road_360", "sha256": "4b1264a6c5965742bf70517560dc59a7818c4d9c6e210a260c70d8b19385fafc"}
        or config.get("timeline") != {"expected_scene_signal_count": 26, "event_id_pattern": "event:multi:NNNN", "sha256": "f850a8a54e29d6f828f52b353af536d8a0aec55f67534026fb3d0391281a7ee1", "signal_id_pattern": "event:scene-change:NNNN", "universe": "all-exact-scene-signals-in-timeline"}
        or config.get("proof_packet_contract") != {"context_view_grid_sha256": "26b869dd733a9b201c6a37526d37af7bdd08e4c316fefc650ede7876efbfbf1f", "sampling": {"boundary_offset_seconds": 0.25, "far_context_seconds": 15.0, "maximum_composite_frames": 6, "maximum_source_viewports": 24, "near_context_seconds": 3.0, "policy_id": "exact_scene_signal_six_anchor_cardinal_v1"}}
        or config.get("development_exclusion") != {"comparison": "absolute-distance-strictly-less-than", "minimum_seconds": 8, "times": [{"denominator": 1, "numerator": 53}, {"denominator": 5, "numerator": 423}, {"denominator": 2, "numerator": 327}, {"denominator": 5, "numerator": 842}, {"denominator": 1, "numerator": 222}]}
        or config.get("selection") != {"hash_preimage": "source_sha256|timeline_sha256|structural-blind-replication-v1|event_id|signal_id", "hash_preimage_encoding": "utf-8-no-newline-exact-lowercase-fields", "minimum_selected_separation_comparison": "greater-than-or-equal", "minimum_selected_separation_seconds": 8, "ordered_tie_break": "event-id-then-signal-id-ascending", "packet_count": 8, "require_global_event_signal_pair_uniqueness": True, "require_global_signal_id_uniqueness": True, "rule": "digest-ascending-greedy-stop-at-cap-fail-if-under-cap-no-backfill"}
        or config.get("descriptor_contract") != {"canonical_json": "utf8-ascii-ensure-sorted-keys-compact-no-newline", "subset_fields": ["acquisition", "descriptor", "sample_offsets_seconds", "score"], "subset_sha256": "7f8b05656986030715f226f9c9c33fc375e1afe3e361fc37b54651851a8aa5cd", "source_config_sha256": "8baf66a00a008625cd91292aaa8ac0a8794d9fb20338e0acfab054b3a2f7f7a2"}
    )
    if invalid:
        raise ValueError("structural blind selection config is invalid")


def _scene_universe(timeline: Mapping[str, object], source_id: str) -> list[tuple[str, str, Fraction]]:
    if (not isinstance(timeline, Mapping)
            or timeline.get("schema_version") != "aegis360.event-timeline.v2"
            or timeline.get("source_id") != source_id
            or not isinstance(timeline.get("events"), list)):
        raise ValueError("event timeline is invalid")
    rows = []
    signals = set(); pairs = set()
    for event in timeline["events"]:
        event_id = event.get("event_id") if isinstance(event, Mapping) else None
        if not isinstance(event_id, str) or EVENT_ID.fullmatch(event_id) is None:
            raise ValueError("timeline event ID is invalid")
        for signal in event.get("signals", []):
            if not isinstance(signal, Mapping) or signal.get("signal_type") != "scene_change":
                continue
            signal_id = signal.get("signal_id")
            pair = (event_id, signal_id)
            if (not isinstance(signal_id, str) or SIGNAL_ID.fullmatch(signal_id) is None
                    or signal_id in signals or pair in pairs):
                raise ValueError("scene signal identity is not globally unique")
            try:
                time = _fraction(signal["evidence"]["timestamp_seconds"])
            except (KeyError, TypeError):
                raise ValueError("scene signal time is invalid") from None
            if time < 0:
                raise ValueError("scene signal time is invalid")
            signals.add(signal_id); pairs.add(pair); rows.append((event_id, signal_id, time))
    return rows


def build_selection_proof(*, config: Mapping[str, object], config_sha256: str,
                          timeline: Mapping[str, object], timeline_sha256: str,
                          grid: Mapping[str, object], grid_sha256: str,
                          packets: Sequence[Mapping[str, object]],
                          packet_sha256s: Sequence[str]) -> dict[str, object]:
    validate_selection_config(config)
    validate_context_view_grid(grid)
    if (config_sha256 != CONFIG_SHA256
            or timeline_sha256 != config["timeline"]["sha256"]
            or grid_sha256 != config["proof_packet_contract"]["context_view_grid_sha256"]
            or any(SHA256.fullmatch(value or "") is None for value in
                   (config_sha256, timeline_sha256, grid_sha256))):
        raise ValueError("selection proof lineage checksum is invalid")
    if TIMELINE_SOURCE_ID != f'{config["source"]["id"]}.webm':
        raise ValueError("selection source identity mapping is invalid")
    universe = _scene_universe(timeline, TIMELINE_SOURCE_ID)
    expected_count = config["timeline"]["expected_scene_signal_count"]
    if len(universe) != expected_count or len(packets) != expected_count or len(packet_sha256s) != expected_count:
        raise ValueError("selection proof requires exactly 26 scene packets")
    supplied = {}
    for packet, packet_sha in zip(packets, packet_sha256s):
        if not isinstance(packet, Mapping) or SHA256.fullmatch(packet_sha or "") is None:
            raise ValueError("selection proof packet is invalid")
        key = (packet.get("event_id"), packet.get("signal_id"))
        if key in supplied:
            raise ValueError("selection proof packet is duplicated")
        validate_scene_boundary_story_packet(packet, timeline, grid,
            timeline_sha256=timeline_sha256, grid_sha256=grid_sha256)
        # Do not accept packet-selected policy values: rebuild using the frozen
        # 15/3/.25 contract and require exact identity.
        expected = build_scene_boundary_story_packet(
            timeline, grid, event_id=key[0], signal_id=key[1],
            timeline_sha256=timeline_sha256, grid_sha256=grid_sha256,
            far_context_seconds=15.0, near_context_seconds=3.0,
            boundary_offset_seconds=0.25)
        if packet != expected:
            raise ValueError("selection proof packet violates frozen sampling")
        supplied[key] = packet_sha
    if set(supplied) != {(event, signal) for event, signal, _ in universe}:
        raise ValueError("selection proof packet universe is incomplete")

    source_sha = config["source"]["sha256"]
    excluded_times = [Fraction(item["numerator"], item["denominator"])
                      for item in config["development_exclusion"]["times"]]
    rows = []
    for event_id, signal_id, time in universe:
        preimage = f"{source_sha}|{timeline_sha256}|structural-blind-replication-v1|{event_id}|{signal_id}"
        digest = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
        rows.append({"event_id": event_id, "signal_id": signal_id,
                     "source_time": _rational(time), "packet_sha256": supplied[(event_id, signal_id)],
                     "selection_digest": digest})
    rows.sort(key=lambda row: (row["selection_digest"], row["event_id"], row["signal_id"]))
    selected = []; cap = config["selection"]["packet_count"]
    minimum = Fraction(config["selection"]["minimum_selected_separation_seconds"])
    exclusion = Fraction(config["development_exclusion"]["minimum_seconds"])
    for row in rows:
        time = Fraction(row["source_time"]["numerator"], row["source_time"]["denominator"])
        if any(abs(time - known) < exclusion for known in excluded_times):
            row["disposition"] = "development_excluded"
        elif len(selected) >= cap:
            row["disposition"] = "after_cap"
        elif any(abs(time - Fraction(other["source_time"]["numerator"], other["source_time"]["denominator"])) < minimum for other in selected):
            row["disposition"] = "minimum_separation"
        else:
            row["disposition"] = "selected"
            row["selection_rank"] = len(selected) + 1
            selected.append(row)
    if len(selected) != cap:
        raise ValueError("selection proof cannot fill frozen packet cap")
    selected_output = [{"selection_rank": row["selection_rank"], "event_id": row["event_id"],
                        "signal_id": row["signal_id"], "source_time": row["source_time"],
                        "packet_sha256": row["packet_sha256"],
                        "selection_digest": row["selection_digest"]} for row in selected]
    return {"schema_version": SCHEMA, "source_id": config["source"]["id"],
            "inputs": {"config_sha256": config_sha256,
                       "timeline_sha256": timeline_sha256,
                       "context_view_grid_sha256": grid_sha256},
            "selection_policy": {"universe_count": expected_count,
                                 "packet_cap": cap,
                                 "minimum_separation_seconds": 8,
                                 "development_exclusion_seconds": 8,
                                 "development_exclusion_comparison": "strictly-less-than"},
            "universe": rows, "selected": selected_output,
            "authority": {"semantic_label": False, "story_boundary": False,
                          "camera_choice": False, "render": False},
            "privacy": {"contains_source_path": False, "contains_pixels": False,
                        "contains_audio": False, "contains_labels": False},
            "limitations": LIMITATIONS}


def validate_selection_proof(document: Mapping[str, object], **inputs) -> None:
    if document != build_selection_proof(**inputs):
        raise ValueError("selection proof must exactly derive from inputs")
