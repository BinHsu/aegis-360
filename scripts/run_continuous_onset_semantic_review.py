#!/usr/bin/env python3
"""Render one exact continuous-onset packet, invoke an adapter, then clean up."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.continuous_onset_semantic_packet import (  # noqa: E402
    validate_continuous_onset_semantic_packet,
)
from aegis360.context_views import validate_context_view_grid  # noqa: E402


def _jobs(packet: dict, grid: dict, *, width: int, height: int) -> list[dict]:
    if (isinstance(width, bool) or isinstance(height, bool)
            or not 64 <= width <= 960 or not 64 <= height <= 540):
        raise ValueError("onset review viewport dimensions are outside the bounded range")
    validate_context_view_grid(grid)
    candidates = {item["candidate_id"]: item for item in grid["candidates"]}
    expected_ids = list(candidates)
    jobs = []
    for sample in packet["samples"]:
        if not sample["available"]:
            if any(sample[key] is not None for key in (
                    "row_index", "timestamp_seconds",
                    "acquisition_interval_pts_seconds", "normalized_difference")):
                raise ValueError("unavailable onset sample must remain null")
            continue
        if (sample["representation"] != "four_cardinal_contact_sheet"
                or sample["candidate_ids"] != expected_ids):
            raise ValueError("onset review sample candidates are invalid")
        jobs.append({
            "sample_id": sample["sample_id"],
            "temporal_role": sample["temporal_role"],
            "timestamp_seconds": sample["timestamp_seconds"],
            "normalized_difference": sample["normalized_difference"],
            "viewports": [candidates[candidate_id] for candidate_id in expected_ids],
            "viewport_width": width, "viewport_height": height,
            "width": width * 2, "height": height * 2,
            "filename": f"{sample['sample_id'].replace(':', '-')}-cardinal-contact.png",
        })
    if not 1 <= len(jobs) <= 5:
        raise ValueError("onset review jobs exceed the bounded contract")
    return jobs


def _index(packet: dict, jobs: list[dict]) -> dict:
    return {
        "schema_version": "aegis360.transient-continuous-onset-review-media-index.v1",
        "source_id": packet["source_id"],
        "onset_candidate_id": packet["candidate_id"],
        "audio_provided": False,
        "frames": [{
            "sample_id": job["sample_id"],
            "temporal_role": job["temporal_role"],
            "timestamp_seconds": job["timestamp_seconds"],
            "normalized_difference": job["normalized_difference"],
            "representation": "four_cardinal_contact_sheet",
            "candidate_ids": [item["candidate_id"] for item in job["viewports"]],
            "width": job["width"], "height": job["height"],
            "filename": job["filename"],
        } for job in jobs],
        "lifecycle": "temporary_directory_deleted_after_adapter_exit",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_video", type=Path)
    parser.add_argument("onset_json", type=Path)
    parser.add_argument("samples_json", type=Path)
    parser.add_argument("grid_json", type=Path)
    parser.add_argument("packet_json", type=Path)
    parser.add_argument("--width", type=int, default=384)
    parser.add_argument("--height", type=int, default=216)
    parser.add_argument("adapter_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    paths = (args.source_video, args.onset_json, args.samples_json,
             args.grid_json, args.packet_json)
    if not all(path.is_file() for path in paths):
        parser.error("source or continuous-onset evidence is missing")
    if not args.adapter_command:
        parser.error("adapter command is required after --")
    command = (args.adapter_command[1:] if args.adapter_command[0] == "--"
               else args.adapter_command)
    if not command:
        parser.error("adapter command is empty")

    onset_raw = args.onset_json.read_bytes()
    samples_raw = args.samples_json.read_bytes()
    grid_raw = args.grid_json.read_bytes()
    onset, samples, grid = map(json.loads, (onset_raw, samples_raw, grid_raw))
    packet = json.loads(args.packet_json.read_bytes())
    validate_continuous_onset_semantic_packet(
        packet, onset, samples, grid,
        onset_sha256=hashlib.sha256(onset_raw).hexdigest(),
        samples_sha256=hashlib.sha256(samples_raw).hexdigest(),
        grid_sha256=hashlib.sha256(grid_raw).hexdigest())
    jobs = _jobs(packet, grid, width=args.width, height=args.height)

    work = None
    with tempfile.TemporaryDirectory(prefix="aegis-onset-review.") as temporary:
        work = Path(temporary)
        for job in jobs:
            labels = ("a", "b", "c", "d")
            filters = ["split=4[a][b][c][d]"]
            for label, viewport in zip(labels, job["viewports"], strict=True):
                filters.append(
                    f"[{label}]v360=input=equirect:output=flat:"
                    f"w={job['viewport_width']}:h={job['viewport_height']}:"
                    f"yaw={viewport['yaw_degrees']}:pitch={viewport['pitch_degrees']}:"
                    f"h_fov={viewport['horizontal_fov_degrees']}:interp=linear[{label}0]")
            filters.append(
                f"[a0][b0][c0][d0]xstack=inputs=4:layout=0_0|{job['viewport_width']}_0|"
                f"0_{job['viewport_height']}|{job['viewport_width']}_{job['viewport_height']}")
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(job["timestamp_seconds"]), "-i", str(args.source_video),
                "-frames:v", "1", "-filter_complex", ";".join(filters),
                "-an", str(work / job["filename"]),
            ], check=True)
        index_path = work / "index.json"
        index_path.write_text(json.dumps(_index(packet, jobs), indent=2,
                                         sort_keys=True) + "\n", encoding="utf-8")
        environment = os.environ.copy()
        environment["AEGIS_REVIEW_MEDIA_DIR"] = str(work)
        environment["AEGIS_REVIEW_MEDIA_INDEX"] = str(index_path)
        completed = subprocess.run(command, cwd=work, env=environment, check=False)
        returncode = completed.returncode
    if work is None or work.exists():
        raise RuntimeError("transient onset review directory was not deleted")
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
