#!/usr/bin/env python3
"""Run the bounded tracking gate for a manifest of short clips."""
import argparse
import json
import math
import os
import re
import subprocess
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
NUMBERS = ("startSeconds", "durationSeconds", "framesPerSecond",
           "viewportYawDegrees", "boxX", "boxY", "boxWidth", "boxHeight")


def fail(message):
    raise SystemExit(message)


def load_manifest(path):
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid manifest: {exc}")
    clips = manifest.get("clips")
    if manifest.get("schemaVersion") != 1 or not isinstance(clips, list) or not clips:
        fail("manifest must have schemaVersion 1 and a non-empty clips array")
    seen = set()
    for clip in clips:
        if not isinstance(clip, dict):
            fail("every clip must be an object")
        for key in ("clipId", "sourceId", "trackId"):
            value = clip.get(key)
            if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
                fail(f"{key} must be a non-empty privacy-safe identifier")
        if clip["clipId"] in seen:
            fail("clipId values must be unique")
        seen.add(clip["clipId"])
        if not isinstance(clip.get("inputVideo"), str) or not Path(clip["inputVideo"]).is_file():
            fail(f"input video not found for clip {clip['clipId']}")
        for key in NUMBERS:
            value = clip.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                fail(f"{key} must be finite for clip {clip['clipId']}")
        if clip["durationSeconds"] <= 0 or clip["framesPerSecond"] <= 0:
            fail("durationSeconds and framesPerSecond must be positive")
        for key in ("boxX", "boxY", "boxWidth", "boxHeight"):
            if not 0 <= clip[key] <= 1:
                fail(f"{key} must be between 0 and 1")
        if clip["boxWidth"] <= 0 or clip["boxHeight"] <= 0:
            fail("boxWidth and boxHeight must be positive")
        if clip["boxX"] + clip["boxWidth"] > 1 or clip["boxY"] + clip["boxHeight"] > 1:
            fail("initial box must fit within the normalized viewport")
    return clips


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    clips = load_manifest(args.manifest)
    if args.output_dir.exists():
        fail("refusing to overwrite output directory")
    args.output_dir.mkdir(parents=True)
    default_runner = Path(__file__).resolve().parent / "run_vision_tracking_gate.sh"
    runner = Path(os.environ.get("AEGIS_TRACKING_GATE_RUNNER", default_runner))
    if not runner.is_file():
        fail("tracking gate runner not found")

    rows = []
    for clip in clips:
        clip_dir = args.output_dir / "clips" / clip["clipId"]
        command = [str(runner), clip["inputVideo"], str(clip_dir),
                   clip["sourceId"], clip["trackId"],
                   *(str(clip[key]) for key in NUMBERS)]
        child = subprocess.run(command, text=True, capture_output=True)
        if child.returncode:
            fail(f"tracking gate failed for clip {clip['clipId']}")
        try:
            summary = json.loads(
                (clip_dir / "tracking.json").read_text(encoding="utf-8")
            )["summary"]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            fail(f"invalid tracking evidence for clip {clip['clipId']}: {type(exc).__name__}")
        rows.append({
            "clipId": clip["clipId"], "sourceId": clip["sourceId"],
            "trackId": clip["trackId"], "outcome": summary["outcome"],
            **{key: summary[key] for key in (
                "requestedFrameCount", "trackedFrameCount", "lostFrameCount",
                "errorFrameCount", "persistenceRatio",
                "maximumSphericalCenterStepRadians", "seamCrossingCount")},
        })

    requested = sum(row["requestedFrameCount"] for row in rows)
    tracked = sum(row["trackedFrameCount"] for row in rows)
    steps = [row["maximumSphericalCenterStepRadians"] for row in rows
             if row["maximumSphericalCenterStepRadians"] is not None]
    outcomes = {}
    for row in rows:
        outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
    report = {
        "schemaVersion": 1, "backendId": "VNTrackObjectRequest",
        "clipCount": len(rows), "clips": rows,
        "aggregate": {
            "outcomeCounts": outcomes, "requestedFrameCount": requested,
            "trackedFrameCount": tracked,
            "lostFrameCount": sum(row["lostFrameCount"] for row in rows),
            "errorFrameCount": sum(row["errorFrameCount"] for row in rows),
            "weightedPersistenceRatio": tracked / requested if requested else 0,
            "maximumSphericalCenterStepRadians": max(steps) if steps else None,
            "seamCrossingCount": sum(row["seamCrossingCount"] for row in rows),
        },
        "limitations": [
            "Clip paths and media metadata are intentionally omitted from this privacy-safe report.",
            "Aggregate continuity does not establish subject identity, box accuracy, seam handoff, recall, or editorial value.",
            "Initial boxes and clip intervals are externally supplied rather than automatically selected.",
        ],
    }
    report_path = args.output_dir / "batch-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
