#!/usr/bin/env python3
"""Create a candidate local-step artifact by bridging bounded interior gaps."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.gap_policy import bridge_candidate_gaps


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

    steps = bridge_candidate_gaps(
        source["steps"],
        maximum_interior_gap_frames=config["maximumInteriorGapFrames"],
    )
    state_counts: dict[str, int] = {}
    for step in steps:
        state_counts[step["state"]] = state_counts.get(step["state"], 0) + 1
    document = {
        "schema_version": "aegis360.bridged-causal-rotation-steps.v1",
        "source_id": source["source_id"],
        "source_config_id": source["config_id"],
        "gap_policy_config_id": config["configId"],
        "coordinate_convention": source["coordinate_convention"],
        "steps": steps,
        "summary": {"state_counts": state_counts},
        "privacy": source["privacy"],
        "limitations": [
            "Interpolated local steps are candidates, not measured motion.",
            "The artifact is not an absolute orientation path.",
            "Boundary and over-bound gaps remain invalid.",
            "No viewer-comfort validation has been performed.",
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
