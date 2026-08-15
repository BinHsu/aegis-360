#!/usr/bin/env python3
"""Run bounded pairwise MLX-VLM review and emit closed reaction-view gain."""

from __future__ import annotations
import argparse, hashlib, json, os, sys, tempfile, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from aegis360.local_reaction_gain_schema import local_reaction_gain_json_schema  # noqa: E402
from aegis360.reaction_view_gain import build_reaction_view_gain  # noqa: E402

def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda:source.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()
def canonical_sha(document: object) -> str:
    return hashlib.sha256((json.dumps(document,allow_nan=False,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("grid_json","roles_json","reactions_json","model_directory","output_json"):
        parser.add_argument(name,type=Path)
    parser.add_argument("frames",nargs="+",type=Path)
    parser.add_argument("--reaction-start-seconds",required=True,type=float)
    parser.add_argument("--reaction-end-seconds",required=True,type=float)
    parser.add_argument("--adapter-id",required=True); parser.add_argument("--config-id",required=True)
    parser.add_argument("--model-id",required=True); parser.add_argument("--expected-model-sha256",required=True)
    parser.add_argument("--maximum-frames",type=int,default=4); args=parser.parse_args()
    if args.output_json.exists(): parser.error("refusing to overwrite output")
    if not 1<=len(args.frames)<=args.maximum_frames<=8: parser.error("frame count must be within the declared bound")
    inputs=(args.grid_json,args.roles_json,args.reactions_json,*args.frames)
    if not all(path.is_file() for path in inputs): parser.error("required evidence or frame is missing")
    weight=args.model_directory/"model.safetensors"
    if not weight.is_file() or sha256_file(weight)!=args.expected_model_sha256: parser.error("model asset SHA-256 mismatch")
    grid_raw=args.grid_json.read_bytes(); roles_raw=args.roles_json.read_bytes(); reactions_raw=args.reactions_json.read_bytes()
    grid=json.loads(grid_raw); roles=json.loads(roles_raw); reactions=json.loads(reactions_raw)
    from mlx_vlm import generate,load
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.structured import build_json_schema_logits_processor
    started=time.monotonic(); model,processor=load(str(args.model_directory))
    prompt=apply_chat_template(processor,model.config,
        "Each silent image is a synchronized comparison from one event: CURRENT is on the left and PROPOSED is on the right. Choose promote only when PROPOSED visibly and substantially presents the audience reaction better while preserving the event relationship. Choose abstain when CURRENT is equal or better, the difference is merely reframing, either view is obstructed, or the evidence is ambiguous. Do not infer sound, identity, speech, or off-screen events. Return only the constrained decision.",
        num_images=len(args.frames))
    constrained=build_json_schema_logits_processor(processor.tokenizer,local_reaction_gain_json_schema())
    result=generate(model,processor,prompt,image=[str(path) for path in args.frames],temperature=0,max_tokens=24,logits_processors=[constrained],verbose=False)
    raw_decision=json.loads(result.text)
    config={"schema_version":"aegis360.reaction-view-gain-config.v2","config_id":args.config_id,"reviewer_kind":"local_vlm","adapter_id":args.adapter_id,"model_id":args.model_id,"model_sha256":args.expected_model_sha256,"decisions":[{"reaction_start_seconds":args.reaction_start_seconds,"reaction_end_seconds":args.reaction_end_seconds,"decision":raw_decision["decision"]}]}
    artifact=build_reaction_view_gain(config,grid,roles,reactions,config_sha256=canonical_sha(config),grid_sha256=hashlib.sha256(grid_raw).hexdigest(),roles_sha256=hashlib.sha256(roles_raw).hexdigest(),reactions_sha256=hashlib.sha256(reactions_raw).hexdigest())
    runtime={"frame_count":len(args.frames),"audio_provided":False,"elapsed_seconds":time.monotonic()-started,"generation_tokens":result.generation_tokens,"mlx_peak_memory_gb":result.peak_memory}
    args.output_json.parent.mkdir(parents=True,exist_ok=True); payload=json.dumps(artifact,allow_nan=False,indent=2,sort_keys=True)+"\n"
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=args.output_json.parent,prefix=f".{args.output_json.name}.",suffix=".tmp",delete=False) as tmp: name=tmp.name; tmp.write(payload)
    try: os.link(name,args.output_json)
    finally: Path(name).unlink(missing_ok=True)
    print(args.output_json); print(json.dumps(runtime,allow_nan=False,sort_keys=True),file=sys.stderr); return 0
if __name__=="__main__": raise SystemExit(main())
