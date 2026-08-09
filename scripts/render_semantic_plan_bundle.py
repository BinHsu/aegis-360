#!/usr/bin/env python3
"""Render a semantic planning directory into one atomic review bundle."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


PLAN_FILES = ("trace.json", "config.json", "camera-path.json", "planning-gate.json")
MEDIA_FILES = {
    "fixed": "fixed-forward.mp4",
    "auto": "auto-directed.mp4",
    "debug": "debug-overlay.mp4",
}


def strict_dump(value: object) -> str:
    return json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"


def load_object(path: Path, label: str) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan_directory", type=Path)
    parser.add_argument("source_media", type=Path)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument(
        "--render-adapter",
        type=Path,
        default=Path(__file__).resolve().parent / "render_slice_adapter.py",
    )
    parser.add_argument("--output-width", type=int, default=1920)
    parser.add_argument("--output-height", type=int, default=1080)
    args = parser.parse_args()

    if args.output_directory.exists():
        parser.error("refusing to overwrite output directory")
    if not args.source_media.is_file():
        parser.error("source media is missing")
    if not args.render_adapter.is_file():
        parser.error("render adapter is missing")
    if args.output_width <= 0 or args.output_height <= 0:
        parser.error("output dimensions must be positive")
    missing = [name for name in PLAN_FILES if not (args.plan_directory / name).is_file()]
    if missing:
        parser.error("planning directory is incomplete: " + ", ".join(missing))

    config = load_object(args.plan_directory / "config.json", "config")
    gate = load_object(args.plan_directory / "planning-gate.json", "planning gate")
    if config.get("schema_version") != "aegis360.semantic-plan-config.v1":
        parser.error("unsupported semantic plan config")
    if config.get("render_contract") != "shot_static_v360_only":
        parser.error("semantic plan does not permit the required render mode")
    if gate.get("schema_version") != "aegis360.semantic-planning-gate.v1":
        parser.error("unsupported semantic planning gate")
    if gate.get("passed_pose_differentiation") is not True:
        parser.error("semantic plan did not pass pose differentiation")
    slice_config = config.get("slice")
    greedy_config = config.get("versioned_greedy_config")
    if not isinstance(slice_config, dict) or not isinstance(greedy_config, dict):
        parser.error("semantic plan config is incomplete")
    camera_config = greedy_config.get("camera")
    if not isinstance(camera_config, dict):
        parser.error("semantic plan camera config is incomplete")

    args.output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{args.output_directory.name}.", dir=args.output_directory.parent,
    ))
    try:
        for name in PLAN_FILES:
            shutil.copy2(args.plan_directory / name, staging / name)
        artifacts = {key: str(staging / name) for key, name in MEDIA_FILES.items()}
        request = {
            "schema_version": "aegis360.render-request.v1",
            "source_media": str(args.source_media.resolve()),
            "camera_path": str((staging / "camera-path.json").resolve()),
            "trace": str((staging / "trace.json").resolve()),
            "start_seconds": slice_config.get("start_seconds"),
            "duration_seconds": slice_config.get("duration_seconds"),
            "render_mode": "shot_static_v360",
            "output_width": args.output_width,
            "output_height": args.output_height,
            "framing_safety": camera_config.get("framing_safety"),
            "artifacts": artifacts,
        }
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="aegis-semantic-render.", suffix=".json",
        ) as handle:
            handle.write(strict_dump(request))
            handle.flush()
            subprocess.run([str(args.render_adapter), handle.name], check=True)
        omitted = [key for key, path in artifacts.items() if not Path(path).is_file()]
        if omitted:
            raise RuntimeError("render adapter omitted artifacts: " + ", ".join(omitted))
        manifest = {
            "schema_version": "aegis360.slice-artifacts.v1",
            "status": "complete",
            "artifacts": {
                **{
                    key: {"path": name, "exists": True}
                    for key, name in MEDIA_FILES.items()
                },
                **{
                    name.removesuffix(".json").replace("-", "_"): {
                        "path": name, "exists": True,
                    }
                    for name in PLAN_FILES
                },
            },
            "privacy": {"contains_source_path": False, "contains_pixels": True},
        }
        (staging / "artifacts.json").write_text(strict_dump(manifest), encoding="utf-8")
        os.rename(staging, args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(args.output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
