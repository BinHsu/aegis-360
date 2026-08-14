#!/usr/bin/env python3
"""Build one atomic path-free window-group geometry proposal."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.window_group_artifact import build_window_group_proposal_artifact  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spherical_json", type=Path)
    parser.add_argument("face_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--start", required=True, type=float)
    parser.add_argument("--duration", required=True, type=float)
    parser.add_argument("--maximum-face-pitch-correction-degrees", type=float, default=5.0)
    parser.add_argument("--use-vertical-bounds-midpoint", action="store_true")
    args = parser.parse_args()
    if not args.spherical_json.is_file() or not args.face_json.is_file():
        parser.error("required evidence is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    artifact = build_window_group_proposal_artifact(
        json.loads(args.spherical_json.read_text(encoding="utf-8")),
        json.loads(args.face_json.read_text(encoding="utf-8")),
        source_id=args.source_id, window_id=args.window_id,
        start_seconds=args.start, duration_seconds=args.duration,
        maximum_face_pitch_correction_degrees=args.maximum_face_pitch_correction_degrees,
        use_vertical_bounds_midpoint=args.use_vertical_bounds_midpoint,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=args.output_json.parent,
            prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(payload)
        try:
            os.link(temporary_name, args.output_json)
        except FileExistsError:
            parser.error("refusing to overwrite output")
        Path(temporary_name).unlink()
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
