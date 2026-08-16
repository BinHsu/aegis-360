"""Fuse overlapping cheap signals into neutral or role-scoped review events."""

from __future__ import annotations

import re
from typing import Mapping

from .context_views import validate_context_view_grid


SCHEMA = "aegis360.event-timeline.v2"


def build_multi_signal_timeline(
    grid: Mapping[str, object], scene_candidates: Mapping[str, object], *,
    grid_sha256: str, scene_candidates_sha256: str,
    reaction_timeline: Mapping[str, object] | None = None,
    reaction_timeline_sha256: str | None = None,
    scene_context_seconds: float = 2.0,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    hashes = (grid_sha256, scene_candidates_sha256)
    if any(re.fullmatch(r"[0-9a-f]{64}", value or "") is None for value in hashes):
        raise ValueError("multi-signal timeline checksums are invalid")
    if scene_candidates.get("schema_version") != "aegis360.scene-change-candidates.v1" or scene_candidates.get("source_id") != grid["source_id"]:
        raise ValueError("multi-signal scene candidates are invalid")
    if not isinstance(scene_context_seconds, (int, float)) or isinstance(scene_context_seconds, bool) or not 0 < scene_context_seconds <= 10:
        raise ValueError("multi-signal scene context is invalid")
    if (reaction_timeline is None) != (reaction_timeline_sha256 is None):
        raise ValueError("reaction timeline and checksum must appear together")
    if reaction_timeline is not None:
        if re.fullmatch(r"[0-9a-f]{64}", reaction_timeline_sha256 or "") is None or reaction_timeline.get("schema_version") != "aegis360.event-timeline.v1" or reaction_timeline.get("source_id") != grid["source_id"] or reaction_timeline.get("window") != grid["window"]:
            raise ValueError("multi-signal reaction timeline is invalid")

    window_start = grid["window"]["start_seconds"]
    window_end = window_start + grid["window"]["duration_seconds"]
    signals = []
    for candidate in scene_candidates["candidates"]:
        timestamp = candidate["timestamp_seconds"]
        if not window_start <= timestamp <= window_end:
            raise ValueError("scene candidate is outside the grid window")
        signals.append({
            "signal_id": candidate["event_id"], "signal_type": "scene_change",
            "start_seconds": max(window_start, timestamp - scene_context_seconds),
            "end_seconds": min(window_end, timestamp + scene_context_seconds),
            "evidence": {"timestamp_seconds": timestamp,
                         "scene_score": candidate["scene_score"]},
        })
    if reaction_timeline is not None:
        for event in reaction_timeline["events"]:
            signals.append({
                "signal_id": event["event_id"], "signal_type": "reaction_candidate",
                "start_seconds": event["start_seconds"],
                "end_seconds": event["end_seconds"],
                "evidence": dict(event["audio_evidence"]),
                "view_context": dict(event["view_context"]),
            })
    signals.sort(key=lambda item: (item["start_seconds"], item["end_seconds"], item["signal_type"], item["signal_id"]))
    clusters = []
    for signal in signals:
        if not clusters or signal["start_seconds"] > clusters[-1]["end_seconds"]:
            clusters.append({"start_seconds": signal["start_seconds"],
                             "end_seconds": signal["end_seconds"], "signals": [signal]})
        else:
            clusters[-1]["end_seconds"] = max(clusters[-1]["end_seconds"], signal["end_seconds"])
            clusters[-1]["signals"].append(signal)

    declared_ids = [candidate["candidate_id"] for candidate in grid["candidates"]]
    events = []
    for index, cluster in enumerate(clusters):
        scene_present = any(signal["signal_type"] == "scene_change" for signal in cluster["signals"])
        reaction_signals = [signal for signal in cluster["signals"] if signal["signal_type"] == "reaction_candidate"]
        if scene_present:
            review_scope = {"mode": "all_declared_candidates",
                            "candidate_ids": declared_ids}
        elif len(reaction_signals) == 1:
            context = reaction_signals[0]["view_context"]
            review_scope = {
                "mode": "current_and_available_proposed",
                "current_candidate_id": context["current_candidate_id"],
                "proposed_candidate_id": context["proposed_candidate_id"],
                "proposed_available_intervals": context["proposed_available_intervals"],
            }
        else:
            raise ValueError("reaction-only cluster must contain one signal in v2")
        events.append({
            "event_id": f"event:multi:{index:04d}",
            "start_seconds": float(cluster["start_seconds"]),
            "end_seconds": float(cluster["end_seconds"]),
            "signals": [{key: value for key, value in signal.items() if key != "view_context"}
                        for signal in cluster["signals"]],
            "review_scope": review_scope,
        })
    return {
        "schema_version": SCHEMA, "source_id": grid["source_id"],
        "window": dict(grid["window"]),
        "inputs": {"context_view_grid_sha256": grid_sha256,
                   "scene_change_candidates_sha256": scene_candidates_sha256,
                   "reaction_timeline_sha256": reaction_timeline_sha256},
        "fusion_policy": {"scene_context_seconds": float(scene_context_seconds),
                          "cluster_rule": "overlapping_review_windows_v1"},
        "events": events,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_names": False,
                    "contains_identity": False,
                    "contains_editorial_decision": False},
        "limitations": [
            "scene-change evidence proposes review boundaries but not importance or roles",
            "v2 fuses reaction and scene-change signals only",
        ],
    }


def validate_multi_signal_timeline(
    document: Mapping[str, object], grid: Mapping[str, object],
    scene_candidates: Mapping[str, object], *, grid_sha256: str,
    scene_candidates_sha256: str,
    reaction_timeline: Mapping[str, object] | None = None,
    reaction_timeline_sha256: str | None = None,
) -> None:
    expected = build_multi_signal_timeline(
        grid, scene_candidates, grid_sha256=grid_sha256,
        scene_candidates_sha256=scene_candidates_sha256,
        reaction_timeline=reaction_timeline,
        reaction_timeline_sha256=reaction_timeline_sha256,
        scene_context_seconds=document.get("fusion_policy", {}).get("scene_context_seconds", -1),
    )
    if document != expected:
        raise ValueError("multi-signal timeline must exactly derive from inputs")
