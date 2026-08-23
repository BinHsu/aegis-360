#!/usr/bin/env python3
"""Build one atomic multi-cadence scene-event pyramid."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.scene_event_pyramid import build_scene_event_pyramid  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("scene_events_json", type=Path, nargs="+")
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if not all(path.is_file() for path in args.scene_events_json):
        parser.error("scene-event input is missing")
    raw = [path.read_bytes() for path in args.scene_events_json]
    artifact = build_scene_event_pyramid(
        [json.loads(value) for value in raw],
        sha256s=[hashlib.sha256(value).hexdigest() for value in raw],
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
    print(json.dumps({"event_count": len(artifact["events"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
