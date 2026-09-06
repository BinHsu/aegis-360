"""Pure-JSON sanitization from sparse-story private packets to adapter input."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from fractions import Fraction
from typing import Mapping, Sequence


PRIVATE_SCHEMA = "aegis360.sparse-story-private-packet.v1"
PROJECTION_SCHEMA = "aegis360.sparse-story-adapter-projection.v1"
INDEX_SCHEMA = "aegis360.sparse-story-adapter-index.v1"
SAFE = re.compile(r"^[A-Za-z0-9._:+/-]+$")
SHA = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID = re.compile(r"^packet-[0-9a-f]{20}$")
ROLES = ("early_far", "early_near", "transition_before", "transition_after",
         "late_near", "late_far")
OFFSETS = (Fraction(-15), Fraction(-3), Fraction(-1, 4), Fraction(1, 4),
           Fraction(3), Fraction(15))
PRIVATE_PRIVACY = {"contains_source_path": False, "contains_pixels": False,
    "contains_audio": False, "contains_expected_class": False,
    "contains_reviewer_result": False}
PRIVATE_AUTHORITY = {"lineage_input": True, "semantic_observation": False,
    "exact_boundary": False, "chapter_map": False, "camera": False,
    "reorder": False, "render": False}
PUBLIC_PRIVACY = {key: False for key in (
    "contains_source_id", "contains_event_id", "contains_signal",
    "contains_source_time", "contains_position", "contains_proposal_control_role",
    "contains_lineage_hash", "contains_signal_evidence", "contains_score_or_confidence",
    "contains_expected_class", "contains_identity", "contains_real_candidate_id",
    "contains_geometry", "contains_chapter_label", "contains_narrative_function",
    "contains_prose", "contains_edit_request")}
PUBLIC_AUTHORITY = {"semantic_observation_input": True, "exact_boundary": False,
    "chapter_map": False, "camera": False, "reorder": False, "render": False}


def _canonical(document: Mapping[str, object]) -> bytes:
    if not isinstance(document, Mapping):
        raise ValueError("canonical document must be an object")
    try:
        return json.dumps(document, allow_nan=False, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("document is not canonical JSON") from error


def canonical_private_packet_bytes(packet): return _canonical(packet)
def private_packet_sha256(packet): return hashlib.sha256(_canonical(packet)).hexdigest()
def canonical_projection_bytes(projection): return _canonical(projection)
def projection_sha256(projection): return hashlib.sha256(_canonical(projection)).hexdigest()
def canonical_index_bytes(index): return _canonical(index)
def index_sha256(index): return hashlib.sha256(_canonical(index)).hexdigest()


def _rational(value: object) -> Fraction:
    if (not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}
            or type(value.get("numerator")) is not int
            or type(value.get("denominator")) is not int
            or value["denominator"] <= 0):
        raise ValueError("private packet rational is invalid")
    result = Fraction(value["numerator"], value["denominator"])
    if (result.numerator, result.denominator) != (value["numerator"], value["denominator"]):
        raise ValueError("private packet rational must be reduced")
    return result


def _safe(value: object) -> bool:
    return isinstance(value, str) and bool(value) and SAFE.fullmatch(value) is not None


def validate_private_packet(packet: Mapping[str, object]) -> None:
    top = {"schema_version", "source_id", "selection", "inputs",
           "center_source_time", "rows", "privacy", "authority"}
    if (not isinstance(packet, Mapping) or set(packet) != top
            or packet.get("schema_version") != PRIVATE_SCHEMA
            or not _safe(packet.get("source_id"))
            or packet.get("privacy") != PRIVATE_PRIVACY
            or packet.get("authority") != PRIVATE_AUTHORITY):
        raise ValueError("sparse-story private packet is invalid")
    selection, inputs = packet["selection"], packet["inputs"]
    if (not isinstance(selection, Mapping)
            or set(selection) != {"role", "original_event_id", "original_signal_ids"}
            or not isinstance(selection.get("role"), str)
            or selection["role"] not in {"proposal", "control"}
            or not isinstance(selection.get("original_signal_ids"), list)
            or len(selection["original_signal_ids"]) != len(set(
                x for x in selection["original_signal_ids"] if isinstance(x, str)))
            or any(not _safe(value) for value in selection["original_signal_ids"])):
        raise ValueError("private packet selection is invalid")
    if selection["role"] == "proposal":
        if not _safe(selection["original_event_id"]) or not selection["original_signal_ids"]:
            raise ValueError("proposal lineage identity is invalid")
    elif selection["original_event_id"] is not None or selection["original_signal_ids"]:
        raise ValueError("control packet cannot invent timeline identity")
    if (not isinstance(inputs, Mapping)
            or set(inputs) != {"execution_manifest_sha256", "source_sha256",
                               "event_timeline_sha256", "context_view_grid_sha256"}
            or any(not isinstance(value, str) or SHA.fullmatch(value) is None
                   for value in inputs.values())):
        raise ValueError("private packet input hashes are invalid")
    center = _rational(packet["center_source_time"])
    if center < 0 or not isinstance(packet.get("rows"), list) or len(packet["rows"]) != 6:
        raise ValueError("private packet rows are invalid")
    canonical_views = None
    for number, (row, role, offset) in enumerate(zip(packet["rows"], ROLES, OFFSETS), 1):
        if (not isinstance(row, Mapping)
                or set(row) != {"row_number", "row_role", "absolute_source_time", "cardinal_views"}
                or type(row.get("row_number")) is not int
                or row["row_number"] != number or row.get("row_role") != role
                or not isinstance(row.get("cardinal_views"), list)
                or len(row["cardinal_views"]) != 4
                or _rational(row["absolute_source_time"]) != center + offset
                or center + offset < 0):
            raise ValueError("private packet row contract is invalid")
        ids = set(); normalized = []
        for view in row["cardinal_views"]:
            if (not isinstance(view, Mapping)
                    or set(view) != {"candidate_id", "yaw_degrees", "pitch_degrees", "horizontal_fov_degrees"}
                    or not _safe(view.get("candidate_id")) or view["candidate_id"] in ids):
                raise ValueError("private cardinal view is invalid")
            ids.add(view["candidate_id"])
            values = (view["yaw_degrees"], view["pitch_degrees"], view["horizontal_fov_degrees"])
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
                raise ValueError("private cardinal geometry is invalid")
            if not (-180 <= values[0] < 180 and -90 <= values[1] <= 90 and 0 < values[2] <= 180):
                raise ValueError("private cardinal geometry is invalid")
            normalized.append(dict(view))
        if canonical_views is None: canonical_views = normalized
        elif normalized != canonical_views:
            raise ValueError("private cardinal ordering must be identical across rows")


def _hmac(key: bytes, message: str) -> str:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def build_adapter_index(*, private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], salt_hex: str):
    if (not isinstance(private_packets, Sequence) or isinstance(private_packets, (str, bytes))
            or not isinstance(ordered_private_packet_sha256s, Sequence)
            or isinstance(ordered_private_packet_sha256s, (str, bytes))
            or len(private_packets) not in {1, 6, 24}
            or len(private_packets) != len(ordered_private_packet_sha256s)
            or not isinstance(salt_hex, str) or SHA.fullmatch(salt_hex) is None):
        raise ValueError("adapter projection set inputs are invalid")
    key = bytes.fromhex(salt_hex); rows = []; packet_hashes = set(); manifests = set()
    full_hmacs = set(); ids = set()
    for packet, supplied_hash in zip(private_packets, ordered_private_packet_sha256s):
        validate_private_packet(packet)
        actual_hash = private_packet_sha256(packet)
        if (not isinstance(supplied_hash, str) or SHA.fullmatch(supplied_hash) is None
                or supplied_hash != actual_hash or actual_hash in packet_hashes):
            raise ValueError("ordered private packet hash set is invalid")
        packet_hashes.add(actual_hash)
        manifest = packet["inputs"]["execution_manifest_sha256"]; manifests.add(manifest)
        id_hmac = _hmac(key, f"id|successor-packet-v1|{manifest}|{actual_hash}")
        order_hmac = _hmac(key, f"order|successor-packet-v1|{manifest}|{actual_hash}")
        packet_id = "packet-" + id_hmac[:20]
        if (id_hmac == order_hmac or id_hmac in full_hmacs
                or order_hmac in full_hmacs or packet_id in ids):
            raise ValueError("adapter projection opaque identifier collision")
        full_hmacs.update((id_hmac, order_hmac)); ids.add(packet_id)
        projection = {"schema_version": PROJECTION_SCHEMA, "packet_id": packet_id,
            "rows": [{"row_number": number, "row_role": role,
                      "media_ref": f"media/{packet_id}/row-{number:02d}.png",
                      "views": ["view-1", "view-2", "view-3", "view-4"]}
                     for number, role in enumerate(ROLES, 1)],
            "privacy": dict(PUBLIC_PRIVACY), "authority": dict(PUBLIC_AUTHORITY)}
        rows.append((order_hmac, id_hmac, projection))
    if len(manifests) != 1:
        raise ValueError("private packets do not share one execution manifest")
    rows.sort(key=lambda item: (item[0], item[1]))
    return {"schema_version": INDEX_SCHEMA, "packet_count": len(rows),
            "packets": [{"presentation_ordinal": ordinal, "projection": row[2]}
                        for ordinal, row in enumerate(rows, 1)]}


def validate_adapter_index(index: Mapping[str, object], **inputs) -> None:
    expected = build_adapter_index(**inputs)
    if index != expected:
        raise ValueError("adapter projection index must exactly rebuild")
