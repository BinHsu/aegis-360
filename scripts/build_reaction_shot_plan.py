#!/usr/bin/env python3
"""Build an atomic role-bound reaction shot plan from immutable evidence."""

from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.reaction_plan import build_reaction_plan  # noqa: E402

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("grid_json", "roles_json", "reactions_json", "availability_json", "output_json"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    inputs = [args.grid_json, args.roles_json, args.reactions_json, args.availability_json]
    if not all(path.is_file() for path in inputs): parser.error("required evidence is missing")
    if args.output_json.exists(): parser.error("refusing to overwrite output")
    grid_bytes = args.grid_json.read_bytes()
    artifact = build_reaction_plan(load(args.grid_json), load(args.roles_json), load(args.reactions_json), load(args.availability_json), grid_sha256=hashlib.sha256(grid_bytes).hexdigest())
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output_json.parent, prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False) as temporary:
        name = temporary.name; temporary.write(payload)
    try: os.link(name, args.output_json)
    finally: Path(name).unlink(missing_ok=True)
    print(json.dumps({"segment_count": len(artifact["segments"])}, sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
