"""Bounded orchestration for one auto-directed analysis/render slice."""

from __future__ import annotations

from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

from .camera_path import greedy_trace_to_camera_path
from .candidate_sequence import AssociationConfig, associate_candidate_sequence
from .greedy_planner import (
    CandidateObservation,
    GreedyConfig,
    Observation,
    ScoreComponent,
    dumps_trace,
    plan_greedy_with_hysteresis,
)
from .interest import InterestConfig, evaluate_interest
from .greedy_config import GreedySliceConfig
from .spherical_dedup import SphericalDedupConfig, deduplicate_spherical_candidates, vision_gate_json_to_perception


SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")
ARTIFACT_NAMES = {
    "fixed": "fixed-forward.mp4",
    "auto": "auto-directed.mp4",
    "debug": "debug-overlay.mp4",
}


def _strict_dump(value: Any) -> str:
    return json.dumps(value, allow_nan=False, indent=2, sort_keys=True) + "\n"


def _observations(frames, weights: dict[str, float]) -> tuple[Observation, ...]:
    output = []
    for frame in frames:
        candidates = []
        for interested in frame.candidates:
            components = tuple(
                ScoreComponent(
                    signal.name,
                    signal.raw,
                    signal.normalized,
                    weights.get(signal.name, 0.0),
                    signal.provenance,
                )
                for signal in interested.signals
                if signal.normalized is not None
            )
            candidate = interested.candidate
            candidates.append(
                CandidateObservation(
                    candidate.candidate_id,
                    candidate.yaw,
                    candidate.pitch,
                    candidate.h_fov,
                    candidate.candidate_type,
                    components,
                )
            )
        output.append(Observation(frame.timestamp, tuple(candidates)))
    return tuple(output)


