#!/usr/bin/env python3
"""Run bounded independent-tile source-motion diagnostics on local ERP media."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.so3 import fit_rotation
from aegis360.tile_motion_evidence import TileHomography, fit_tile_motion
from aegis360.vision_homography import (
    vision_native_to_source_target_top_left,
)
from aegis360.viewport_rays import RectilinearViewport, ViewportTile


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def angle(quaternion) -> float:
    return 2.0 * math.acos(max(-1.0, min(1.0, abs(quaternion[3]))))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_erp", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--duration", type=float, required=True)
    arguments = parser.parse_args()
    if not arguments.input_erp.is_file():
        parser.error("input ERP does not exist")
    if arguments.output_dir.exists():
        parser.error("refusing to overwrite output directory")
    if arguments.start < 0 or arguments.duration <= 0:
        parser.error("invalid interval")

    config = load(arguments.config)
    parent = config["parentViewport"]
    tile_config = config["tiles"]
    fps = config["sampleFps"]
    expected_frames = math.ceil(arguments.duration * fps)
    if expected_frames < 2:
        parser.error("interval must contain at least two frames")
    started = time.monotonic()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    view_reports = {}

    with tempfile.TemporaryDirectory(prefix="aegis-real-tile-motion-") as raw:
        private = Path(raw)
        binary = private / "vision_motion_probe"
        run([
            "xcrun", "swiftc", str(ROOT / "tools/vision_motion_probe.swift"),
            "-o", str(binary),
        ])
        for view in config["viewports"]:
            view_dir = private / view["id"]
            parent_dir = view_dir / "parent"
            parent_dir.mkdir(parents=True)
            filter_graph = (
                f"fps={fps},v360=input=equirect:output=flat:"
                f"w={parent['width']}:h={parent['height']}:"
                f"yaw={view['yawDegrees']}:pitch={view['pitchDegrees']}:"
                f"h_fov={parent['horizontalFovDegrees']}:interp=linear"
            )
            run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-ss", str(arguments.start), "-t", str(arguments.duration),
                "-i", str(arguments.input_erp), "-an", "-vf", filter_graph,
                "-start_number", "0", str(parent_dir / "%06d.png"),
            ])
            if len(list(parent_dir.glob("*.png"))) != expected_frames:
                raise RuntimeError(f"{view['id']}: unexpected parent frame count")

            evidence_by_tile = {}
            tile_extents = {}
            for row in range(tile_config["rows"]):
                for column in range(tile_config["columns"]):
                    tile_id = f"r{row}c{column}"
                    x = column * tile_config["width"]
                    y = row * tile_config["height"]
                    tile = ViewportTile(
                        x, y, tile_config["width"], tile_config["height"]
                    )
                    tile_extents[tile_id] = tile
                    frames_dir = view_dir / tile_id
                    frames_dir.mkdir()
                    run([
                        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-framerate", str(fps),
                        "-i", str(parent_dir / "%06d.png"),
                        "-vf", f"crop={tile.width}:{tile.height}:{x}:{y}",
                        "-frames:v", str(expected_frames),
                        str(frames_dir / "%06d.png"),
                    ])
                    frames = sorted(frames_dir.glob("*.png"))
                    probe_input = {
                        "sourceId": (
                            f"{arguments.source_id}-{view['id']}-{tile_id}"
                        ),
                        "frameWidth": tile.width,
                        "frameHeight": tile.height,
                        "frames": [
                            {
                                "image": str(path),
                                "timestampSeconds": index / fps,
                            }
                            for index, path in enumerate(frames)
                        ],
                    }
                    input_path = view_dir / f"{tile_id}-input.json"
                    output_path = view_dir / f"{tile_id}-evidence.json"
                    input_path.write_text(json.dumps(probe_input))
                    run([str(binary), str(input_path), str(output_path)])
                    evidence_by_tile[tile_id] = load(output_path)

            viewport = RectilinearViewport(
                parent["width"], parent["height"],
                math.radians(view["yawDegrees"]),
                math.radians(view["pitchDegrees"]),
                math.radians(parent["horizontalFovDegrees"]),
            )
            pairs = []
            for index in range(1, expected_frames):
                observations = []
                unavailable = False
                for tile_id in sorted(evidence_by_tile):
                    observation = evidence_by_tile[tile_id]["observations"][index]
                    if observation["state"] != "measured":
                        unavailable = True
                        break
                    converted = vision_native_to_source_target_top_left(
                        observation["homographyRowMajor"],
                        tile_extents[tile_id].height,
                    )
                    observations.append(TileHomography(
                        tile_id, tile_extents[tile_id], converted
                    ))
                if unavailable:
                    pairs.append({"state": "invalid",
                                  "failure_reason": "vision_tile_unavailable"})
                    continue
                fitted = fit_tile_motion(
                    observations, viewport,
                    homography_columns=config["tileFit"]["homographyColumns"],
                    homography_rows=config["tileFit"]["homographyRows"],
                    maximum_disagreement_radians=math.radians(
                        config["tileFit"]["maximumDisagreementDegrees"]
                    ),
                    minimum_tiles=config["tileFit"]["minimumTiles"],
                    coverage_columns=config["tileFit"]["coverageColumns"],
                    coverage_rows=config["tileFit"]["coverageRows"],
                    minimum_covered_cells=config["tileFit"]["minimumCoveredCells"],
                )
                if fitted.consensus.state != "selected":
                    pairs.append({
                        "state": "invalid",
                        "failure_reason": fitted.consensus.failure_reason,
                        "selected_tile_ids": fitted.consensus.selected_tile_ids,
                    })
                    continue
                # Vision conversion gives previous->current. Source motion is
                # current->previous, so reverse every selected ray pair.
                fused = fit_rotation([
                    (target, source)
                    for source, target in fitted.selected_correspondences
                ])
                bounds = config["fusedFit"]
                failure = None
                if angle(fused.rotation_xyzw) > math.radians(
                    bounds["maxStepRotationDegrees"]
                ):
                    failure = "rotation_step_exceeds_configured_bound"
                elif fused.confidence < bounds["minimumFitConfidence"]:
                    failure = "rotation_fit_confidence_below_bound"
                elif fused.inlier_ratio < bounds["minimumInlierRatio"]:
                    failure = "rotation_fit_inlier_ratio_below_bound"
                elif fused.residual_radians > math.radians(
                    bounds["maximumFitResidualDegrees"]
                ):
                    failure = "rotation_fit_residual_exceeds_bound"
                pairs.append({
                    "state": "measured" if failure is None else "invalid",
                    "failure_reason": failure,
                    "selected_tile_ids": fitted.consensus.selected_tile_ids,
                    "step_rotation_radians": angle(fused.rotation_xyzw),
                    "residual_radians": fused.residual_radians,
                })
            reasons = {}
            for pair in pairs:
                if pair["failure_reason"]:
                    reasons[pair["failure_reason"]] = (
                        reasons.get(pair["failure_reason"], 0) + 1
                    )
            view_reports[view["id"]] = {
                "pair_count": len(pairs),
                "measured_pair_count": sum(
                    pair["state"] == "measured" for pair in pairs
                ),
                "failure_reasons": reasons,
                "pairs": pairs,
            }
            shutil.rmtree(view_dir)

    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    report = {
        "schema_version": "aegis360.real-erp-tile-motion-report.v1",
        "source_id": arguments.source_id,
        "config_id": config["configId"],
        "interval": {
            "start_seconds": arguments.start,
            "duration_seconds": arguments.duration,
            "sample_fps": fps,
        },
        "viewports": view_reports,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "elapsed_seconds": time.monotonic() - started,
            "child_max_rss_bytes": max(
                usage_before.ru_maxrss, usage_after.ru_maxrss
            ),
        },
        "privacy": {
            "contains_source_paths": False,
            "contains_pixels": False,
            "contains_identity_data": False,
        },
        "limitations": [
            "Analysis-only per-viewport tile diagnostic; no multiview path.",
            "No viewer video was rendered.",
            "Visual registration is not gyro ground truth.",
        ],
    }
    arguments.output_dir.mkdir(parents=True)
    (arguments.output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps({
        viewport_id: {
            "measured": value["measured_pair_count"],
            "pairs": value["pair_count"],
            "failures": value["failure_reasons"],
        }
        for viewport_id, value in view_reports.items()
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
