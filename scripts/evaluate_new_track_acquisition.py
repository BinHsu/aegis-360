#!/usr/bin/env python3
"""Evaluate a fresh post-termination track acquisition without pixels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.new_track_acquisition import (  # noqa: E402
    AcquisitionPolicy, evaluate_new_track_acquisition,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("refresh_trace", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--terminated-at", type=float, required=True)
    parser.add_argument("--new-track-id", required=True)
    parser.add_argument("--consecutive-compatible", type=int, default=2)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if not args.refresh_trace.is_file():
        parser.error("refresh trace is missing")
    result = evaluate_new_track_acquisition(
        json.loads(args.refresh_trace.read_text()),
        terminated_at=args.terminated_at,
        new_track_id=args.new_track_id,
        policy=AcquisitionPolicy(args.consecutive_compatible),
    )
    args.output_json.write_text(
        json.dumps(result, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "acquired": result["new_track_id"] is not None,
        "acquired_at": result["acquired_at"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
