#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo / "src"))

from aegis360.flat_stabilizer import plan


parser = argparse.ArgumentParser(description="Plan flat-video post-warp stabilization")
parser.add_argument("motion_evidence", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--smoothing-radius", type=float, default=0.5)
parser.add_argument(
    "--measurement-direction",
    required=True,
    choices=("previous_to_current", "current_to_previous"),
)
args = parser.parse_args()
document = json.loads(args.motion_evidence.read_text(encoding="utf-8"))
result = plan(
    document,
    smoothing_radius_seconds=args.smoothing_radius,
    measurement_direction=args.measurement_direction,
)
args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
