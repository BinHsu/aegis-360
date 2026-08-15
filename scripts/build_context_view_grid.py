#!/usr/bin/env python3
"""Write one atomic deterministic four-cardinal context-view grid."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.context_views import build_context_view_grid  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start-seconds", required=True, type=float)
    parser.add_argument("--duration-seconds", required=True, type=float)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    artifact = build_context_view_grid(
        source_id=args.source_id, start_seconds=args.start_seconds,
        duration_seconds=args.duration_seconds,
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
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
