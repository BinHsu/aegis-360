#!/usr/bin/env python3
"""Build one atomic reaction-interval candidate artifact from sound events."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.reaction_intervals import build_reaction_intervals  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sound_events_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--applause-threshold", type=float, default=0.5)
    parser.add_argument("--clapping-threshold", type=float, default=0.5)
    parser.add_argument("--minimum-supporting-windows", type=int, default=2)
    args = parser.parse_args()
    if not args.sound_events_json.is_file():
        parser.error("sound-event artifact is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    artifact = build_reaction_intervals(
        json.loads(args.sound_events_json.read_text(encoding="utf-8")),
        applause_threshold=args.applause_threshold,
        clapping_threshold=args.clapping_threshold,
        minimum_supporting_windows=args.minimum_supporting_windows,
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
        os.link(temporary_name, args.output_json)
        Path(temporary_name).unlink()
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
    print(json.dumps({"interval_count": len(artifact["intervals"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
