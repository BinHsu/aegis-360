"""Pixel-free bounded semantic-review packet for one continuous onset."""

from __future__ import annotations

import math
import re
from typing import Mapping

from .context_views import validate_context_view_grid
from .continuous_onset_candidates import validate_continuous_onset_candidates


SCHEMA = "aegis360.continuous-onset-semantic-packet.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")


def build_continuous_onset_semantic_packet(
    onset: Mapping[str, object], samples: Mapping[str, object],
    grid: Mapping[str, object], *, candidate_id: str, onset_sha256: str,
    samples_sha256: str, grid_sha256: str,
) -> dict[str, object]:
    validate_context_view_grid(grid)
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (onset_sha256, samples_sha256, grid_sha256)):
        raise ValueError("continuous-onset semantic packet checksums are invalid")
    if (onset.get("schema_version") != "aegis360.continuous-onset-candidates.v1"
            or samples.get("schema_version") not in {
                "aegis360.frame-difference-samples.v1",
                "aegis360.frame-difference-samples.v2",
            }
            or onset.get("source_id") != samples.get("source_id")
            or onset.get("source_id") != grid.get("source_id")
            or onset.get("window") != samples.get("window")
            or onset.get("window") != grid.get("window")
            or onset.get("inputs", {}).get("frame_difference_samples_sha256")
            != samples_sha256
            or samples.get("privacy", {}).get("contains_source_path") is not False
            or samples.get("privacy", {}).get("contains_pixels") is not False):
        raise ValueError("continuous-onset semantic packet lineage is invalid")
    validate_continuous_onset_candidates(
        onset, samples, onset.get("policy", {}), samples_sha256=samples_sha256,
        policy_sha256=onset.get("inputs", {}).get("candidate_policy_sha256", ""),
    )
    matches = [item for item in onset.get("candidates", [])
               if item.get("candidate_id") == candidate_id]
    if len(matches) != 1:
        raise ValueError("continuous-onset semantic packet requires one candidate")
    candidate = matches[0]
    if (candidate.get("hard_cut_claimed") is not False
            or candidate.get("temporal_form") != "continuous_onset"):
        raise ValueError("continuous-onset candidate cannot claim a hard cut")
    rows = samples.get("samples", [])
    window_start = samples["window"]["start_seconds"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("continuous-onset acquisition rows are invalid")
    timestamps = []
    for row in rows:
        if (not isinstance(row, Mapping)
                or set(row) != {"interval_pts_seconds", "pts_seconds",
                                "normalized_difference"}
                or any(isinstance(row[key], bool)
                       or not isinstance(row[key], (int, float))
                       or not math.isfinite(row[key])
                       for key in row)
                or not 0 <= row["normalized_difference"] <= 1
                or not math.isclose(row["pts_seconds"],
                                    window_start + row["interval_pts_seconds"],
                                    rel_tol=0, abs_tol=1e-9)):
            raise ValueError("continuous-onset acquisition row is invalid")
        timestamps.append(row["pts_seconds"])
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("continuous-onset acquisition rows must be ordered")
    lower = candidate.get("uncertainty_interval", {}).get("start_seconds")
    upper = candidate.get("uncertainty_interval", {}).get("end_seconds")
    support_start = candidate.get("support_interval", {}).get("start_seconds")
    support_end = candidate.get("support_interval", {}).get("end_seconds")
    support_count = candidate.get("support_interval", {}).get(
        "supporting_sample_count")
    if (lower not in timestamps or upper not in timestamps
            or support_start not in timestamps or support_end not in timestamps
            or support_start != upper or not lower < upper <= support_end):
        raise ValueError("continuous-onset timing is not backed by acquisition rows")
    lower_index = timestamps.index(lower)
    upper_index = timestamps.index(upper)
    support_end_index = timestamps.index(support_end)
    if (lower_index == 0
            or isinstance(support_count, bool) or not isinstance(support_count, int)
            or support_count < 2
            or support_end_index - upper_index + 1 != support_count):
        raise ValueError("continuous-onset packet requires bounded before and after rows")
    selected = [
        ("before", lower_index - 1),
        ("lower_bound", lower_index),
        ("upper_bound", upper_index),
        ("support_end", support_end_index),
        ("after", support_end_index + 1 if support_end_index + 1 < len(rows) else None),
    ]
    available_indices = [index for _, index in selected if index is not None]
    if len(set(available_indices)) != len(available_indices):
        raise ValueError("continuous-onset packet roles must resolve distinctly")
    candidate_ids = [item["candidate_id"] for item in grid["candidates"]]
    if len(candidate_ids) != 4:
        raise ValueError("continuous-onset packet requires four grid candidates")
    review_samples = []
    for sample_index, (role, row_index) in enumerate(selected):
        row = None if row_index is None else rows[row_index]
        review_samples.append({
            "sample_id": f"sample:{sample_index:02d}", "temporal_role": role,
            "available": row is not None, "row_index": row_index,
            "timestamp_seconds": None if row is None else float(row["pts_seconds"]),
            "acquisition_interval_pts_seconds": (None if row is None else
                                                  float(row["interval_pts_seconds"])),
            "normalized_difference": (None if row is None else
                                      float(row["normalized_difference"])),
            "representation": "four_cardinal_contact_sheet",
            "candidate_ids": candidate_ids,
        })
    return {
        "schema_version": SCHEMA, "source_id": onset["source_id"],
        "candidate_id": candidate_id,
        "inputs": {"continuous_onset_candidates_sha256": onset_sha256,
                   "frame_difference_samples_sha256": samples_sha256,
                   "context_view_grid_sha256": grid_sha256},
        "onset": {"uncertainty_interval": dict(candidate["uncertainty_interval"]),
                  "support_interval": dict(candidate["support_interval"]),
                  "temporal_form": "continuous_onset",
                  "hard_cut_claimed": False},
        "edge": None,
        "sampling_policy": {"policy_id": "onset-five-row-cardinal-v1",
                            "maximum_composite_frames": 5,
                            "maximum_source_viewports": 20},
        "samples": review_samples,
        "temporary_media_policy": {"durable_pixels_allowed": False,
                                   "render_only_declared_candidates": True,
                                   "delete_after_adapter_completion": True},
        "planner_authority": {"story_boundary_emitted": False,
                              "candidate_selected": False,
                              "renderer_command_emitted": False},
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_identity": False,
                    "contains_free_text": False},
        "limitations": ["five acquisition rows bound review but contain no pixels",
                        "semantic review cannot create a boundary, view or render command"],
    }


def validate_continuous_onset_semantic_packet(
    document: Mapping[str, object], onset: Mapping[str, object],
    samples: Mapping[str, object], grid: Mapping[str, object], *,
    onset_sha256: str, samples_sha256: str, grid_sha256: str,
) -> None:
    expected = build_continuous_onset_semantic_packet(
        onset, samples, grid, candidate_id=document.get("candidate_id", ""),
        onset_sha256=onset_sha256, samples_sha256=samples_sha256,
        grid_sha256=grid_sha256,
    )
    if document != expected:
        raise ValueError("continuous-onset semantic packet must exactly derive from inputs")
