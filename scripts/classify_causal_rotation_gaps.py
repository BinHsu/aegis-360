#!/usr/bin/env python3
"""Classify causal rotation-step gaps without filling or smoothing them."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.gap_policy import classify_gap_runs


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rotation_steps", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()

    source = load(arguments.rotation_steps)
    config = load(arguments.config)
    if source.get("schema_version") != "aegis360.causal-rotation-steps.v1":
        raise SystemExit("unsupported rotation-step schema")
    if (
        config.get("schemaVersion")
        != "aegis360.causal-gap-policy-config.v1"
    ):
        raise SystemExit("unsupported gap-policy config schema")
    if arguments.output.exists():
        raise SystemExit("refusing to overwrite output")

    runs = classify_gap_runs(
        source["steps"],
        maximum_interior_gap_frames=config["maximumInteriorGapFrames"],
    )
    classifications: dict[str, int] = {}
    for run in runs:
        classifications[run.classification] = (
            classifications.get(run.classification, 0) + 1
        )
    document = {
        "schema_version": "aegis360.causal-gap-analysis.v1",
        "source_id": source["source_id"],
        "source_config_id": source["config_id"],
        "gap_policy_config_id": config["configId"],
        "policy": {
            "maximum_interior_gap_frames": (
                config["maximumInteriorGapFrames"]
            ),
            "boundary_gap_policy": config["boundaryGapPolicy"],
            "interior_gap_policy": config["interiorGapPolicy"],
            "performs_interpolation": False,
        },
        "summary": {
            "gap_run_count": len(runs),
            "classification_counts": classifications,
            "invalid_step_count": sum(run.frame_count for run in runs),
        },
        "gap_runs": [
            {
                "start_step_index": run.start_step_index,
                "end_step_index": run.end_step_index,
                "frame_count": run.frame_count,
                "start_pts_seconds": run.start_pts_seconds,
                "end_pts_seconds": run.end_pts_seconds,
                "classification": run.classification,
                "reason": run.reason,
            }
            for run in runs
        ],
        "privacy": source["privacy"],
        "limitations": [
            "Bridge candidates are classifications, not interpolated motion.",
            "The three-frame threshold has not passed viewer-comfort review.",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(document["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
