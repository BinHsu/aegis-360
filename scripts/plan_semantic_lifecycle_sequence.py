#!/usr/bin/env python3
"""Merge semantic lifecycles and evaluate a planning-only directing gate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.framing import FramingSafetyConfig  # noqa: E402
from aegis360.camera_path import greedy_trace_to_camera_path  # noqa: E402
from aegis360.greedy_config import load_greedy_config  # noqa: E402
from aegis360.greedy_planner import (  # noqa: E402
    dumps_trace, plan_greedy_with_hysteresis,
)
from aegis360.interest import (  # noqa: E402
    evaluate_interest, interest_to_greedy_observations,
)
from aegis360.pre_review import static_shot_difference  # noqa: E402
from aegis360.semantic_sequence import (  # noqa: E402
    merge_lifecycle_candidate_sequences,
)
from aegis360.shot_render import greedy_trace_to_static_shots  # noqa: E402


def _load_manifest(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "aegis360.semantic-plan-input.v1":
        raise ValueError("unsupported semantic plan input schema")
    if not isinstance(document.get("source_id"), str) or not document["source_id"]:
        raise ValueError("source_id is required")
    duration = document.get("duration_seconds")
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError("duration_seconds must be finite and positive")
    tracks = document.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError("at least one track input is required")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--horizontal-fov-degrees", type=float, default=110.0)
    parser.add_argument("--minimum-change-degrees", type=float, default=8.0)
    parser.add_argument("--minimum-distinct-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    if not args.manifest.is_file() or not args.config.is_file():
        parser.error("required input is missing")

    document = _load_manifest(args.manifest)
    config = load_greedy_config(args.config)
    sequences = []
    track_contracts = []
    for row in document["tracks"]:
        if not isinstance(row, dict):
            raise ValueError("track input must be an object")
        lifecycle_path = Path(row.get("lifecycle_json", ""))
        tracking_path = Path(row.get("tracking_json", ""))
        candidate_type = row.get("candidate_type")
        if (
            not lifecycle_path.is_file()
            or not tracking_path.is_file()
            or not isinstance(candidate_type, str)
            or not candidate_type
        ):
            raise ValueError("track input is incomplete")
        lifecycle = json.loads(lifecycle_path.read_text(encoding="utf-8"))
        tracking = json.loads(tracking_path.read_text(encoding="utf-8"))
        sequences.append((lifecycle, tracking, candidate_type))
        track_contracts.append({
            "track_id": lifecycle.get("track_id"),
            "candidate_type": candidate_type,
            "lifecycle_schema": lifecycle.get("schema_version"),
            "tracking_schema": tracking.get("schemaVersion"),
        })

    horizontal_fov = math.radians(args.horizontal_fov_degrees)
    frames = merge_lifecycle_candidate_sequences(
        sequences, horizontal_fov=horizontal_fov,
    )
    interest = evaluate_interest(frames)
    observations = interest_to_greedy_observations(interest, config.scoring)
    trace = plan_greedy_with_hysteresis(observations, config.planner)
    trace["slice_config"] = config.trace_config()
    trace["input_contract"] = {
        "schema_version": document["schema_version"],
        "source_id": document["source_id"],
        "tracks": track_contracts,
        "candidate_association": "geometric_only",
        "editorial_persistence_allowed": False,
        "rendered": False,
    }
    trace["limitations"] = [
        "Planning-only diagnostic; no video was rendered.",
        "Operational detector/tracker compatibility does not verify identity.",
        "Pose differentiation does not establish semantic interest or comfort.",
    ]

    framing = config.framing_safety
    shots = greedy_trace_to_static_shots(
        trace, float(document["duration_seconds"]), framing,
    )
    difference = static_shot_difference(
        shots,
        baseline_h_fov=framing.minimum_h_fov,
        minimum_change=math.radians(args.minimum_change_degrees),
        minimum_seconds=args.minimum_distinct_seconds,
    )
    selected = [row["selected_candidate_id"] for row in trace["decisions"]]
    report = {
        "schema_version": "aegis360.semantic-planning-gate.v1",
        "source_id": document["source_id"],
        "passed_pose_differentiation": difference["passed"],
        "decision_count": len(selected),
        "selected_candidate_counts": {
            candidate_id: selected.count(candidate_id)
            for candidate_id in sorted(set(selected))
        },
        "static_shot_difference": difference,
        "privacy": {
            "contains_pixels": False,
            "contains_source_path": False,
            "contains_embeddings": False,
        },
        "rendered": False,
    }
    camera_path = greedy_trace_to_camera_path(
        trace,
        float(document["duration_seconds"]),
        direction_threshold=config.camera_min_angular_change,
    )
    resolved_config = {
        "schema_version": "aegis360.semantic-plan-config.v1",
        "source_id": document["source_id"],
        "slice": {
            "start_seconds": float(document.get("start_seconds", 0.0)),
            "duration_seconds": float(document["duration_seconds"]),
        },
        "versioned_greedy_config": config.trace_config(),
        "render_contract": "shot_static_v360_only",
        "privacy": {
            "contains_source_path": False,
            "contains_pixels": False,
        },
    }

    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{args.output_directory.name}.",
        dir=args.output_directory.parent,
    ))
    try:
        (staging / "trace.json").write_text(
            dumps_trace(trace), encoding="utf-8"
        )
        (staging / "planning-gate.json").write_text(
            json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / "camera-path.json").write_text(
            json.dumps(
                camera_path, allow_nan=False, indent=2, sort_keys=True
            ) + "\n",
            encoding="utf-8",
        )
        (staging / "config.json").write_text(
            json.dumps(
                resolved_config, allow_nan=False, indent=2, sort_keys=True
            ) + "\n",
            encoding="utf-8",
        )
        staging.rename(args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({
        "decisions": len(selected),
        "pose_gate_passed": difference["passed"],
        "selected_candidate_counts": report["selected_candidate_counts"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
