#!/usr/bin/env python3
"""Bind closed relative reaction-view gain decisions to immutable evidence."""

from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.reaction_view_gain import build_reaction_view_gain  # noqa: E402

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("config_json", "grid_json", "roles_json", "reactions_json", "output_json"):
        parser.add_argument(name, type=Path)
    args=parser.parse_args(); paths=(args.config_json,args.grid_json,args.roles_json,args.reactions_json)
    if not all(path.is_file() for path in paths): parser.error("required input is missing")
    if args.output_json.exists(): parser.error("refusing to overwrite output")
    raw=[path.read_bytes() for path in paths]; docs=[json.loads(value) for value in raw]
    artifact=build_reaction_view_gain(docs[0],docs[1],docs[2],docs[3],
        config_sha256=hashlib.sha256(raw[0]).hexdigest(),grid_sha256=hashlib.sha256(raw[1]).hexdigest(),
        roles_sha256=hashlib.sha256(raw[2]).hexdigest(),reactions_sha256=hashlib.sha256(raw[3]).hexdigest())
    args.output_json.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(artifact,allow_nan=False,indent=2,sort_keys=True)+"\n"
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=args.output_json.parent,prefix=f".{args.output_json.name}.",suffix=".tmp",delete=False) as tmp: name=tmp.name; tmp.write(payload)
    try: os.link(name,args.output_json)
    finally: Path(name).unlink(missing_ok=True)
    print(args.output_json); return 0
if __name__=="__main__": raise SystemExit(main())
