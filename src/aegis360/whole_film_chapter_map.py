"""Build a complete, candidate-free chapter map from every retained boundary."""

from __future__ import annotations

import re
from typing import Mapping


SCHEMA = "aegis360.whole-film-chapter-map.v1"
CONFIG_SCHEMA = "aegis360.whole-film-chapter-map-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:/+-]+$")
BOUNDARY_ROLES = {"chapter_boundary", "within_chapter_cut", "ending_transition"}
CHAPTER_ROLES = {"opening", "journey", "destination", "closing", "other"}


def build_whole_film_chapter_map(
    segment_timeline: Mapping[str, object], config: Mapping[str, object], *,
    segment_timeline_sha256: str, config_sha256: str,
) -> dict[str, object]:
    if (segment_timeline.get("schema_version") != "aegis360.story-segment-timeline.v1"
            or config.get("schema_version") != CONFIG_SCHEMA
            or any(SHA256.fullmatch(value or "") is None
                   for value in (segment_timeline_sha256, config_sha256))):
        raise ValueError("whole-film chapter-map input is invalid")
    if set(config) != {"schema_version", "map_id", "reviewer_type", "reviewer_id",
                       "reviewer_asset_sha256", "boundary_dispositions", "chapter_roles"}:
        raise ValueError("whole-film chapter-map config is invalid")
    if (not isinstance(config["map_id"], str) or SAFE_ID.fullmatch(config["map_id"]) is None
            or config["reviewer_type"] not in {"human", "agent", "local_model"}
            or not isinstance(config["reviewer_id"], str)
            or SAFE_ID.fullmatch(config["reviewer_id"]) is None):
        raise ValueError("whole-film chapter-map provenance is invalid")
    asset_sha = config["reviewer_asset_sha256"]
    if config["reviewer_type"] == "local_model":
        if not isinstance(asset_sha, str) or SHA256.fullmatch(asset_sha) is None:
            raise ValueError("local chapter-map reviewer requires an asset checksum")
    elif asset_sha is not None:
        raise ValueError("human or agent chapter-map review cannot claim a model asset")
    segments = segment_timeline.get("segments", [])
    if not segments:
        raise ValueError("whole-film chapter map requires segments")
    expected_boundaries = [item["left_boundary"] for item in segments[1:]]
    dispositions = config["boundary_dispositions"]
    if (not isinstance(dispositions, list)
            or len(dispositions) != len(expected_boundaries)):
        raise ValueError("every retained boundary requires one disposition")

    accounted = []
    for expected, disposition in zip(expected_boundaries, dispositions, strict=True):
        required = {"event_id", "signal_id", "timestamp_seconds", "structural_role"}
        if (not isinstance(disposition, Mapping) or set(disposition) != required
                or disposition["event_id"] != expected["event_id"]
                or disposition["signal_id"] != expected["signal_id"]
                or disposition["timestamp_seconds"] != expected["timestamp_seconds"]
                or disposition["structural_role"] not in BOUNDARY_ROLES):
            raise ValueError("chapter-map boundary accounting is incomplete or reordered")
        accounted.append(dict(disposition))

    chapter_ranges = []
    first = 0
    for index, disposition in enumerate(dispositions, start=1):
        if disposition["structural_role"] in {"chapter_boundary", "ending_transition"}:
            chapter_ranges.append((first, index))
            first = index
    chapter_ranges.append((first, len(segments)))
    roles = config["chapter_roles"]
    if (not isinstance(roles, list) or len(roles) != len(chapter_ranges)
            or any(role not in CHAPTER_ROLES for role in roles)):
        raise ValueError("chapter roles must align exactly to derived chapters")

    chapters = []
    for index, ((start_index, end_index), role) in enumerate(
        zip(chapter_ranges, roles, strict=True)
    ):
        members = segments[start_index:end_index]
        chapters.append({
            "chapter_id": f"chapter:{index:04d}",
            "chapter_role": role,
            "start_seconds": members[0]["start_seconds"],
            "end_seconds": members[-1]["end_seconds"],
            "segment_ids": [item["segment_id"] for item in members],
        })
    window = segment_timeline["window"]
    window_start = float(window["start_seconds"])
    window_end = window_start + float(window["duration_seconds"])
    if (chapters[0]["start_seconds"] != window_start
            or chapters[-1]["end_seconds"] != window_end
            or any(left["end_seconds"] != right["start_seconds"]
                   for left, right in zip(chapters, chapters[1:]))):
        raise ValueError("whole-film chapters must cover the window without gaps")
    return {
        "schema_version": SCHEMA, "source_id": segment_timeline["source_id"],
        "window": dict(window),
        "inputs": {"story_segment_timeline_sha256": segment_timeline_sha256,
                   "chapter_map_config_sha256": config_sha256},
        "map_id": config["map_id"], "boundary_accounting": accounted,
        "provenance": {"reviewer_type": config["reviewer_type"],
                       "reviewer_id": config["reviewer_id"],
                       "reviewer_asset_sha256": asset_sha},
        "chapters": chapters,
        "completeness": {"all_retained_boundaries_accounted": True,
                         "gap_free": True, "overlap_free": True},
        "planner_authority": {"temporal_reordering_authorized": False,
                              "candidate_selected": False,
                              "renderer_command_emitted": False},
        "limitations": [
            "complete accounting does not prove editorial chapter accuracy",
            "chapter roles do not select a view or a teaser interval",
            "ADR 0011 requires an independent foreshadow authorization gate",
        ],
    }


def validate_whole_film_chapter_map(
    document: Mapping[str, object], segment_timeline: Mapping[str, object],
    config: Mapping[str, object], *, segment_timeline_sha256: str,
    config_sha256: str,
) -> None:
    expected = build_whole_film_chapter_map(
        segment_timeline, config, segment_timeline_sha256=segment_timeline_sha256,
        config_sha256=config_sha256,
    )
    if document != expected:
        raise ValueError("whole-film chapter map must exactly derive from inputs")
