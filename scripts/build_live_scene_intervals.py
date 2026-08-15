#!/usr/bin/env python3
"""Build atomic broad live-scene intervals from canonical semantic events."""

from __future__ import annotations
import argparse, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.live_scene import build_live_scene_intervals  # noqa: E402

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("semantic_json", type=Path); parser.add_argument("output_json", type=Path)
    args = parser.parse_args()
    if not args.semantic_json.is_file(): parser.error("semantic events are missing")
    if args.output_json.exists(): parser.error("refusing to overwrite output")
    artifact = build_live_scene_intervals(json.loads(args.semantic_json.read_text()))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output_json.parent, prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False) as temporary:
        name = temporary.name; temporary.write(payload)
    try: os.link(name, args.output_json)
    finally: Path(name).unlink(missing_ok=True)
    print(json.dumps({"interval_count": len(artifact["intervals"])}, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
