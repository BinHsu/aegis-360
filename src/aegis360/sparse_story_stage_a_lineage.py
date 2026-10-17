"""Bounded Stage A packet lineage from frozen, caller-supplied JSON evidence.

This is a synthetic/preflight gate. It does not prove source bytes, timeline
derivation from cheap signals, or the semantic labels of the six cases.
"""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Mapping, Sequence

from .context_views import validate_context_view_grid
from .sparse_story_projection import (OFFSETS, PRIVATE_AUTHORITY, PRIVATE_PRIVACY,
    PRIVATE_SCHEMA, ROLES, SAFE, SHA,
    private_packet_sha256, validate_private_packet)


MANIFEST_SCHEMA = "aegis360.sparse-story-stage-a-lineage-manifest.synthetic.v1"
CENTERS = (Fraction(1028, 5), Fraction(662, 5), Fraction(200),
           Fraction(297), Fraction(1309, 4), Fraction(773, 2))
SOURCE_SLOTS = (0, 0, 1, 1, 1, 1)


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, allow_nan=False, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("lineage evidence is not canonical JSON") from error


def _parse_frozen_bytes(raw: bytes, expected: object) -> str:
    if not isinstance(raw, bytes):
        raise ValueError("frozen JSON must be raw bytes")
    def pairs(items):
        document = {}
        for key, value in items:
            if key in document:
                raise ValueError("frozen JSON has duplicate keys")
            document[key] = value
        return document
    def bad_constant(value):
        raise ValueError(f"frozen JSON contains nonfinite {value}")
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                            parse_constant=bad_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("frozen JSON bytes are invalid") from error
    if _canonical(parsed) != _canonical(expected):
        raise ValueError("frozen JSON bytes do not match supplied document")
    return hashlib.sha256(raw).hexdigest()


def _fraction(value: object) -> Fraction:
    if (not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}
            or type(value["numerator"]) is not int or type(value["denominator"]) is not int
            or value["denominator"] <= 0):
        raise ValueError("source time must be an exact rational")
    result = Fraction(value["numerator"], value["denominator"])
    if (result.numerator, result.denominator) != (value["numerator"], value["denominator"]):
        raise ValueError("source time must be reduced")
    return result


def _rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _safe(value: object) -> bool:
    return isinstance(value, str) and bool(SAFE.fullmatch(value))


