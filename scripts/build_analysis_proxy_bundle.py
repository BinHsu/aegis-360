#!/usr/bin/env python3
"""Create the canonical FFV1 analysis proxy as an atomic bundle."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.analysis_proxy_bundle import (  # noqa: E402
    build_analysis_proxy_bundle,
    validate_analysis_proxy_bundle,
    validate_analysis_proxy_config,
)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def probe(path, video_only=False):
    command = ["ffprobe", "-v", "error"]
    if video_only:
        command += ["-select_streams", "v:0"]
    command += [
        "-show_entries",
        (
            "stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,"
            "time_base,start_pts,start_time,duration,sample_aspect_ratio,"
            "color_range,color_space,color_transfer,color_primaries:"
            "format=format_name,duration"
        ),
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("source_id")
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--start-seconds")
    parser.add_argument("--duration-seconds")
    return parser, parser.parse_args()


def main():
    parser, args = parse_args()
    if not args.source.is_file() or not args.config.is_file():
        parser.error("required input is missing")
    if args.output.exists():
        parser.error("refusing to overwrite output directory")
    if (args.start_seconds is None) != (args.duration_seconds is None):
        parser.error("start and duration must appear together")

    try:
        start = Fraction(args.start_seconds or "0")
        duration = (
            None
            if args.duration_seconds is None
            else Fraction(args.duration_seconds)
        )
    except (ValueError, ZeroDivisionError):
        parser.error("bounded interval is invalid")
    if start < 0 or duration is not None and duration <= 0:
        parser.error("bounded interval is invalid")

    raw_config = args.config.read_bytes()
    config = json.loads(raw_config)
    validate_analysis_proxy_config(config)
    source_sha256 = sha(args.source)
    source_probe = probe(args.source, video_only=True)
    source_streams = source_probe.get("streams", [])
    selected_source_is_valid = (
        len(source_streams) == 1
        and source_streams[0].get("codec_type") == "video"
        and source_streams[0].get("start_pts") is not None
        and source_streams[0].get("time_base") is not None
    )
    if not selected_source_is_valid:
        parser.error("source selected video timing is unavailable")

    output_parent = args.output.parent
    output_parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{args.output.name}.", dir=output_parent)
    )
    began = time.monotonic()
    try:
        proxy = stage / "analysis-proxy.mkv"
        command = [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-threads",
            "2",
            "-i",
            str(args.source),
        ]
        if duration is not None:
            command += [
                "-ss",
                args.start_seconds,
                "-t",
                args.duration_seconds,
            ]
        command += [
            "-map",
            "0:v:0",
            "-an",
            "-vf",
            (
                "fps=10/1,scale=960:480:flags=lanczos,format=yuv420p,"
                "setsar=1/1,setpts=PTS-STARTPTS"
            ),
            "-c:v",
            "ffv1",
            "-f",
            "matroska",
            str(proxy),
        ]
        subprocess.run(command, check=True)

        if sha(args.source) != source_sha256:
            raise RuntimeError("source changed during proxy acquisition")

        proxy_probe = probe(proxy)
        proxy_streams = proxy_probe.get("streams", [])
        if (
            len(proxy_streams) != 1
            or proxy_streams[0].get("codec_type") != "video"
        ):
            raise ValueError("proxy must contain one video and zero audio streams")

        stream = proxy_streams[0]
        colors = {
            key: stream.get(key) or "unknown"
            for key in (
                "color_range",
                "color_space",
                "color_transfer",
                "color_primaries",
            )
        }
        normalized_probe = {
            "stream_count": 1,
            "stream_types": [stream.get("codec_type")],
            "codec_name": stream.get("codec_name"),
            "width": stream.get("width"),
            "height": stream.get("height"),
            "pixel_format": stream.get("pix_fmt"),
            "frame_rate": stream.get("r_frame_rate"),
            "time_base": stream.get("time_base"),
            "start_pts": int(stream.get("start_pts")),
            "start_time_seconds": float(stream.get("start_time")),
            "duration_seconds": float(
                stream.get("duration")
                or proxy_probe.get("format", {}).get("duration")
            ),
            "sample_aspect_ratio": stream.get("sample_aspect_ratio"),
            "format_name": proxy_probe.get("format", {}).get("format_name"),
            **colors,
        }
        time_base_numerator, time_base_denominator = map(
            int, source_streams[0]["time_base"].split("/")
        )
        source_interval = {
            "start": {
                "numerator": start.numerator,
                "denominator": start.denominator,
            },
            "duration": (
                None
                if duration is None
                else {
                    "numerator": duration.numerator,
                    "denominator": duration.denominator,
                }
            ),
        }
        runtime = {
            "elapsed_seconds": time.monotonic() - began,
            "output_bytes": proxy.stat().st_size,
        }
        bundle_inputs = {
            "source_id": args.source_id,
            "source_sha256": source_sha256,
            "config": config,
            "config_sha256": hashlib.sha256(raw_config).hexdigest(),
            "proxy_sha256": sha(proxy),
            "source_timing": {
                "first_pts": int(source_streams[0]["start_pts"]),
                "time_base_numerator": time_base_numerator,
                "time_base_denominator": time_base_denominator,
            },
            "source_interval": source_interval,
            "probe": normalized_probe,
            "runtime": runtime,
        }
        manifest = build_analysis_proxy_bundle(**bundle_inputs)
        validate_analysis_proxy_bundle(manifest, **bundle_inputs)
        (stage / "manifest.json").write_text(
            json.dumps(manifest, allow_nan=False, indent=2, sort_keys=True) + "\n"
        )
        os.rename(stage, args.output)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
