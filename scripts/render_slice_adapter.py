#!/usr/bin/env python3
"""Render the three artifacts required by aegis360.render-request.v1."""

from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.camera_path import (  # noqa: E402
    camera_path_document_to_keyframes,
    format_ffmpeg_sendcmd,
    interpolate_path,
)


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "schema_version",
    "source_media",
    "camera_path",
    "trace",
    "start_seconds",
    "duration_seconds",
    "artifacts",
}
ARTIFACTS = {"fixed", "auto", "debug"}


def fail(message: str, code: int = 1) -> None:
    print(f"render adapter: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {label}: {error}")
    if not isinstance(value, dict):
        fail(f"{label} must be a JSON object")
    return value


def finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def media_fps(source: Path) -> float:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate", "-of", "default=nw=1:nk=1",
            str(source),
        ],
        text=True, capture_output=True,
    )
    if completed.returncode:
        fail("ffprobe could not inspect the source video stream")
    try:
        numerator, denominator = completed.stdout.strip().split("/", 1)
        fps = float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        fail("source video has no usable average frame rate")
    if not math.isfinite(fps) or fps <= 0:
        fail("source video frame rate must be finite and positive")
    return fps


def trace_tsv(trace: dict[str, object], duration: float) -> str:
    decisions = trace.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        fail("trace requires a non-empty decisions array")
    timestamps: list[float] = []
    rows: list[tuple[float, float, float, str]] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            fail("trace decisions must be objects")
        timestamp = decision.get("timestamp")
        selected_id = decision.get("selected_candidate_id")
        candidates = decision.get("candidates")
        reason = decision.get("reason")
        if not finite_number(timestamp) or not isinstance(selected_id, str):
            fail("trace decision timestamp or selected candidate is invalid")
        if not isinstance(reason, str) or not isinstance(candidates, list):
            fail("trace decision reason or candidates are invalid")
        selected = next(
            (
                item for item in candidates
                if isinstance(item, dict) and item.get("candidate_id") == selected_id
            ),
            None,
        )
        if selected is None:
            fail("trace selected candidate geometry is missing")
        values = (
            selected.get("yaw_radians"),
            selected.get("pitch_radians"),
            selected.get("utility"),
        )
        if not all(finite_number(value) for value in values):
            fail("trace selected candidate values must be finite")
        timestamps.append(float(timestamp))
        rows.append((math.degrees(values[0]), math.degrees(values[1]), values[2], reason))
    if any(second <= first for first, second in zip(timestamps, timestamps[1:])):
        fail("trace decision timestamps must be strictly increasing")
    origin = timestamps[0]
    output = ["start\tend\tyaw\tpitch\tutility\treason"]
    for index, (yaw, pitch, utility, reason) in enumerate(rows):
        start = timestamps[index] - origin
        end = timestamps[index + 1] - origin if index + 1 < len(rows) else duration
        if start < 0 or end <= start or end > duration + 1e-9:
            fail("trace decisions do not fit the requested duration")
        clean_reason = reason.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        output.append(
            f"{start:.9f}\t{end:.9f}\t{yaw:.6f}\t{pitch:.6f}\t"
            f"{utility:.9f}\t{clean_reason}"
        )
    return "\n".join(output) + "\n"


def main() -> None:
    if len(sys.argv) != 2:
        fail(f"usage: {sys.argv[0]} REQUEST.json", 2)
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            fail(f"{tool} is required")

    request = load_object(Path(sys.argv[1]), "request")
    missing = REQUIRED - request.keys()
    if missing:
        fail("incomplete request; missing: " + ", ".join(sorted(missing)), 2)
    if request["schema_version"] != "aegis360.render-request.v1":
        fail("unsupported request schema version", 2)
    start, duration = request["start_seconds"], request["duration_seconds"]
    if (
        not finite_number(start) or start < 0
        or not finite_number(duration) or duration <= 0
    ):
        fail("start_seconds and duration_seconds are invalid", 2)

    source = Path(request["source_media"]) if isinstance(request["source_media"], str) else Path()
    camera_file = Path(request["camera_path"]) if isinstance(request["camera_path"], str) else Path()
    trace_file = Path(request["trace"]) if isinstance(request["trace"], str) else Path()
    artifacts = request["artifacts"]
    if not source.is_file() or not camera_file.is_file() or not trace_file.is_file():
        fail("source_media, camera_path, and trace must be existing files", 2)
    if not isinstance(artifacts, dict) or set(artifacts) != ARTIFACTS:
        fail("artifacts must contain exactly fixed, auto, and debug", 2)
    if not all(isinstance(value, str) and value for value in artifacts.values()):
        fail("artifact paths must be non-empty strings", 2)
    outputs = {name: Path(path) for name, path in artifacts.items()}
    if len(set(outputs.values())) != 3:
        fail("artifact paths must be distinct", 2)
    for output in outputs.values():
        if not output.parent.is_dir():
            fail(f"artifact parent directory does not exist: {output.parent}", 2)
        if output.exists():
            fail(f"refusing to overwrite artifact: {output}", 2)

    try:
        camera = camera_path_document_to_keyframes(load_object(camera_file, "camera path"))
        if camera[-1].time > duration + 1e-9:
            fail("camera path extends beyond requested duration", 2)
        fps = media_fps(source)
        commands = format_ffmpeg_sendcmd(interpolate_path(camera, fps))
        overlay = trace_tsv(load_object(trace_file, "trace"), float(duration))
    except (TypeError, ValueError) as error:
        fail(str(error), 2)

    with tempfile.TemporaryDirectory(prefix="aegis-render-adapter.") as temporary:
        temp = Path(temporary)
        commands_file = temp / "camera.sendcmd"
        overlay_file = temp / "trace.tsv"
        commands_file.write_text(commands, encoding="utf-8")
        overlay_file.write_text(overlay, encoding="utf-8")
        try:
            subprocess.run(
                [
                    str(ROOT / "scripts/render_fixed_forward_baseline.sh"),
                    str(source), str(outputs["fixed"]), str(start), str(duration),
                    "0", "0", "90", "640", "360",
                ],
                check=True,
            )
            subprocess.run(
                [
                    str(ROOT / "scripts/render_dynamic_v360_proxy.sh"),
                    str(source), str(outputs["auto"]), str(commands_file),
                    str(start), str(duration),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable, str(ROOT / "scripts/render_debug_preview.py"),
                    str(outputs["auto"]), str(outputs["debug"]), str(overlay_file),
                ],
                check=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            for output in outputs.values():
                output.unlink(missing_ok=True)
            fail(f"render failed: {error}")


if __name__ == "__main__":
    main()
