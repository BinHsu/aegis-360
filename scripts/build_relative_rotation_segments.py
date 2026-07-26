#!/usr/bin/env python3
"""Build independently anchored relative-orientation segments."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.relative_rotation_segments import build_relative_rotation_segments


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bridged_steps", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    source = json.loads(
        arguments.bridged_steps.read_text(encoding="utf-8")
    )
    if (
        source.get("schema_version")
        != "aegis360.bridged-causal-rotation-steps.v1"
    ):
        raise SystemExit("unsupported bridged-step schema")
    if arguments.output.exists():
        raise SystemExit("refusing to overwrite output")
    segments = build_relative_rotation_segments(source["steps"])
    document = {
        "schema_version": "aegis360.relative-rotation-segments.v1",
        "source_id": source["source_id"],
        "source_config_id": source["source_config_id"],
        "gap_policy_config_id": source["gap_policy_config_id"],
        "coordinate_convention": source["coordinate_convention"],
        "segments": segments,
        "summary": {
            "segment_count": len(segments),
            "sample_count": sum(
                len(segment["samples"]) for segment in segments
            ),
        },
        "privacy": source["privacy"],
        "limitations": [
            "Each segment has an independent identity anchor.",
            "No orientation relationship is claimed across invalid gaps.",
            "Interpolated samples are not measured camera motion.",
            "This artifact has not passed viewer-comfort validation.",
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
