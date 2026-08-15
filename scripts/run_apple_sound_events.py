#!/usr/bin/env python3
"""Extract bounded temporary PCM and emit path-free Apple sound events."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.sound_events import validate_sound_events  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_video", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start-seconds", required=True, type=float)
    parser.add_argument("--duration-seconds", required=True, type=float)
    args = parser.parse_args()
    if not args.input_video.is_file():
        parser.error("input video is missing")
    if args.output_json.exists():
        parser.error("refusing to overwrite output")
    if (
        not math.isfinite(args.start_seconds) or args.start_seconds < 0
        or not math.isfinite(args.duration_seconds)
        or not 0 < args.duration_seconds <= 300
    ):
        parser.error("analysis window must be finite, positive and at most 300 seconds")
    root = Path(__file__).resolve().parents[1]
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aegis-sound-events-") as work:
        work_dir = Path(work)
        pcm, binary, raw = work_dir / "audio.wav", work_dir / "sound_event_gate", work_dir / "raw.json"
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(args.start_seconds), "-t", str(args.duration_seconds),
            "-i", str(args.input_video), "-map", "0:a:0", "-vn", "-ac", "1",
            "-ar", "44100", "-c:a", "pcm_s16le", str(pcm),
        ], check=True)
        subprocess.run([
            "xcrun", "swiftc", str(root / "tools/sound_event_gate.swift"),
            "-o", str(binary),
        ], check=True)
        subprocess.run([str(binary), str(pcm), args.source_id, str(raw)], check=True)
        artifact = json.loads(raw.read_text(encoding="utf-8"))
        artifact["window"] = {
            "start_seconds": args.start_seconds,
            "duration_seconds": args.duration_seconds,
            "analysis_channel_count": 1,
            "analysis_sample_rate_hz": 44100,
        }
        for row in artifact["windows"]:
            row["start_seconds"] += args.start_seconds
        validate_sound_events(artifact)
        payload = json.dumps(artifact, allow_nan=False, indent=2, sort_keys=True) + "\n"
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=args.output_json.parent,
                prefix=f".{args.output_json.name}.", suffix=".tmp", delete=False,
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(payload)
            os.link(temporary_name, args.output_json)
            Path(temporary_name).unlink()
            temporary_name = None
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
