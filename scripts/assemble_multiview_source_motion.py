#!/usr/bin/env python3
"""Build a privacy-safe source-motion artifact from multiview ray matches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.multiview_motion import assemble_source_motion


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    try:
        source = json.loads(args.input_json.read_text(encoding="utf-8"))
        result = assemble_source_motion(source)
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output_json.with_name(f".{args.output_json.name}.tmp")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(args.output_json)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"assemble_multiview_source_motion: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
