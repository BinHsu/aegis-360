#!/usr/bin/env python3
"""Bind checksummed candidate-scoped availability to a context-view grid."""

from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.candidate_availability import build_candidate_availability  # noqa: E402

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("config_json",type=Path); parser.add_argument("grid_json",type=Path); parser.add_argument("output_json",type=Path); args=parser.parse_args()
    if not args.config_json.is_file() or not args.grid_json.is_file(): parser.error("required input is missing")
    if args.output_json.exists(): parser.error("refusing to overwrite output")
    config_bytes=args.config_json.read_bytes(); grid_bytes=args.grid_json.read_bytes(); artifact=build_candidate_availability(json.loads(config_bytes),json.loads(grid_bytes),config_sha256=hashlib.sha256(config_bytes).hexdigest(),grid_sha256=hashlib.sha256(grid_bytes).hexdigest())
    args.output_json.parent.mkdir(parents=True,exist_ok=True); payload=json.dumps(artifact,allow_nan=False,indent=2,sort_keys=True)+"\n"
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=args.output_json.parent,prefix=f".{args.output_json.name}.",suffix=".tmp",delete=False) as temporary: name=temporary.name; temporary.write(payload)
    try: os.link(name,args.output_json)
    finally: Path(name).unlink(missing_ok=True)
    print(args.output_json); return 0
if __name__=="__main__": raise SystemExit(main())