def build_stage_a_private_packets(*, execution_manifest: Mapping[str, object],
        execution_manifest_bytes: bytes,
        sources: Sequence[Mapping[str, object]],
        timelines: Sequence[Mapping[str, object]],
        timeline_bytes: Sequence[bytes],
        grids: Sequence[Mapping[str, object]],
        grid_bytes: Sequence[bytes]) -> tuple[list[dict[str, object]], list[str]]:
    """Return six exact private packets and their pre-projection ordered hashes.

    The manifest fixes the source pair and all six selections before projection.
    A caller must separately prove source SHA values against media and timeline
    v2 against upstream scene/reaction evidence before claiming real lineage.
    """
    if (not isinstance(execution_manifest, Mapping)
            or set(execution_manifest) != {"schema_version", "sources", "selections"}
            or execution_manifest["schema_version"] != MANIFEST_SCHEMA
            or not isinstance(execution_manifest["sources"], list)
            or len(execution_manifest["sources"]) != 2
            or not isinstance(execution_manifest["selections"], list)
            or len(execution_manifest["selections"]) != 6
            or any(not isinstance(items, Sequence) or isinstance(items, (str, bytes))
                   or len(items) != 2 for items in
                   (sources, timelines, timeline_bytes, grids, grid_bytes))):
        raise ValueError("Stage A lineage manifest or evidence cardinality is invalid")
    manifest_sha = _parse_frozen_bytes(execution_manifest_bytes, execution_manifest)
    evidence = []
    source_ids = set()
    for declaration, source, timeline, timeline_raw, grid, grid_raw in zip(
            execution_manifest["sources"], sources, timelines, timeline_bytes,
            grids, grid_bytes):
        timeline_sha = _parse_frozen_bytes(timeline_raw, timeline)
        grid_sha = _parse_frozen_bytes(grid_raw, grid)
        if (not isinstance(declaration, Mapping)
                or set(declaration) != {"source_id", "source_sha256",
                                            "event_timeline_sha256", "context_view_grid_sha256"}
                or not _safe(declaration.get("source_id"))
                or declaration["source_id"] in source_ids
                or any(not isinstance(declaration.get(key), str)
                       or SHA.fullmatch(declaration[key]) is None for key in
                       ("source_sha256", "event_timeline_sha256", "context_view_grid_sha256"))
                or not isinstance(source, Mapping)
                or set(source) != {"source_id", "source_sha256", "duration"}
                or source["source_id"] != declaration["source_id"]
                or source["source_sha256"] != declaration["source_sha256"]
                or not isinstance(timeline, Mapping)
                or set(timeline) != {"schema_version", "source_id", "window", "inputs",
                                     "fusion_policy", "events", "privacy", "limitations"}
                or timeline.get("schema_version") != "aegis360.event-timeline.v2"
                or timeline.get("source_id") != declaration["source_id"]
                or not isinstance(timeline.get("events"), list)
                or not isinstance(timeline.get("inputs"), Mapping)
                or timeline["inputs"].get("context_view_grid_sha256")
                   != declaration["context_view_grid_sha256"]
                or timeline_sha != declaration["event_timeline_sha256"]
                or not isinstance(grid, Mapping)
                or grid.get("source_id") != declaration["source_id"]
                or grid_sha != declaration["context_view_grid_sha256"]):
            raise ValueError("Stage A source/timeline/grid does not match frozen manifest")
        validate_context_view_grid(grid)
        if timeline["window"] != grid["window"]:
            raise ValueError("timeline and grid windows differ")
        if (len(grid["candidates"]) != 4
                or [candidate["yaw_degrees"] for candidate in grid["candidates"]]
                   != [0.0, 90.0, -180.0, -90.0]
                or len({(candidate["pitch_degrees"],
                         candidate["horizontal_fov_degrees"])
                        for candidate in grid["candidates"]}) != 1):
            raise ValueError("Stage A requires exactly four cardinal views")
        duration = _fraction(source["duration"])
        if duration <= 0:
            raise ValueError("source duration is invalid")
        window = grid["window"]
        window_start = Fraction(str(window["start_seconds"]))
        window_end = window_start + Fraction(str(window["duration_seconds"]))
        events = {}
        for event in timeline["events"]:
            if (not isinstance(event, Mapping) or not _safe(event.get("event_id"))
                    or event["event_id"] in events or not isinstance(event.get("signals"), list)):
                raise ValueError("timeline event IDs are invalid")
            signal_ids = []
            for signal in event["signals"]:
                if not isinstance(signal, Mapping) or not _safe(signal.get("signal_id")):
                    raise ValueError("timeline signal IDs are invalid")
                signal_ids.append(signal["signal_id"])
            if len(signal_ids) != len(set(signal_ids)):
                raise ValueError("timeline signal IDs are duplicated")
            events[event["event_id"]] = (signal_ids, event)
        evidence.append((declaration, duration, grid, events, window_start, window_end))
        source_ids.add(declaration["source_id"])
    packets = []
    for case_index, (selection, center, slot) in enumerate(zip(
            execution_manifest["selections"], CENTERS, SOURCE_SLOTS)):
        declaration, duration, grid, events, window_start, window_end = evidence[slot]
        role = selection.get("role") if isinstance(selection, Mapping) else None
        if (not isinstance(selection, Mapping)
                or set(selection) != {"source_id", "role", "original_event_id",
                                         "original_signal_ids", "center_source_time"}
                or selection["source_id"] != declaration["source_id"]
                or role not in {"proposal", "control"}
                or _fraction(selection["center_source_time"]) != center
                or center + OFFSETS[0] < max(Fraction(0), window_start)
                or center + OFFSETS[-1] > min(duration, window_end)):
            raise ValueError(f"Stage A selection {case_index} is not frozen case order")
        event_id, signal_ids = selection["original_event_id"], selection["original_signal_ids"]
        if role == "proposal":
            if (not _safe(event_id) or event_id not in events
                    or not isinstance(signal_ids, list) or not signal_ids
                    or any(not _safe(signal_id) for signal_id in signal_ids)
                    or len(signal_ids) != len(set(signal_ids))
                    or any(signal_id not in events[event_id][0]
                           for signal_id in signal_ids)):
                raise ValueError("Stage A proposal is not timeline-derived")
            event = events[event_id][1]
            try:
                start = Fraction(str(event["start_seconds"]))
                end = Fraction(str(event["end_seconds"]))
                signal_centers = [Fraction(str(signal["evidence"]["timestamp_seconds"]))
                    for signal in event["signals"] if signal["signal_id"] in signal_ids
                    and signal.get("signal_type") == "scene_change"]
            except (KeyError, TypeError, ValueError, OverflowError) as error:
                raise ValueError("Stage A proposal event time is invalid") from error
            if not start <= center <= end or center not in signal_centers:
                raise ValueError("Stage A proposal center is not timeline-derived")
        elif event_id is not None or signal_ids != []:
            raise ValueError("Stage A control invents timeline identity")
        views = [{key: candidate[key] for key in ("candidate_id", "yaw_degrees",
                  "pitch_degrees", "horizontal_fov_degrees")}
                 for candidate in grid["candidates"]]
        packet = {"schema_version": PRIVATE_SCHEMA, "source_id": declaration["source_id"],
            "selection": {"role": role, "original_event_id": event_id,
                          "original_signal_ids": list(signal_ids)},
            "inputs": {"execution_manifest_sha256": manifest_sha,
                       "source_sha256": declaration["source_sha256"],
                       "event_timeline_sha256": declaration["event_timeline_sha256"],
                       "context_view_grid_sha256": declaration["context_view_grid_sha256"]},
            "center_source_time": _rational(center),
            "rows": [{"row_number": number, "row_role": row_role,
                      "absolute_source_time": _rational(center + offset),
                      "cardinal_views": [dict(view) for view in views]}
                     for number, (row_role, offset) in enumerate(zip(ROLES, OFFSETS), 1)],
            "privacy": dict(PRIVATE_PRIVACY), "authority": dict(PRIVATE_AUTHORITY)}
        validate_private_packet(packet)
        packets.append(packet)
    hashes = [private_packet_sha256(packet) for packet in packets]
    if len(set(hashes)) != 6:
        raise ValueError("Stage A private packet hashes must be unique")
    return packets, hashes


def validate_stage_a_private_packets(*, private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], **evidence: object) -> None:
    expected_packets, expected_hashes = build_stage_a_private_packets(**evidence)
    if (not isinstance(private_packets, Sequence) or isinstance(private_packets, (str, bytes))
            or not isinstance(ordered_private_packet_sha256s, Sequence)
            or isinstance(ordered_private_packet_sha256s, (str, bytes))
            or list(private_packets) != expected_packets
            or list(ordered_private_packet_sha256s) != expected_hashes):
        raise ValueError("Stage A private packet lineage must exactly rebuild")
