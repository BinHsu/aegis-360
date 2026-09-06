#!/usr/bin/env python3
"""Build one atomic numeric plan for a typed story timeline."""

import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.typed_global_story_planner import build_typed_global_story_plan  # noqa: E402

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("timeline", "continuity", "grid", "policy", "output"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--utility", action="append", type=Path, required=True)
    args = parser.parse_args()
    paths = [args.timeline, *args.utility, args.continuity, args.grid, args.policy]
    if not all(path.is_file() for path in paths): parser.error("required input is missing")
    if args.output.exists(): parser.error("refusing to overwrite output")
    raw = {path: path.read_bytes() for path in paths}
    sha = lambda path: hashlib.sha256(raw[path]).hexdigest()
    document = build_typed_global_story_plan(
        json.loads(raw[args.timeline]), [json.loads(raw[p]) for p in args.utility],
        json.loads(raw[args.continuity]), json.loads(raw[args.grid]),
        json.loads(raw[args.policy]), timeline_sha256=sha(args.timeline),
        utility_sha256s=[sha(p) for p in args.utility],
        continuity_sha256=sha(args.continuity), grid_sha256=sha(args.grid),
        policy_sha256=sha(args.policy))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, allow_nan=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent,
            prefix=f".{args.output.name}.", suffix=".tmp", delete=False) as tmp:
        name = tmp.name; tmp.write(payload)
    try: os.link(name, args.output)
    finally: Path(name).unlink(missing_ok=True)
    print(args.output); return 0
if __name__ == "__main__": raise SystemExit(main())