def run_slice(
    vision_document: str,
    output_dir: Path,
    *,
    source_id: str,
    width: int,
    height: int,
    start_seconds: float,
    duration_seconds: float,
    association: AssociationConfig = AssociationConfig(),
    dedup: SphericalDedupConfig = SphericalDedupConfig(),
    interest: InterestConfig = InterestConfig(),
    greedy: GreedyConfig = GreedyConfig(),
    weights: dict[str, float] | None = None,
    slice_config: GreedySliceConfig | None = None,
    render_adapter: Path | None = None,
    source_media: Path | None = None,
    render_mode: str = "dynamic",
) -> None:
    """Create a complete bundle atomically and never overwrite a prior run.

    A render adapter is an executable invoked as ``ADAPTER REQUEST.json``.  It
    must create all three paths in ``request["artifacts"]``.  The request is
    temporary and may contain the source path; persisted trace/config do not.
    """

    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite output bundle: {output_dir}")
    if not SAFE_ID.fullmatch(source_id):
        raise ValueError("source_id must be a privacy-safe job token")
    if render_mode not in {"dynamic", "shot_static_v360"}:
        raise ValueError("unsupported render_mode")
    if (
        not math.isfinite(start_seconds)
        or start_seconds < 0
        or not math.isfinite(duration_seconds)
        or duration_seconds <= 0
    ):
        raise ValueError("start_seconds must be nonnegative and duration_seconds positive")
    camera_threshold = math.radians(5.0)
    framing_safety = None
    persisted_slice_config = None
    if slice_config is not None:
        greedy = slice_config.planner
        weights = dict(slice_config.scoring.weights)
        camera_threshold = slice_config.camera_min_angular_change
        framing_safety = slice_config.framing_safety
        persisted_slice_config = slice_config.trace_config()
    weights = weights or {
        "presence": 0.40,
        "persistence": 0.30,
        "composition": 0.15,
        "forward_prior": 0.15,
    }
    if not weights or not all(
        name and math.isfinite(value) for name, value in weights.items()
    ):
        raise ValueError("interest weights must be named finite numbers")

    perception = vision_gate_json_to_perception(
        vision_document, width=width, height=height
    )
    if not perception:
        raise ValueError("Vision sequence contains no samples")
    document_source_ids = {item.sample.source_id for item in perception}
    if document_source_ids != {source_id}:
        raise ValueError("source_id does not match the Vision sequence")
    raw_document = json.loads(vision_document)
    sequence = raw_document.get("sequence")
    if sequence is not None:
        evidence_start = float(sequence.get("startSeconds"))
        evidence_duration = float(sequence.get("durationSeconds"))
        if not math.isclose(evidence_start, start_seconds, abs_tol=1e-9):
            raise ValueError("start_seconds does not match the Vision sequence")
        if not math.isclose(evidence_duration, duration_seconds, abs_tol=1e-9):
            raise ValueError("duration_seconds does not match the Vision sequence")
    deduped = tuple(deduplicate_spherical_candidates(item, dedup) for item in perception)
    associated = associate_candidate_sequence(
        tuple(item.result for item in deduped), association
    )
    scored = evaluate_interest(associated, interest)
    trace = plan_greedy_with_hysteresis(_observations(scored, weights), greedy)
    trace.update(
        {
            "source": {
                "source_id": source_id,
                "sample_width": width,
                "sample_height": height,
                "projection": "equirectangular",
            },
            "pipeline": {
                "ingest": "apple-vision-gate.v1",
                "spherical_dedup": "aegis360.spherical_dedup",
                "temporal_association": "aegis360.candidate_sequence",
                "interest": "aegis360.interest:v1",
            },
            "dedup": [
                {
                    "frame_index": result.result.sample.frame_index,
                    "input_candidates": sum(len(cluster.members) for cluster in result.clusters),
                    "output_candidates": len(result.clusters),
                }
                for result in deduped
            ],
        }
    )
    camera_path = greedy_trace_to_camera_path(
        trace,
        duration_seconds,
        direction_threshold=camera_threshold,
        framing_safety=framing_safety,
    )
    config = {
        "schema_version": "aegis360.slice-config.v1",
        "source_id": source_id,
        "dimensions": {"width": width, "height": height},
        "slice": {"start_seconds": start_seconds, "duration_seconds": duration_seconds},
        "association": asdict(association),
        "dedup": asdict(dedup),
        "interest": asdict(interest),
        "greedy": asdict(greedy),
        "interest_weights": dict(sorted(weights.items())),
        "versioned_greedy_config": persisted_slice_config,
        "privacy": {
            "contains_source_path": False,
            "contains_pixels": False,
            "job_scoped_candidate_ids": True,
        },
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        (staging / "trace.json").write_text(dumps_trace(trace), encoding="utf-8")
        (staging / "config.json").write_text(_strict_dump(config), encoding="utf-8")
        (staging / "camera-path.json").write_text(
            _strict_dump(camera_path), encoding="utf-8"
        )
        artifacts = {name: str(staging / filename) for name, filename in ARTIFACT_NAMES.items()}
        status = "planned"
        if render_adapter is not None:
            if source_media is None or not source_media.is_file():
                raise ValueError("render adapter requires an existing source_media")
            request = {
                "schema_version": "aegis360.render-request.v1",
                "source_media": str(source_media.resolve()),
                "camera_path": str((staging / "camera-path.json").resolve()),
                "trace": str((staging / "trace.json").resolve()),
                "start_seconds": start_seconds,
                "duration_seconds": duration_seconds,
                "render_mode": render_mode,
                "framing_safety": (
                    persisted_slice_config["camera"]["framing_safety"]
                    if persisted_slice_config is not None else None
                ),
                "artifacts": artifacts,
            }
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix="aegis-render-request.", suffix=".json"
            ) as handle:
                handle.write(_strict_dump(request))
                handle.flush()
                subprocess.run([str(render_adapter), handle.name], check=True)
            missing = [name for name, path in artifacts.items() if not Path(path).is_file()]
            if missing:
                raise RuntimeError("render adapter omitted artifacts: " + ", ".join(missing))
            status = "complete"
        manifest = {
            "schema_version": "aegis360.slice-artifacts.v1",
            "status": status,
            "artifacts": {
                **{name: {"path": filename, "exists": status == "complete"} for name, filename in ARTIFACT_NAMES.items()},
                "trace": {"path": "trace.json", "exists": True},
                "config": {"path": "config.json", "exists": True},
                "camera_path": {"path": "camera-path.json", "exists": True},
            },
        }
        (staging / "artifacts.json").write_text(_strict_dump(manifest), encoding="utf-8")
        os.rename(staging, output_dir)
    except BaseException:
        for child in staging.iterdir():
            child.unlink()
        staging.rmdir()
        raise
