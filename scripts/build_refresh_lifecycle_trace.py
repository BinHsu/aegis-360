#!/usr/bin/env python3
"""Build a privacy-safe lifecycle trace from refresh and tracker evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.refresh_lifecycle import (  # noqa: E402
    build_refresh_lifecycle_trace,
    dumps_refresh_lifecycle_trace,
)
from aegis360.tracking_policy import TrackingPolicy  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("refresh_trace_json", type=Path)
    parser.add_argument("tracking_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--missing-grace-refreshes", type=int, default=2)
    parser.add_argument("--confidence-decay", type=float, default=.75)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")

    refresh = json.loads(args.refresh_trace_json.read_text())
    tracking = json.loads(args.tracking_json.read_text())
    confidences = {
        float(row["timestampSeconds"]): float(row["confidence"])
        for row in tracking["observations"]
        if row.get("state") == "tracked" and row.get("confidence") is not None
    }
    document = build_refresh_lifecycle_trace(
        refresh,
        confidences,
        policy=TrackingPolicy(
            missing_grace_frames=args.missing_grace_refreshes,
            confidence_decay=args.confidence_decay,
        ),
    )
    args.output_json.write_text(
        dumps_refresh_lifecycle_trace(document), encoding="utf-8"
    )
    print(f"trace={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
