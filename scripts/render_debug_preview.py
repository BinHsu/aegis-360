#!/usr/bin/env python3
"""Burn a compact decision trace into an already-rendered auto preview."""

from __future__ import annotations

import csv
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont


def fail(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


if len(sys.argv) != 4:
    fail(f"usage: {sys.argv[0]} AUTO.mp4 OUTPUT.mp4 TRACE.tsv", 2)

source, output, trace = map(Path, sys.argv[1:])
if output.exists():
    fail(f"refusing to overwrite existing output: {output}")
if not source.is_file():
    fail(f"input not found: {source}")
if not trace.is_file():
    fail(f"trace not found: {trace}")
for tool in ("ffmpeg",):
    if shutil.which(tool) is None:
        fail(f"{tool} is required")

rows: list[tuple[float, float, str]] = []
with trace.open(newline="", encoding="utf-8") as handle:
    reader = csv.DictReader(handle, delimiter="\t")
    required = {"start", "end", "yaw", "pitch", "utility", "reason"}
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        fail("trace must have TSV columns: start end yaw pitch utility reason")
    for row in reader:
        try:
            start, end = float(row["start"]), float(row["end"])
            yaw, pitch, utility = (
                float(row["yaw"]),
                float(row["pitch"]),
                float(row["utility"]),
            )
        except (TypeError, ValueError):
            fail("trace contains a non-numeric time, pose, or utility")
        if not all(map(math.isfinite, (start, end, yaw, pitch, utility))):
            fail("trace numeric values must be finite")
        if start < 0 or end <= start:
            fail("trace intervals must satisfy 0 <= start < end")
        reason = row["reason"].replace("\n", " ").replace("\r", " ")
        rows.append(
            (
                start,
                end,
                f"selected yaw={yaw:.1f}  pitch={pitch:.1f}  "
                f"utility={utility:.3f}  reason={reason}",
            )
        )
if not rows:
    fail("trace must contain at least one interval")

with tempfile.TemporaryDirectory(prefix="aegis-debug-preview.") as tmp:
    inputs: list[str] = []
    filters: list[str] = []
    previous = "[0:v:0]"
    font = ImageFont.load_default(size=18)
    for index, (start, end, label) in enumerate(rows, 1):
        image = Image.new("RGBA", (640, 42), (0, 0, 0, 190))
        ImageDraw.Draw(image).text((10, 10), label, fill=(255, 255, 255, 255), font=font)
        image_path = Path(tmp) / f"label-{index:04d}.png"
        image.save(image_path)
        inputs.extend(("-i", str(image_path)))
        current = f"[debug{index}]"
        filters.append(
            f"{previous}[{index}:v:0]overlay=x=0:y=0:"
            f"enable='between(t,{start:.9f},{end:.9f})'{current}"
        )
        previous = current

    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(source),
        *inputs, "-filter_complex", ";".join(filters), "-map", previous,
        "-map", "0:a:0", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
        str(output),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        output.unlink(missing_ok=True)
        fail(f"ffmpeg debug preview render failed ({completed.returncode})")
