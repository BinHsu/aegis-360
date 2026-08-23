#!/usr/bin/env python3
"""Validate and atomically render one bounded story-segment plan."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.bounded_story_render import build_bounded_story_filter_graph  # noqa: E402
from aegis360.bounded_story_segment_planner import validate_bounded_story_segment_plan  # noqa: E402


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_video", type=Path)
    parser.add_argument("segment_timeline_json", type=Path)
    parser.add_argument("constraints_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("policy_json", type=Path)
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--relevance", type=Path, action="append", default=[])
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--fixed-baseline", action="store_true")
    args = parser.parse_args()
    paths = [args.source_video, args.segment_timeline_json, args.constraints_json,
             args.grid_json, args.policy_json, args.plan_json, *args.relevance]
    if not all(path.is_file() for path in paths):
        parser.error("render source or evidence is missing")
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    raws = [path.read_bytes() for path in paths[1:]]
    timeline, constraints, grid, policy, plan = [json.loads(raw) for raw in raws[:5]]
    relevance_raw = raws[5:]
    relevances = [json.loads(raw) for raw in relevance_raw]
    validate_bounded_story_segment_plan(
        plan, timeline, constraints, relevances, grid, policy,
        segment_timeline_sha256=digest(raws[0]), constraints_sha256=digest(raws[1]),
        relevance_sha256s=[digest(raw) for raw in relevance_raw],
        grid_sha256=digest(raws[2]), policy_sha256=digest(raws[3]),
    )
    render_plan = copy.deepcopy(plan)
    mode = "fixed_baseline" if args.fixed_baseline else "planned"
    if args.fixed_baseline:
        for decision in render_plan["decisions"]:
            decision["selected_candidate_id"] = policy["initial_candidate_id"]
    graph, video_label, audio_label = build_bounded_story_filter_graph(
        render_plan, grid, width=args.width, height=args.height,
    )
    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{args.output_directory.name}.",
                                      dir=args.output_directory.parent))
    try:
        output = temporary / "video.mp4"
        subprocess.run([
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(args.source_video), "-filter_complex", graph,
            "-map", video_label, "-map", audio_label,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", str(output),
        ], check=True)
        trace = {
            "schema_version": "aegis360.bounded-story-segment-render.v1",
            "source_id": plan["source_id"],
            "mode": mode,
            "inputs": {"plan_sha256": digest(raws[4]),
                       "grid_sha256": digest(raws[2])},
            "window": plan["window"],
            "video": {"width": args.width, "height": args.height,
                      "codec": "libx264", "preset": "fast", "crf": 18,
                      "audio_codec": "aac", "audio_bitrate": "192k"},
            "privacy": {"contains_source_path": False, "contains_identity": False},
        }
        (temporary / "trace.json").write_text(
            json.dumps(trace, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        os.rename(temporary, args.output_directory)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    print(json.dumps({"decision_count": len(plan["decisions"]), "mode": mode}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
