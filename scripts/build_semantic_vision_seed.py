#!/usr/bin/env python3
"""Build an atomic path-free Vision seed manifest from semantic artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_vision_seed import build_vision_seed_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("events_json", type=Path)
    parser.add_argument("tracklets_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--track-id", required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    parser.add_argument("--sample-fps", type=float, required=True)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output JSON")
    if not args.events_json.is_file() or not args.tracklets_json.is_file():
        parser.error("required input artifact is missing")
    events = json.loads(args.events_json.read_text(encoding="utf-8"))
    tracklets = json.loads(args.tracklets_json.read_text(encoding="utf-8"))
    manifest = build_vision_seed_manifest(
        events, tracklets, track_id=args.track_id,
        duration_seconds=args.duration_seconds, sample_fps=args.sample_fps,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        manifest, allow_nan=False, indent=2, sort_keys=True
    ) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix=f".{args.output_json.name}.",
            dir=args.output_json.parent, delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(serialized)
        os.replace(temporary, args.output_json)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    print(json.dumps({
        "track_id": manifest["track_id"],
        "start_seconds": manifest["start_seconds"],
        "viewport_id": manifest["viewport"]["viewport_id"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
