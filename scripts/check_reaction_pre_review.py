#!/usr/bin/env python3
"""Fail closed on reaction-preview mechanics before human editorial review."""

from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aegis360.reaction_plan import canonical_sha256, validate_reaction_plan  # noqa: E402
from aegis360.reaction_pre_review import evaluate_reaction_preview  # noqa: E402

def load(path: Path): return json.loads(path.read_text(encoding="utf-8"))
def probe(path: Path) -> dict[str, object]:
    result=subprocess.run(["ffprobe","-v","error","-count_frames","-show_entries","stream=index,codec_type,codec_name,pix_fmt,width,height,r_frame_rate,duration,nb_read_frames","-of","json",str(path)],check=True,capture_output=True,text=True)
    return {"streams":json.loads(result.stdout)["streams"]}
def decoded_hash(path: Path, selector: str) -> str:
    result=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-map",selector,"-f","hash","-hash","sha256","-"],check=True,capture_output=True,text=True)
    prefix="SHA256="
    value=result.stdout.strip()
    if not value.startswith(prefix) or len(value)!=len(prefix)+64: raise ValueError("decoded stream hash is invalid")
    return value[len(prefix):]
def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("grid_json","roles_json","reactions_json","availability_json","gain_json","plan_json","primary_bundle","planned_bundle"):
        parser.add_argument(name,type=Path)
    parser.add_argument("--minimum-pose-change-degrees",type=float,default=8.0)
    parser.add_argument("--minimum-distinct-seconds",type=float,default=2.0)
    parser.add_argument("--output-json",type=Path)
    args=parser.parse_args(); evidence=[args.grid_json,args.roles_json,args.reactions_json,args.availability_json,args.gain_json,args.plan_json]
    primary_video=args.primary_bundle/"video.mp4"; planned_video=args.planned_bundle/"video.mp4"
    paths=evidence+[args.primary_bundle/"render.json",args.planned_bundle/"render.json",primary_video,planned_video]
    if not all(path.is_file() for path in paths): parser.error("required evidence or preview file is missing")
    grid_bytes=args.grid_json.read_bytes(); grid=json.loads(grid_bytes); roles=load(args.roles_json)
    reactions=load(args.reactions_json); availability=load(args.availability_json); gain=load(args.gain_json); plan=load(args.plan_json)
    validate_reaction_plan(plan,grid,grid_sha256=hashlib.sha256(grid_bytes).hexdigest(),roles=roles,reactions=reactions,availability=availability,gain=gain)
    primary_trace=load(args.primary_bundle/"render.json"); planned_trace=load(args.planned_bundle/"render.json")
    plan_sha=canonical_sha256(plan)
    if primary_trace.get("reaction_shot_plan_sha256")!=plan_sha or planned_trace.get("reaction_shot_plan_sha256")!=plan_sha:
        raise ValueError("preview trace plan checksum mismatch")
    report=evaluate_reaction_preview(grid,roles,plan,primary_trace,planned_trace,probe(primary_video),probe(planned_video),primary_video_hash=decoded_hash(primary_video,"0:v:0"),planned_video_hash=decoded_hash(planned_video,"0:v:0"),primary_audio_hash=decoded_hash(primary_video,"0:a:0"),planned_audio_hash=decoded_hash(planned_video,"0:a:0"),minimum_pose_change_degrees=args.minimum_pose_change_degrees,minimum_distinct_seconds=args.minimum_distinct_seconds)
    payload=json.dumps(report,indent=2,sort_keys=True)+"\n"
    if args.output_json is not None:
        if args.output_json.exists(): parser.error("refusing to overwrite output")
        args.output_json.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=args.output_json.parent,prefix=f".{args.output_json.name}.",suffix=".tmp",delete=False) as tmp: name=tmp.name; tmp.write(payload)
        try: os.link(name,args.output_json)
        finally: Path(name).unlink(missing_ok=True)
        print(args.output_json)
    else: print(payload,end="")
    return 0 if report["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
