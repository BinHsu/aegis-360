#!/usr/bin/env python3
"""Render an atomic planned or primary-only reaction preview bundle."""

from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.reaction_plan import canonical_sha256, validate_reaction_plan  # noqa: E402

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_video", type=Path); parser.add_argument("grid_json", type=Path)
    parser.add_argument("plan_json", type=Path); parser.add_argument("output_directory", type=Path)
    parser.add_argument("--mode", choices=("planned", "primary-only"), required=True)
    parser.add_argument("--width", type=int, default=960); parser.add_argument("--height", type=int, default=540)
    args = parser.parse_args()
    if not all(path.is_file() for path in (args.input_video, args.grid_json, args.plan_json)): parser.error("required input is missing")
    if args.output_directory.exists(): parser.error("refusing to overwrite output directory")
    if args.width <= 0 or args.height <= 0 or args.width % 2 or args.height % 2: parser.error("output dimensions must be positive and even")
    grid_bytes = args.grid_json.read_bytes(); grid = json.loads(grid_bytes); plan = json.loads(args.plan_json.read_text())
    grid_sha = hashlib.sha256(grid_bytes).hexdigest(); validate_reaction_plan(plan, grid, grid_sha256=grid_sha)
    candidate_by_id = {item["candidate_id"]: item for item in grid["candidates"]}
    primary = next(item["candidate_id"] for item in plan["segments"] if item["reason"] == "primary_performance_default")
    segments = plan["segments"] if args.mode == "planned" else [{
        "start_seconds": grid["window"]["start_seconds"],
        "end_seconds": grid["window"]["start_seconds"] + grid["window"]["duration_seconds"],
        "candidate_id": primary, "reason": "primary_only_baseline",
    }]
    chains, labels = [], []
    for index, segment in enumerate(segments):
        view = candidate_by_id[segment["candidate_id"]]; label = f"v{index}"; labels.append(f"[{label}]")
        chains.append(
            f"[0:v:0]trim=start={segment['start_seconds']}:end={segment['end_seconds']},"
            f"setpts=PTS-STARTPTS,v360=input=equirect:output=flat:w={args.width}:h={args.height}:"
            f"yaw={view['yaw_degrees']}:pitch={view['pitch_degrees']}:h_fov={view['horizontal_fov_degrees']}:interp=linear[{label}]"
        )
    duration = grid["window"]["duration_seconds"]
    filter_complex = ";".join(chains + [
        "".join(labels) + f"concat=n={len(labels)}:v=1:a=0[joined]",
        f"[joined]tpad=stop_mode=clone:stop_duration=0.1,fps=15,trim=duration={duration},"
        "setpts=PTS-STARTPTS[video]",
    ])
    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{args.output_directory.name}.", dir=args.output_directory.parent))
    try:
        output = staging / "video.mp4"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(args.input_video),
            "-filter_complex", filter_complex, "-map", "[video]", "-map", "0:a:0", "-t", str(grid["window"]["duration_seconds"]),
            "-c:v", "h264_videotoolbox", "-b:v", "6000k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output),
        ], check=True)
        trace = {
            "schema_version": "aegis360.reaction-preview-render.v1", "source_id": grid["source_id"],
            "mode": args.mode, "context_view_grid_sha256": grid_sha,
            "reaction_shot_plan_sha256": canonical_sha256(plan), "segments": segments,
            "encoder": {"video": "h264_videotoolbox", "bitrate": "6000k", "pixel_format": "yuv420p", "audio": "aac_192k", "width": args.width, "height": args.height, "frames_per_second": 15},
            "privacy": {"contains_source_path": False, "contains_pixels": False},
        }
        (staging / "render.json").write_text(json.dumps(trace, allow_nan=False, indent=2, sort_keys=True) + "\n")
        staging.rename(args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True); raise
    print(args.output_directory); return 0

if __name__ == "__main__": raise SystemExit(main())
