"""Private schedule and neutral public index for structural blind review."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from fractions import Fraction
from typing import Mapping


CONFIG_SCHEMA = "aegis360.structural-chapter-blind-schedule-config.v1"
PRIVATE_SCHEMA = "aegis360.structural-chapter-blind-schedule.private.v1"
PUBLIC_SCHEMA = "aegis360.structural-chapter-blind-review-index.public.v1"
PROOF_SCHEMA = "aegis360.structural-chapter-blind-selection-proof.v1"
CONFIG_SHA256 = "3964162f0cb99bf9959cee1b19bef9fd041a04a76dfae9085052c9babb30d8ba"
CANONICAL_CONFIG_SHA256 = "83fbf667236497dc09d1d5409b5f2ae28140b858e8aaf95c318c8745afe1837a"
PROOF_SHA256 = "ad6f29b1cf34374ad3130afa3bd2535ac81676fdb4300a2891fb5c6c8712a567"
SHA = re.compile(r"^[0-9a-f]{64}$")
OPAQUE = re.compile(r"^(packet|review)-[0-9a-f]{20}$")
AUTHORITY = {"review_scheduling": True, "semantic_labels": False,
             "story_boundaries": False, "camera_commands": False,
             "render_commands": False}


def _canonical_hash(value: Mapping[str, object]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_schedule_config(config: Mapping[str, object]) -> None:
    if (not isinstance(config, Mapping)
            or config.get("schema_version") != CONFIG_SCHEMA
            or _canonical_hash(config) != CANONICAL_CONFIG_SHA256):
        raise ValueError("structural blind schedule config is invalid")


def _fraction(value: object) -> Fraction:
    if (not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}
            or type(value.get("numerator")) is not int
            or type(value.get("denominator")) is not int
            or value["denominator"] <= 0):
        raise ValueError("selection center rational is invalid")
    result = Fraction(value["numerator"], value["denominator"])
    if (result.numerator != value["numerator"]
            or result.denominator != value["denominator"]):
        raise ValueError("selection center rational must be reduced")
    return result


def _rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _validate_proof(proof: Mapping[str, object], config: Mapping[str, object]):
    if (not isinstance(proof, Mapping)
            or set(proof) != {"schema_version", "source_id", "inputs",
                              "selection_policy", "universe", "selected",
                              "authority", "privacy", "limitations"}
            or proof.get("schema_version") != PROOF_SCHEMA
            or proof.get("source_id") != "old_ghost_road_360"
            or proof.get("inputs", {}).get("config_sha256")
               != "c4a1f411e26de8061c46f49e7db43474b4aeb75839d7d7f140cc38bd5df2e6cb"
            or proof.get("selection_policy", {}).get("packet_cap") != 8
            or not isinstance(proof.get("universe"), list)
            or len(proof["universe"]) != 26
            or not isinstance(proof.get("selected"), list)
            or len(proof["selected"]) != 8
            or proof.get("authority") != {"semantic_label": False,
                 "story_boundary": False, "camera_choice": False, "render": False}
            or proof.get("privacy") != {"contains_source_path": False,
                 "contains_pixels": False, "contains_audio": False,
                 "contains_labels": False}):
        raise ValueError("selection proof is invalid for structural scheduling")
    selected_universe = {(row.get("event_id"), row.get("signal_id")): row
                         for row in proof["universe"]
                         if isinstance(row, Mapping) and row.get("disposition") == "selected"}
    if len(selected_universe) != 8:
        raise ValueError("selection proof must contain eight selected universe rows")
    result = []
    identities = set(); packet_hashes = set(); digests = set()
    for rank, row in enumerate(proof["selected"], start=1):
        if (not isinstance(row, Mapping)
                or set(row) != {"selection_rank", "event_id", "signal_id",
                                "source_time", "packet_sha256", "selection_digest"}
                or row["selection_rank"] != rank
                or not all(isinstance(row.get(key), str) for key in
                           ("event_id", "signal_id", "packet_sha256", "selection_digest"))
                or SHA.fullmatch(row["packet_sha256"]) is None
                or SHA.fullmatch(row["selection_digest"]) is None):
            raise ValueError("selection proof selected row is invalid")
        center = _fraction(row["source_time"])
        identity = (row["event_id"], row["signal_id"])
        universe = selected_universe.get(identity)
        if (identity in identities or row["packet_sha256"] in packet_hashes
                or row["selection_digest"] in digests or universe is None
                or any(universe.get(key) != row[key] for key in
                       ("source_time", "packet_sha256", "selection_digest", "selection_rank"))):
            raise ValueError("selection proof selected rows do not bind universe")
        identities.add(identity); packet_hashes.add(row["packet_sha256"])
        digests.add(row["selection_digest"]); result.append((row, center))
    return result


def _mac(salt: bytes, value: str) -> str:
    return hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()


def build_structural_blind_schedule(*, selection_proof: Mapping[str, object],
                                    selection_proof_sha256: str,
                                    config: Mapping[str, object],
                                    config_sha256: str,
                                    presentation_salt_hex: str):
    validate_schedule_config(config)
    if (selection_proof_sha256 != PROOF_SHA256
            or selection_proof_sha256 != config["selection"]["selection_proof_sha256"]
            or config_sha256 != CONFIG_SHA256
            or SHA.fullmatch(presentation_salt_hex or "") is None):
        raise ValueError("structural blind schedule lineage is invalid")
    salt = bytes.fromhex(presentation_salt_hex)
    selected = _validate_proof(selection_proof, config)
    rows_config = config["review_rows"]
    cardinals = config["cardinal_candidates"]
    candidates = []
    all_full_macs = set(); all_ids = set()
    for row, center in selected:
        center_text = f"{center.numerator}/{center.denominator}"
        base = (f"{selection_proof_sha256}|{config_sha256}|packet-v1|"
                f"{row['event_id']}|{row['signal_id']}|{row['packet_sha256']}|{center_text}")
        order_mac = _mac(salt, "order|" + base)
        id_mac = _mac(salt, "id|" + base)
        packet_id = "packet-" + id_mac[:20]
        if order_mac in all_full_macs or id_mac in all_full_macs or packet_id in all_ids:
            raise ValueError("structural blind schedule HMAC collision")
        all_full_macs.update((order_mac, id_mac)); all_ids.add(packet_id)
        private_rows = []
        for index, spec in enumerate(rows_config, start=1):
            offset = _fraction(spec["relative_offset_seconds"])
            absolute = center + offset
            if absolute < 0:
                raise ValueError("structural blind schedule row is before source start")
            private_rows.append({"row_number": index, "row_role": spec["row_role"],
                "relative_offset_seconds": _rational(offset),
                "absolute_source_time": _rational(absolute),
                "media_ref": f"media/{packet_id}/row-{index:02d}.png",
                "views": cardinals})
        candidates.append({"packet_id": packet_id, "order_hmac_sha256": order_mac,
            "identifier_hmac_sha256": id_mac, "selection_rank": row["selection_rank"],
            "event_id": row["event_id"], "signal_id": row["signal_id"],
            "lineage_packet_sha256": row["packet_sha256"],
            "selection_digest": row["selection_digest"],
            "absolute_center_time": _rational(center), "rows": private_rows})
    candidates.sort(key=lambda row: (row["order_hmac_sha256"], row["event_id"], row["signal_id"]))
    for ordinal, row in enumerate(candidates, start=1):
        row["presentation_ordinal"] = ordinal
    bundle_mac = _mac(salt, f"bundle|{selection_proof_sha256}|{config_sha256}")
    bundle_id = "review-" + bundle_mac[:20]
    if bundle_mac in all_full_macs or bundle_id in all_ids:
        raise ValueError("structural blind schedule HMAC collision")
    private = {"schema_version": PRIVATE_SCHEMA,
        "source_id": selection_proof["source_id"],
        "inputs": {"selection_proof_sha256": selection_proof_sha256,
                   "schedule_config_sha256": config_sha256,
                   "source_sha256": config["selection"]["source_sha256"]},
        "presentation": {"bundle_id": bundle_id, "bundle_hmac_sha256": bundle_mac,
                         "presentation_salt_sha256": hashlib.sha256(salt).hexdigest(),
                         "algorithm": "HMAC-SHA256"},
        "entries": candidates, "authority": AUTHORITY,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "reviewer_visible": False}}
    public_packets = []
    anonymous = config["public_projection"]["anonymous_views"]
    for entry in candidates:
        public_packets.append({"packet_id": entry["packet_id"],
            "presentation_ordinal": entry["presentation_ordinal"],
            "rows": [{"row_number": row["row_number"], "row_role": row["row_role"],
                      "media_ref": row["media_ref"], "views": anonymous}
                     for row in entry["rows"]]})
    public = {"schema_version": PUBLIC_SCHEMA, "bundle_id": bundle_id,
        "packet_count": 8, "packets": public_packets,
        "questions": config["review"]["questions"],
        "outcomes": config["review"]["outcomes"],
        "classification_consistency": config["review"]["classification_consistency"],
        "privacy": {"contains_source_path": False, "contains_absolute_time": False,
                    "contains_identity": False, "contains_lineage_hash": False,
                    "contains_geometry": False, "contains_score_or_label": False},
        "authority": {"blind_review_input": True, "semantic_labels": False,
                      "story_boundaries": False, "camera_commands": False,
                      "render_commands": False}}
    validate_private_schedule(private)
    validate_public_index(public, config)
    validate_projection(private, public)
    return private, public


def validate_private_schedule(document: Mapping[str, object]) -> None:
    if (not isinstance(document, Mapping)
            or set(document) != {"schema_version", "source_id", "inputs",
                                 "presentation", "entries", "authority", "privacy"}
            or document.get("schema_version") != PRIVATE_SCHEMA
            or document.get("authority") != AUTHORITY
            or document.get("privacy") != {"contains_source_path": False,
                 "contains_pixels": False, "reviewer_visible": False}
            or not isinstance(document.get("entries"), list)
            or len(document["entries"]) != 8):
        raise ValueError("private structural blind schedule is invalid")


def validate_public_index(document: Mapping[str, object], config: Mapping[str, object]) -> None:
    expected_top = {"schema_version", "bundle_id", "packet_count", "packets",
                    "questions", "outcomes", "classification_consistency",
                    "privacy", "authority"}
    if (not isinstance(document, Mapping) or set(document) != expected_top
            or document.get("schema_version") != PUBLIC_SCHEMA
            or OPAQUE.fullmatch(document.get("bundle_id", "")) is None
            or document.get("packet_count") != 8
            or document.get("questions") != config["review"]["questions"]
            or document.get("outcomes") != config["review"]["outcomes"]
            or document.get("classification_consistency") != config["review"]["classification_consistency"]
            or not isinstance(document.get("packets"), list)
            or len(document["packets"]) != 8):
        raise ValueError("public structural blind index is invalid")
    packet_ids = set()
    for ordinal, packet in enumerate(document["packets"], start=1):
        if (not isinstance(packet, Mapping)
                or set(packet) != {"packet_id", "presentation_ordinal", "rows"}
                or OPAQUE.fullmatch(packet.get("packet_id", "")) is None
                or packet["packet_id"] in packet_ids
                or packet.get("presentation_ordinal") != ordinal
                or not isinstance(packet.get("rows"), list)
                or len(packet["rows"]) != 6):
            raise ValueError("public structural blind packet is invalid")
        packet_ids.add(packet["packet_id"])
        for number, (row, role) in enumerate(zip(packet["rows"], config["public_projection"]["row_roles"]), start=1):
            if row != {"row_number": number, "row_role": role,
                       "media_ref": f"media/{packet['packet_id']}/row-{number:02d}.png",
                       "views": config["public_projection"]["anonymous_views"]}:
                raise ValueError("public structural blind row is invalid")
    encoded = json.dumps(document, sort_keys=True)
    forbidden = config["public_projection"]["forbidden_fields"]
    if any(f'"{field}"' in encoded for field in forbidden) or "/" + "/" in encoded:
        raise ValueError("public structural blind index leaks private fields")


def validate_projection(private: Mapping[str, object], public: Mapping[str, object]) -> None:
    expected = [(entry["packet_id"], entry["presentation_ordinal"],
                 [(row["row_role"], row["media_ref"]) for row in entry["rows"]])
                for entry in private["entries"]]
    actual = [(packet["packet_id"], packet["presentation_ordinal"],
               [(row["row_role"], row["media_ref"]) for row in packet["rows"]])
              for packet in public["packets"]]
    if public["bundle_id"] != private["presentation"]["bundle_id"] or actual != expected:
        raise ValueError("public structural blind projection does not match private schedule")


def validate_exact_schedule(private, public, **inputs) -> None:
    expected_private, expected_public = build_structural_blind_schedule(**inputs)
    if private != expected_private or public != expected_public:
        raise ValueError("structural blind schedule must exactly rebuild")
