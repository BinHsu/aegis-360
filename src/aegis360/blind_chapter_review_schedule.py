"""Deterministic private schedule and neutral public index for blind review."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
from fractions import Fraction
from typing import Mapping


CONFIG_SCHEMA = "aegis360.blind-chapter-review-schedule-config.v1"
PRIVATE_SCHEMA = "aegis360.blind-chapter-review-schedule.private.v1"
PUBLIC_SCHEMA = "aegis360.blind-chapter-review-index.public.v1"
PROPOSAL_SCHEMA = "aegis360.chapter-proposal-candidates.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:+-]+$")
ROWS = [
    {"relative_offset_seconds": -30, "row_role": "early_far"},
    {"relative_offset_seconds": -10, "row_role": "early_near"},
    {"relative_offset_seconds": -2, "row_role": "transition_before"},
    {"relative_offset_seconds": 2, "row_role": "transition_after"},
    {"relative_offset_seconds": 10, "row_role": "late_near"},
    {"relative_offset_seconds": 30, "row_role": "late_far"},
]
CARDINAL = [
    {"candidate_id": "context:cardinal:0", "horizontal_fov_degrees": 110.0,
     "order": 0, "pitch_degrees": 0.0, "yaw_degrees": 0.0},
    {"candidate_id": "context:cardinal:1", "horizontal_fov_degrees": 110.0,
     "order": 1, "pitch_degrees": 0.0, "yaw_degrees": 90.0},
    {"candidate_id": "context:cardinal:2", "horizontal_fov_degrees": 110.0,
     "order": 2, "pitch_degrees": 0.0, "yaw_degrees": -180.0},
    {"candidate_id": "context:cardinal:3", "horizontal_fov_degrees": 110.0,
     "order": 3, "pitch_degrees": 0.0, "yaw_degrees": -90.0},
]
HARD_NEGATIVES = [76.75, 327.25, 386.5, 429.75, 499.75, 506.25, 565.25]
AUTHORITY = {
    "review_scheduling": True, "semantic_labels": False,
    "story_boundaries": False, "candidate_selection": False,
    "camera_commands": False, "render_commands": False,
}
QUESTIONS = [
    "What visibly persists across the early rows?",
    "What visibly persists across the late rows?",
    "What, if anything, changes between those two sustained states?",
    "Is the difference an activity/context change, ordinary continuous movement, a near-object or projection effect, or not distinguishable from this packet?",
    "Is the evidence sufficient to make a closed observation without identity, intent, causality or speech claims?",
]
OUTCOMES = ["story_change", "capture_artifact", "no_semantic_change", "abstain"]
PUBLIC_VIEWS = [
    {"view_id": "view:00", "layout_position": "top_left"},
    {"view_id": "view:01", "layout_position": "top_right"},
    {"view_id": "view:02", "layout_position": "bottom_left"},
    {"view_id": "view:03", "layout_position": "bottom_right"},
]


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and SHA256.fullmatch(value) is not None


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def validate_schedule_config(config: Mapping[str, object]) -> None:
    expected = {"schema_version", "config_id", "control_lattice",
                "control_order_string", "proposal_minimum_separation_seconds",
                "control_minimum_separation_seconds",
                "hard_negative_minimum_separation_seconds",
                "hard_negative_proxy_times_seconds", "control_count",
                "maximum_proposals",
                "neutral_order_string", "review_rows", "cardinal_candidates"}
    invalid = (
        not isinstance(config, Mapping) or set(config) != expected
        or config.get("schema_version") != CONFIG_SCHEMA
        or config.get("config_id") != "skiing-blind-chapter-review-schedule-v1"
        or config.get("control_lattice") != {
            "start_seconds": 30, "end_seconds": 580, "step_seconds": 10}
        or config.get("control_order_string") !=
        "source_sha256|proposal_policy_sha256|protocol_sha256|control-v1|timestamp-one-decimal"
        or config.get("proposal_minimum_separation_seconds") != 45
        or config.get("control_minimum_separation_seconds") != 45
        or config.get("hard_negative_minimum_separation_seconds") != 30
        or config.get("hard_negative_proxy_times_seconds") != HARD_NEGATIVES
        or config.get("control_count") != 3
        or config.get("maximum_proposals") != 6
        or config.get("neutral_order_string") !=
        "HMAC-SHA256(private-256-bit-salt,domain|source_sha256|proposal_policy_sha256|protocol_sha256|packet-v1|role|timestamp-one-decimal)"
        or config.get("review_rows") != ROWS
        or config.get("cardinal_candidates") != CARDINAL
    )
    if invalid:
        raise ValueError("blind chapter-review schedule config is invalid")


def _validate_proposals(document: Mapping[str, object], policy_sha256: str):
    top = {"schema_version", "source_id", "inputs", "policy", "candidates",
           "privacy", "authority", "limitations"}
    if not isinstance(document, Mapping) or set(document) != top:
        raise ValueError("chapter proposals must match the closed schema")
    inputs, policy, candidates = document["inputs"], document["policy"], document["candidates"]
    policy_keys = {"config_id", "eligible_center_count", "score_median", "score_mad",
                   "mad_zero", "emission_threshold", "threshold_comparison",
                   "local_maximum_radius_seconds", "local_plateau_rule",
                   "minimum_temporal_separation_seconds", "maximum_candidates",
                   "selection_rule", "dominant_family_diversity_rule",
                   "local_maxima_audit", "local_maxima_disposition_counts"}
    expected_authority = {"review_candidate_emitted": bool(candidates),
                          "story_boundary": False, "candidate_selected": False,
                          "production_eligible": False, "render": False}
    expected_limitations = [
        "candidates are visual-state review proposals, not semantic chapter labels",
        "fixed support windows cannot propose within 30 seconds of either endpoint",
        "distribution-relative thresholding does not manufacture weak candidates",
    ]
    invalid = (
        document.get("schema_version") != PROPOSAL_SCHEMA
        or not isinstance(document.get("source_id"), str)
        or SAFE_ID.fullmatch(document["source_id"]) is None
        or not isinstance(inputs, Mapping)
        or set(inputs) != {"visual_state_features_sha256", "chapter_proposal_config_sha256"}
        or not all(_is_sha(value) for value in inputs.values())
        or inputs.get("chapter_proposal_config_sha256") != policy_sha256
        or not isinstance(policy, Mapping)
        or set(policy) != policy_keys
        or policy.get("maximum_candidates") != 6
        or policy.get("minimum_temporal_separation_seconds") != 45
        or not isinstance(candidates, list) or not 1 <= len(candidates) <= 6
        or document.get("privacy") != {"contains_source_path": False,
                                       "contains_pixels": False,
                                       "contains_audio": False,
                                       "contains_identity": False}
        or document.get("authority") != expected_authority
        or document.get("limitations") != expected_limitations
    )
    if invalid:
        raise ValueError("chapter proposals are invalid for blind scheduling")
    centers = []
    origins = []
    candidate_keys = {"candidate_id", "center_proxy_time_seconds", "center_source_time",
                      "support_windows", "uncertainty", "family_metrics",
                      "dominant_family", "persistence_adjusted_score"}
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, Mapping) or set(candidate) != candidate_keys:
            raise ValueError("chapter proposal candidate shape is invalid")
        center = _number(candidate["center_proxy_time_seconds"], "proposal center")
        source_time = candidate["center_source_time"]
        if (candidate["candidate_id"] != f"chapter-proposal-{index:02d}"
                or not center.is_integer()
                or not 30 <= center <= 580
                or not isinstance(source_time, Mapping)
                or set(source_time) != {"numerator", "denominator"}
                or any(isinstance(source_time.get(k), bool)
                       or not isinstance(source_time.get(k), int) for k in source_time)
                or source_time["denominator"] <= 0):
            raise ValueError("chapter proposal candidate timing is invalid")
        support = candidate["support_windows"]
        uncertainty = candidate["uncertainty"]
        if (support != {"before_proxy_seconds_half_open": [int(center) - 30,
                                                            int(center) - 10],
                        "after_proxy_seconds_half_open": [int(center) + 10,
                                                           int(center) + 30],
                        "samples_per_window": 20}
                or uncertainty != {"kind": "symmetric-temporal-review-radius",
                                   "radius_seconds": 10}
                or candidate["dominant_family"] not in
                {"global", "spatial_luma", "rgb_histogram"}
                or not 0 <= _number(candidate["persistence_adjusted_score"],
                                    "proposal score") <= 1):
            raise ValueError("chapter proposal evidence contract is invalid")
        _validate_family_metrics(candidate["family_metrics"])
        centers.append(int(center))
        origins.append(Fraction(source_time["numerator"], source_time["denominator"])
                       - int(center))
    if centers != sorted(set(centers)) or any(
            right - left < 45 for left, right in zip(centers, centers[1:])):
        raise ValueError("chapter proposal centers collide or violate separation")
    if len(set(origins)) != 1:
        raise ValueError("chapter proposal affine source origins disagree")
    return centers, origins[0]


def _validate_family_metrics(metrics: object) -> None:
    families = {"global", "spatial_luma", "rgb_histogram"}
    keys = {"state_distance", "before_dispersion", "after_dispersion",
            "dispersion_penalty", "persistence_adjusted_score"}
    if not isinstance(metrics, Mapping) or set(metrics) != families:
        raise ValueError("chapter proposal family metrics are invalid")
    for row in metrics.values():
        if (not isinstance(row, Mapping) or set(row) != keys
                or any(not 0 <= _number(value, "family metric") <= 1
                       for value in row.values())):
            raise ValueError("chapter proposal family metrics are invalid")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hmac(salt: bytes, value: str) -> str:
    return hmac.new(salt, value.encode("utf-8"), hashlib.sha256).hexdigest()


def _stamp(value: int | float) -> str:
    return f"{value:.1f}"


def _source_time(origin: Fraction, proxy_time: int) -> dict[str, int]:
    value = origin + proxy_time
    return {"numerator": value.numerator, "denominator": value.denominator}


def build_blind_chapter_review_schedule(
    *, proposals: Mapping[str, object], proposals_sha256: str,
    source_sha256: str, policy_sha256: str, protocol_sha256: str,
    config: Mapping[str, object], config_sha256: str,
    presentation_salt_hex: str,
) -> tuple[dict[str, object], dict[str, object]]:
    validate_schedule_config(config)
    if not all(_is_sha(value) for value in (
            proposals_sha256, source_sha256, policy_sha256,
            protocol_sha256, config_sha256)):
        raise ValueError("blind schedule proof hashes are invalid")
    if (not isinstance(presentation_salt_hex, str)
            or SHA256.fullmatch(presentation_salt_hex) is None):
        raise ValueError("presentation salt must be a private 256-bit lowercase hex value")
    salt = bytes.fromhex(presentation_salt_hex)
    centers, origin = _validate_proposals(proposals, policy_sha256)
    prefix = f"{source_sha256}|{policy_sha256}|{protocol_sha256}"
    lattice = range(30, 581, 10)
    ordered = sorted(lattice, key=lambda timestamp: (
        _digest(f"{prefix}|control-v1|{_stamp(timestamp)}"), timestamp))
    controls = []
    for timestamp in ordered:
        if (all(abs(timestamp - proposal) >= 45 for proposal in centers)
                and all(abs(timestamp - control) >= 45 for control in controls)
                and all(abs(timestamp - negative) >= 30 for negative in HARD_NEGATIVES)):
            controls.append(timestamp)
            if len(controls) == 3:
                break
    if len(controls) != 3:
        raise ValueError("frozen lattice cannot supply three separated controls")
    entries = ([{"private_role": "proposal", "proposal_id": candidate["candidate_id"],
                 "absolute_proxy_time_seconds": center}
                for candidate, center in zip(proposals["candidates"], centers)]
               + [{"private_role": "control", "proposal_id": None,
                   "absolute_proxy_time_seconds": timestamp} for timestamp in controls])
    for entry in entries:
        seed = (f"{prefix}|packet-v1|{entry['private_role']}|"
                f"{_stamp(entry['absolute_proxy_time_seconds'])}")
        entry["presentation_hmac_sha256"] = _hmac(salt, f"order|{seed}")
        entry["packet_id"] = "packet-" + _hmac(salt, f"id|{seed}")[:20]
    digests = [entry["presentation_hmac_sha256"] for entry in entries]
    packet_ids = [entry["packet_id"] for entry in entries]
    if len(set(digests)) != len(digests):
        raise ValueError("neutral packet digest collision")
    if len(set(packet_ids)) != len(packet_ids):
        raise ValueError("neutral packet identifier collision")
    entries.sort(key=lambda entry: entry["presentation_hmac_sha256"])
    for index, entry in enumerate(entries, start=1):
        entry["presentation_ordinal"] = index
        entry["absolute_source_time"] = _source_time(
            origin, entry["absolute_proxy_time_seconds"])
        entry["rows"] = []
        for row_index, row in enumerate(ROWS, start=1):
            proxy_time = entry["absolute_proxy_time_seconds"] + row["relative_offset_seconds"]
            entry["rows"].append({
                **row,
                "absolute_proxy_time_seconds": proxy_time,
                "absolute_source_time": _source_time(origin, proxy_time),
                "media_ref": f"media/{entry['packet_id']}/row-{row_index:02d}.png",
                "cardinal_mapping": [dict(candidate) for candidate in CARDINAL],
            })
    private = {
        "schema_version": PRIVATE_SCHEMA,
        "source_id": proposals["source_id"],
        "inputs": {"chapter_proposals_sha256": proposals_sha256,
                   "source_sha256": source_sha256,
                   "proposal_policy_sha256": policy_sha256,
                   "protocol_sha256": protocol_sha256,
                   "schedule_config_sha256": config_sha256},
        "selection_proof": {"ordered_lattice_sha256": _digest(
            "|".join(_stamp(timestamp) for timestamp in ordered)),
            "selected_control_count": 3,
            "proposal_count": len(centers),
            "presentation_salt_sha256": hashlib.sha256(salt).hexdigest(),
            "presentation_algorithm": "HMAC-SHA256-sort-then-opaque-id-v1"},
        "entries": entries,
        "authority": dict(AUTHORITY),
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "reviewer_visible": False},
    }
    packets = [{"packet_id": entry["packet_id"],
                "presentation_ordinal": entry["presentation_ordinal"],
                "rows": [{"row_role": row["row_role"],
                           "media_ref": row["media_ref"], "missing": False,
                           "views": [dict(view) for view in PUBLIC_VIEWS]}
                          for row in entry["rows"]]}
               for entry in entries]
    bundle_id = "review-" + _hmac(salt, f"bundle|{prefix}|{proposals_sha256}")[:20]
    public = {"schema_version": PUBLIC_SCHEMA, "bundle_id": bundle_id,
              "packets": packets,
              "review_form": {"outcomes": list(OUTCOMES),
                              "questions": list(QUESTIONS)},
              "privacy": {"contains_absolute_time": False,
                          "contains_signal_evidence": False,
                          "contains_proposal_or_control_role": False,
                          "contains_proof_hash": False,
                          "contains_cardinal_geometry": False},
              "authority": dict(AUTHORITY)}
    validate_private_schedule(private)
    validate_public_reviewer_index(public)
    validate_schedule_projection(private, public)
    return private, public


def validate_private_schedule(document: Mapping[str, object]) -> None:
    if (not isinstance(document, Mapping)
            or set(document) != {"schema_version", "source_id", "inputs",
                                 "selection_proof", "entries", "authority", "privacy"}
            or document.get("schema_version") != PRIVATE_SCHEMA
            or not isinstance(document.get("source_id"), str)
            or SAFE_ID.fullmatch(document["source_id"]) is None
            or not isinstance(document.get("inputs"), Mapping)
            or set(document["inputs"]) != {"chapter_proposals_sha256", "source_sha256",
                                           "proposal_policy_sha256", "protocol_sha256",
                                           "schedule_config_sha256"}
            or not all(_is_sha(value) for value in document["inputs"].values())
            or document.get("authority") != AUTHORITY
            or document.get("privacy") != {"contains_source_path": False,
                                            "contains_pixels": False,
                                            "reviewer_visible": False}):
        raise ValueError("private blind schedule is invalid")
    proof = document["selection_proof"]
    entries = document["entries"]
    if (not isinstance(proof, Mapping)
            or set(proof) != {"ordered_lattice_sha256", "selected_control_count",
                              "proposal_count", "presentation_salt_sha256",
                              "presentation_algorithm"}
            or not _is_sha(proof["ordered_lattice_sha256"])
            or not _is_sha(proof["presentation_salt_sha256"])
            or proof["presentation_algorithm"] !=
            "HMAC-SHA256-sort-then-opaque-id-v1"
            or not isinstance(entries, list)
            or len(entries) != proof["selected_control_count"] + proof["proposal_count"]
            or type(proof["selected_control_count"]) is not int
            or type(proof["proposal_count"]) is not int
            or proof["selected_control_count"] != 3
            or not 1 <= proof["proposal_count"] <= 6):
        raise ValueError("private blind schedule proof is invalid")
    entry_keys = {"private_role", "proposal_id", "absolute_proxy_time_seconds",
                  "presentation_hmac_sha256", "packet_id", "presentation_ordinal",
                  "absolute_source_time", "rows"}
    packet_ids = []
    presentation_digests = []
    proposal_ids = []
    proposal_centers = []
    control_centers = []
    role_counts = {"proposal": 0, "control": 0}
    origins = []
    for index, entry in enumerate(entries, start=1):
        if (not isinstance(entry, Mapping) or set(entry) != entry_keys
                or entry["private_role"] not in {"proposal", "control"}
                or (entry["private_role"] == "control") != (entry["proposal_id"] is None)
                or not _is_sha(entry["presentation_hmac_sha256"])
                or not isinstance(entry["packet_id"], str)
                or re.fullmatch(r"packet-[0-9a-f]{20}", entry["packet_id"]) is None
                or type(entry["presentation_ordinal"]) is not int
                or entry["presentation_ordinal"] != index
                or type(entry["absolute_proxy_time_seconds"]) is not int
                or not isinstance(entry["absolute_source_time"], Mapping)
                or set(entry["absolute_source_time"]) != {"numerator", "denominator"}
                or not isinstance(entry["rows"], list) or len(entry["rows"]) != 6):
            raise ValueError("private blind schedule entry is invalid")
        packet_ids.append(entry["packet_id"])
        presentation_digests.append(entry["presentation_hmac_sha256"])
        role_counts[entry["private_role"]] += 1
        if entry["private_role"] == "proposal":
            if (not isinstance(entry["proposal_id"], str)
                    or re.fullmatch(r"chapter-proposal-[0-9]{2}", entry["proposal_id"]) is None):
                raise ValueError("private proposal mapping is invalid")
            proposal_ids.append(entry["proposal_id"])
            proposal_centers.append(entry["absolute_proxy_time_seconds"])
        else:
            control_centers.append(entry["absolute_proxy_time_seconds"])
        source_time = entry["absolute_source_time"]
        if (any(isinstance(source_time.get(k), bool)
                or not isinstance(source_time.get(k), int) for k in source_time)
                or source_time["denominator"] <= 0):
            raise ValueError("private source timestamp is invalid")
        origin = Fraction(source_time["numerator"], source_time["denominator"])
        origin -= entry["absolute_proxy_time_seconds"]
        origins.append(origin)
        private_row_keys = {"relative_offset_seconds", "row_role",
                            "absolute_proxy_time_seconds", "absolute_source_time",
                            "media_ref", "cardinal_mapping"}
        for expected_row, row in zip(ROWS, entry["rows"]):
            if (not isinstance(row, Mapping) or set(row) != private_row_keys
                    or row["relative_offset_seconds"] != expected_row["relative_offset_seconds"]
                    or row["row_role"] != expected_row["row_role"]
                    or row["absolute_proxy_time_seconds"] !=
                    entry["absolute_proxy_time_seconds"] + row["relative_offset_seconds"]
                    or row["cardinal_mapping"] != CARDINAL
                    or row["media_ref"] !=
                    f"media/{entry['packet_id']}/row-{ROWS.index(expected_row)+1:02d}.png"):
                raise ValueError("private blind schedule row is invalid")
            row_source = row["absolute_source_time"]
            if (not isinstance(row_source, Mapping)
                    or set(row_source) != {"numerator", "denominator"}
                    or any(isinstance(row_source.get(k), bool)
                           or not isinstance(row_source.get(k), int) for k in row_source)
                    or row_source["denominator"] <= 0
                    or Fraction(row_source["numerator"], row_source["denominator"])
                    != origin + row["absolute_proxy_time_seconds"]):
                raise ValueError("private review-row source timestamp is invalid")
    prefix = (f"{document['inputs']['source_sha256']}|"
              f"{document['inputs']['proposal_policy_sha256']}|"
              f"{document['inputs']['protocol_sha256']}")
    ordered_lattice = sorted(range(30, 581, 10), key=lambda timestamp: (
        _digest(f"{prefix}|control-v1|{_stamp(timestamp)}"), timestamp))
    expected_controls = []
    for timestamp in ordered_lattice:
        if (all(abs(timestamp - proposal) >= 45 for proposal in proposal_centers)
                and all(abs(timestamp - control) >= 45 for control in expected_controls)
                and all(abs(timestamp - negative) >= 30 for negative in HARD_NEGATIVES)):
            expected_controls.append(timestamp)
            if len(expected_controls) == 3:
                break
    if (presentation_digests != sorted(presentation_digests)
            or len(set(presentation_digests)) != len(entries)
            or len(set(packet_ids)) != len(entries)
            or role_counts != {"proposal": proof["proposal_count"], "control": 3}
            or sorted(proposal_ids) != [f"chapter-proposal-{index:02d}"
                                        for index in range(1, len(proposal_ids) + 1)]
            or len(set(origins)) != 1
            or any(right - left < 45 for left, right in
                   zip(sorted(proposal_centers), sorted(proposal_centers)[1:]))
            or sorted(control_centers) != sorted(expected_controls)
            or proof["ordered_lattice_sha256"] != _digest(
                "|".join(_stamp(timestamp) for timestamp in ordered_lattice))):
        raise ValueError("private blind schedule neutral order is invalid")


def validate_public_reviewer_index(document: Mapping[str, object]) -> None:
    if (not isinstance(document, Mapping)
            or set(document) != {"schema_version", "bundle_id", "packets",
                                 "review_form", "privacy", "authority"}
            or document.get("schema_version") != PUBLIC_SCHEMA
            or not isinstance(document.get("bundle_id"), str)
            or re.fullmatch(r"review-[0-9a-f]{20}", document["bundle_id"]) is None
            or document.get("authority") != AUTHORITY
            or document.get("review_form") != {"outcomes": OUTCOMES,
                                                "questions": QUESTIONS}
            or document.get("privacy") != {"contains_absolute_time": False,
                                            "contains_signal_evidence": False,
                                            "contains_proposal_or_control_role": False,
                                            "contains_proof_hash": False,
                                            "contains_cardinal_geometry": False}
            or not isinstance(document.get("packets"), list)
            or not 4 <= len(document["packets"]) <= 9):
        raise ValueError("public blind reviewer index is invalid")
    packet_ids = []
    for index, packet in enumerate(document["packets"], start=1):
        if (not isinstance(packet, Mapping)
                or set(packet) != {"packet_id", "presentation_ordinal", "rows"}
                or re.fullmatch(r"packet-[0-9a-f]{20}", packet["packet_id"]) is None
                or packet["presentation_ordinal"] != index
                or not isinstance(packet["rows"], list) or len(packet["rows"]) != 6):
            raise ValueError("public blind reviewer packet is invalid")
        for expected, row in zip(ROWS, packet["rows"]):
            if (not isinstance(row, Mapping)
                    or set(row) != {"row_role", "media_ref", "missing", "views"}
                    or row["row_role"] != expected["row_role"]
                    or row["missing"] is not False
                    or row["views"] != PUBLIC_VIEWS):
                raise ValueError("public blind reviewer row is invalid")
            reference = row["media_ref"]
            if (not isinstance(reference, str) or not reference
                    or reference.startswith(("/", "~")) or "\\" in reference
                    or any(part in {"", ".", ".."} for part in reference.split("/"))
                    or reference != f"media/{packet['packet_id']}/row-{ROWS.index(expected)+1:02d}.png"):
                raise ValueError("public artifact reference must be safe and neutral")
        packet_ids.append(packet["packet_id"])
    if len(set(packet_ids)) != len(packet_ids):
        raise ValueError("public packet identifiers must be unique")


def validate_schedule_projection(private: Mapping[str, object],
                                 public: Mapping[str, object]) -> None:
    """Prove the public index is exactly the blind projection of private data."""
    validate_private_schedule(private)
    validate_public_reviewer_index(public)
    if len(private["entries"]) != len(public["packets"]):
        raise ValueError("private/public blind packet counts disagree")
    for entry, packet in zip(private["entries"], public["packets"]):
        expected = {"packet_id": entry["packet_id"],
                    "presentation_ordinal": entry["presentation_ordinal"],
                    "rows": [{"row_role": row["row_role"],
                              "media_ref": row["media_ref"], "missing": False,
                              "views": [dict(view) for view in PUBLIC_VIEWS]}
                             for row in entry["rows"]]}
        if packet != expected:
            raise ValueError("public reviewer index is not the exact private projection")


def validate_exact_blind_chapter_review_schedule(
    private: Mapping[str, object], public: Mapping[str, object], *,
    proposals: Mapping[str, object], proposals_sha256: str,
    source_sha256: str, policy_sha256: str, protocol_sha256: str,
    config: Mapping[str, object], config_sha256: str,
    presentation_salt_hex: str,
) -> None:
    """Coordinator-only rebuild check; the private salt never enters artifacts."""
    expected_private, expected_public = build_blind_chapter_review_schedule(
        proposals=proposals, proposals_sha256=proposals_sha256,
        source_sha256=source_sha256, policy_sha256=policy_sha256,
        protocol_sha256=protocol_sha256, config=config,
        config_sha256=config_sha256,
        presentation_salt_hex=presentation_salt_hex)
    if private != expected_private or public != expected_public:
        raise ValueError("blind chapter-review schedule must exactly rebuild from inputs")
