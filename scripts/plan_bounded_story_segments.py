#!/usr/bin/env python3
"""Build one atomic bounded symbolic story-segment plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.bounded_story_segment_planner import plan_bounded_story_segments  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("segment_timeline_json", type=Path)
    parser.add_argument("constraints_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--start-seconds", type=float, required=True)
    parser.add_argument("--end-seconds", type=float, required=True)
    parser.add_argument("--relevance", type=Path, action="append", default=[])
    args = parser.parse_args()
    paths = [args.segment_timeline_json, args.constraints_json, args.grid_json,
             args.policy_json, *args.relevance]
    if not all(path.is_file() for path in paths):
        parser.error("planner evidence is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = [path.read_bytes() for path in paths]
    relevance_raw = raw[4:]
    document = plan_bounded_story_segments(
        json.loads(raw[0]), json.loads(raw[1]),
        [json.loads(value) for value in relevance_raw],
        json.loads(raw[2]), json.loads(raw[3]),
        start_seconds=args.start_seconds, end_seconds=args.end_seconds,
        segment_timeline_sha256=hashlib.sha256(raw[0]).hexdigest(),
        constraints_sha256=hashlib.sha256(raw[1]).hexdigest(),
        relevance_sha256s=[hashlib.sha256(value).hexdigest() for value in relevance_raw],
        grid_sha256=hashlib.sha256(raw[2]).hexdigest(),
        policy_sha256=hashlib.sha256(raw[3]).hexdigest(),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=args.output_json.parent, delete=False) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"decision_count": len(document["decisions"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
