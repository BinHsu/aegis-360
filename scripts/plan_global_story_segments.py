#!/usr/bin/env python3
"""Build a complete persistent-view numeric story plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.global_story_segment_planner import plan_global_story_segments  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline_json", "constraints_json", "grid_json", "policy_json",
                 "output_json"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--utility", action="append", type=Path, default=[])
    args = parser.parse_args()
    paths = [args.timeline_json, args.constraints_json, args.grid_json,
             args.policy_json, *args.utility]
    if not all(path.is_file() for path in paths):
        parser.error("required planner input is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    utility_raw = raw[4:]
    artifact = plan_global_story_segments(
        json.loads(raw[0]), json.loads(raw[1]),
        [json.loads(value) for value in utility_raw],
        json.loads(raw[2]), json.loads(raw[3]),
        timeline_sha256=hashlib.sha256(raw[0]).hexdigest(),
        constraints_sha256=hashlib.sha256(raw[1]).hexdigest(),
        utility_sha256s=[hashlib.sha256(value).hexdigest() for value in utility_raw],
        grid_sha256=hashlib.sha256(raw[2]).hexdigest(),
        policy_sha256=hashlib.sha256(raw[3]).hexdigest(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=args.output_json.parent, delete=False) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"segment_count": len(artifact["decisions"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
