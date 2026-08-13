#!/usr/bin/env python3
"""Plan one selected window-group proposal into an atomic render-ready directory."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.camera_path import greedy_trace_to_camera_path  # noqa: E402
from aegis360.greedy_config import load_greedy_config  # noqa: E402
from aegis360.greedy_planner import dumps_trace, plan_greedy_with_hysteresis  # noqa: E402
from aegis360.interest import evaluate_interest, interest_to_greedy_observations  # noqa: E402
from aegis360.pre_review import static_shot_difference  # noqa: E402
from aegis360.scene_context import validate_scene_context  # noqa: E402
from aegis360.shot_render import greedy_trace_to_static_shots  # noqa: E402
from aegis360.window_group import WindowGroupShot, window_group_candidate_frames  # noqa: E402


def dump(value: object) -> str:
    return json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal_json", type=Path)
    parser.add_argument("context_json", type=Path)
    parser.add_argument("greedy_config", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    if not all(path.is_file() for path in (
        args.proposal_json, args.context_json, args.greedy_config,
    )):
        parser.error("required input is missing")
    proposal = json.loads(args.proposal_json.read_text(encoding="utf-8"))
    context_document = json.loads(args.context_json.read_text(encoding="utf-8"))
    if proposal.get("schema_version") != "aegis360.window-group-proposal.v1":
        parser.error("unsupported proposal schema")
    context = validate_scene_context(context_document)
    proposal_window = proposal.get("window")
    context_window = context_document.get("window")
    if not isinstance(proposal_window, dict) or not isinstance(context_window, dict):
        parser.error("window metadata is missing")
    for key in ("source_id", "window_id", "start_seconds", "duration_seconds"):
        if proposal_window.get(key) != context_window.get(key):
            parser.error("proposal and context windows disagree")
    proposal_candidates = proposal.get("candidates")
    validated_candidates = [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "member_candidate_ids": list(candidate.member_candidate_ids),
        }
        for candidate in context.candidates
    ]
    if proposal_candidates != validated_candidates:
        parser.error("context candidates do not reproduce the proposal")
    geometry = proposal.get("geometry")
    if not isinstance(geometry, dict):
        parser.error("proposal geometry is missing")
    try:
        shot = WindowGroupShot(**geometry)
    except TypeError as error:
        parser.error(f"proposal geometry is invalid: {error}")
    absolute_timestamps = proposal_window.get("sample_timestamps_seconds")
    if not isinstance(absolute_timestamps, list):
        parser.error("proposal timestamps are missing")
    start = float(proposal_window["start_seconds"])
    duration = float(proposal_window["duration_seconds"])
    timestamps = [float(timestamp) - start for timestamp in absolute_timestamps]
    frames = window_group_candidate_frames(context, shot, timestamps)
    config = load_greedy_config(args.greedy_config)
    interest = evaluate_interest(frames)
    observations = interest_to_greedy_observations(interest, config.scoring)
    trace = plan_greedy_with_hysteresis(observations, config.planner)
    trace["slice_config"] = config.trace_config()
    trace["input_contract"] = {
        "schema_version": "aegis360.window-group-plan-input.v1",
        "proposal_schema": proposal["schema_version"],
        "context_schema": context_document["schema_version"],
        "source_id": proposal_window["source_id"],
        "window_id": proposal_window["window_id"],
        "selected_candidate_id": context.selected_candidate_id,
        "selection_resolution": (
            "deterministic_context_fallback"
            if context.selected_candidate_id is None
            else "review_selected_group"
        ),
        "association": shot.association_provenance,
        "identity_verified": False,
        "editorial_persistence_allowed": False,
        "rendered": False,
    }
    trace["limitations"] = [
        "Window group geometry does not establish member identity.",
        "Human/VLM context selection does not establish active speaker.",
        "Planning success does not establish comfort or directing quality.",
    ]
    static_shots = greedy_trace_to_static_shots(trace, duration, config.framing_safety)
    difference = static_shot_difference(
        static_shots, baseline_h_fov=config.framing_safety.minimum_h_fov,
        minimum_change=math.radians(8), minimum_seconds=2,
    )
    camera_path = greedy_trace_to_camera_path(
        trace, duration, direction_threshold=config.camera_min_angular_change,
        framing_safety=config.framing_safety,
    )
    selected = [decision["selected_candidate_id"] for decision in trace["decisions"]]
    gate = {
        "schema_version": "aegis360.semantic-planning-gate.v1",
        "source_id": proposal_window["source_id"],
        "passed_pose_differentiation": difference["passed"],
        "decision_count": len(selected),
        "selected_candidate_counts": {
            candidate_id: selected.count(candidate_id)
            for candidate_id in sorted(set(selected))
        },
        "static_shot_difference": difference,
        "privacy": {
            "contains_pixels": False, "contains_source_path": False,
            "contains_embeddings": False,
        },
        "rendered": False,
    }
    resolved_config = {
        "schema_version": "aegis360.semantic-plan-config.v1",
        "source_id": proposal_window["source_id"],
        "slice": {"start_seconds": start, "duration_seconds": duration},
        "versioned_greedy_config": config.trace_config(),
        "render_contract": "shot_static_v360_only",
        "privacy": {"contains_source_path": False, "contains_pixels": False},
    }
    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{args.output_directory.name}.", dir=args.output_directory.parent,
    ))
    try:
        (staging / "trace.json").write_text(dumps_trace(trace), encoding="utf-8")
        (staging / "planning-gate.json").write_text(dump(gate), encoding="utf-8")
        (staging / "camera-path.json").write_text(dump(camera_path), encoding="utf-8")
        (staging / "config.json").write_text(dump(resolved_config), encoding="utf-8")
        staging.rename(args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(dump({
        "pose_gate_passed": difference["passed"],
        "selected_candidate_counts": gate["selected_candidate_counts"],
    }), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
