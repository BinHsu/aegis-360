#!/usr/bin/env python3
"""Build an atomic context grid from checksummed declared geometry config."""

from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.context_views import build_declared_context_view_grid  # noqa: E402

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("config_json",type=Path); parser.add_argument("output_json",type=Path)
    parser.add_argument("--source-id",required=True); parser.add_argument("--start-seconds",required=True,type=float); parser.add_argument("--duration-seconds",required=True,type=float); args=parser.parse_args()
    if not args.config_json.is_file(): parser.error("geometry config is missing")
    if args.output_json.exists(): parser.error("refusing to overwrite output")
    config_bytes=args.config_json.read_bytes(); artifact=build_declared_context_view_grid(json.loads(config_bytes),config_sha256=hashlib.sha256(config_bytes).hexdigest(),source_id=args.source_id,start_seconds=args.start_seconds,duration_seconds=args.duration_seconds)
    args.output_json.parent.mkdir(parents=True,exist_ok=True); payload=json.dumps(artifact,allow_nan=False,indent=2,sort_keys=True)+"\n"
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=args.output_json.parent,prefix=f".{args.output_json.name}.",suffix=".tmp",delete=False) as temporary: name=temporary.name; temporary.write(payload)
    try: os.link(name,args.output_json)
    finally: Path(name).unlink(missing_ok=True)
    print(args.output_json); return 0
if __name__=="__main__": raise SystemExit(main())
