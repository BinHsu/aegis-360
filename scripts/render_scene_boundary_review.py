#!/usr/bin/env python3
"""Render one atomic silent 2x2 cardinal scene-boundary review bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.multi_signal_review_packet import validate_multi_signal_review_packet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_video", type=Path)
    parser.add_argument("timeline_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("packet_json", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    if not all(path.is_file() for path in (
        args.source_video, args.timeline_json, args.grid_json, args.packet_json,
    )):
        parser.error("source or evidence is missing")
    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    timeline_bytes = args.timeline_json.read_bytes()
    grid_bytes = args.grid_json.read_bytes()
    packet_bytes = args.packet_json.read_bytes()
    timeline, grid, packet = map(json.loads, (timeline_bytes, grid_bytes, packet_bytes))
    validate_multi_signal_review_packet(
        packet, timeline, grid,
        timeline_sha256=hashlib.sha256(timeline_bytes).hexdigest(),
        grid_sha256=hashlib.sha256(grid_bytes).hexdigest(),
    )
    candidates = grid["candidates"]
    if len(candidates) != 4 or packet["event"]["review_scope"]["mode"] != "all_declared_candidates":
        parser.error("scene-boundary review requires four neutral candidates")
    start = packet["event"]["start_seconds"]
    duration = packet["event"]["end_seconds"] - start
    filters = ["[0:v:0]split=4[v0][v1][v2][v3]"]
    for index, candidate in enumerate(candidates):
        filters.append(
            f"[v{index}]v360=input=equirect:output=flat:w=640:h=360:"
            f"yaw={candidate['yaw_degrees']}:pitch={candidate['pitch_degrees']}:"
            f"h_fov={candidate['horizontal_fov_degrees']}:interp=linear[o{index}]"
        )
    filters.extend(["[o0][o1]hstack=inputs=2[top]", "[o2][o3]hstack=inputs=2[bottom]",
                    "[top][bottom]vstack=inputs=2[out]"])
    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{args.output_directory.name}.", dir=args.output_directory.parent))
    try:
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(start), "-t", str(duration), "-i", str(args.source_video),
            "-filter_complex", ";".join(filters), "-map", "[out]", "-an",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(staging / "video.mp4"),
        ], check=True)
        trace = {
            "schema_version": "aegis360.scene-boundary-review-render.v1",
            "source_id": packet["source_id"], "event_id": packet["event_id"],
            "inputs": {"timeline_sha256": hashlib.sha256(timeline_bytes).hexdigest(),
                       "grid_sha256": hashlib.sha256(grid_bytes).hexdigest(),
                       "packet_sha256": hashlib.sha256(packet_bytes).hexdigest()},
            "window": {"start_seconds": start, "duration_seconds": duration},
            "layout": {"top_left": candidates[0]["candidate_id"],
                       "top_right": candidates[1]["candidate_id"],
                       "bottom_left": candidates[2]["candidate_id"],
                       "bottom_right": candidates[3]["candidate_id"]},
            "video": {"width": 1280, "height": 720, "audio_present": False,
                      "codec": "libx264", "preset": "fast", "crf": 18},
            "privacy": {"contains_source_path": False, "contains_identity": False,
                        "contains_editorial_decision": False},
        }
        (staging / "trace.json").write_text(
            json.dumps(trace, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.rename(staging, args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(args.output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
