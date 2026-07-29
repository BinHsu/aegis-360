#!/usr/bin/env python3
"""Plan a lifecycle-backed candidate sequence without rendering video."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.greedy_config import load_greedy_config  # noqa: E402
from aegis360.greedy_planner import (  # noqa: E402
    dumps_trace, plan_greedy_with_hysteresis,
)
from aegis360.interest import (  # noqa: E402
    evaluate_interest, interest_to_greedy_observations,
)
from aegis360.lifecycle_candidates import lifecycle_candidate_frames  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lifecycle_json", type=Path)
    parser.add_argument("tracking_json", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--candidate-type", required=True)
    parser.add_argument("--horizontal-fov-degrees", type=float, default=100)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if not all(path.is_file() for path in (
        args.lifecycle_json, args.tracking_json, args.config
    )):
        parser.error("required input is missing")

    lifecycle = json.loads(args.lifecycle_json.read_text())
    tracking = json.loads(args.tracking_json.read_text())
    config = load_greedy_config(args.config)
    frames = lifecycle_candidate_frames(
        lifecycle,
        tracking,
        horizontal_fov=math.radians(args.horizontal_fov_degrees),
        candidate_type=args.candidate_type,
    )
    interest = evaluate_interest(frames)
    observations = interest_to_greedy_observations(
        interest, config.scoring,
    )
    trace = plan_greedy_with_hysteresis(observations, config.planner)
    trace["slice_config"] = config.trace_config()
    trace["input_contract"] = {
        "lifecycle_schema": lifecycle["schema_version"],
        "candidate_association": "geometric_only",
        "editorial_persistence_allowed": False,
        "rendered": False,
    }
    trace["limitations"] = [
        "Planning-only diagnostic; no video was rendered.",
        "Operational detector/tracker compatibility does not verify identity.",
    ]
    args.output_json.write_text(dumps_trace(trace), encoding="utf-8")
    print(json.dumps({
        "decisions": len(trace["decisions"]),
        "subject_selected": sum(
            row["selected_candidate_id"].startswith("lifecycle:")
            for row in trace["decisions"]
        ),
        "fallbacks": sum(row["fallback"] for row in trace["decisions"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
