#!/usr/bin/env python3
"""Apply tunable temporal suppression to raw scene-event evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.scene_change_candidates import build_scene_change_candidates  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene_events_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--score-floor", type=float, default=0.4)
    parser.add_argument("--minimum-separation-seconds", type=float, default=10.0)
    args = parser.parse_args()
    if not args.scene_events_json.is_file():
        parser.error("scene events are missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    raw = args.scene_events_json.read_bytes()
    artifact = build_scene_change_candidates(
        json.loads(raw), scene_events_sha256=hashlib.sha256(raw).hexdigest(),
        score_floor=args.score_floor,
        minimum_separation_seconds=args.minimum_separation_seconds,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output_json.parent, delete=False) as temporary:
        temporary_name = temporary.name
        temporary.write(payload)
    try:
        os.link(temporary_name, args.output_json)
    finally:
        Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"candidate_count": len(artifact["candidates"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
