#!/usr/bin/env python3
"""Resolve a global event plan to complete availability-clipped segments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.global_camera_segments import build_global_camera_segments  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan_json", "timeline_json", "grid_json", "output_json"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    paths = (args.plan_json, args.timeline_json, args.grid_json)
    if not all(path.is_file() for path in paths):
        parser.error("required input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    artifact = build_global_camera_segments(
        *[json.loads(value) for value in raw],
        plan_sha256=hashlib.sha256(raw[0]).hexdigest(),
        timeline_sha256=hashlib.sha256(raw[1]).hexdigest(),
        grid_sha256=hashlib.sha256(raw[2]).hexdigest(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=args.output_json.parent,
        prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
    ) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"segment_count": len(artifact["segments"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
