"""Dependency-free ingestion and spherical cross-viewport candidate deduplication."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Mapping

from .geometry import direction_from_angles, spherical_distance, wrap_yaw
from .perception import (
    AdapterProvenance,
    FrameSample,
    PerceptionResult,
    SignalEvidence,
    SphericalCandidateEvidence,
)


@dataclass(frozen=True)
class SphericalDedupConfig:
    """Geometric duplicate gate; detector confidence is deliberately absent."""

    max_center_distance: float = math.radians(12.0)
    extent_overlap_scale: float = 0.6
    minimum_extent_gate: float = math.radians(2.0)

    def __post_init__(self) -> None:
        values = (
            self.max_center_distance,
            self.extent_overlap_scale,
            self.minimum_extent_gate,
        )
        if not all(math.isfinite(value) and value >= 0.0 for value in values):
            raise ValueError("dedup thresholds must be finite and nonnegative")
        if self.max_center_distance >= math.pi:
            raise ValueError("max_center_distance must be less than pi")


@dataclass(frozen=True)
class DuplicateCluster:
    """Merged candidate and every original observation that produced it."""

    candidate: SphericalCandidateEvidence
    members: tuple[SphericalCandidateEvidence, ...]


@dataclass(frozen=True)
class SphericalDedupResult:
    result: PerceptionResult
    clusters: tuple[DuplicateCluster, ...]


def _pair_gate(first, second, config: SphericalDedupConfig) -> bool:
    if first.candidate_type != second.candidate_type:
        return False
    extent_gate = max(
        config.minimum_extent_gate,
        config.extent_overlap_scale * (first.h_fov + second.h_fov) / 2.0,
    )
    threshold = min(config.max_center_distance, extent_gate)
    return spherical_distance((first.yaw, first.pitch), (second.yaw, second.pitch)) <= threshold


def _mean_direction(members) -> tuple[float, float]:
    directions = [direction_from_angles(item.yaw, item.pitch) for item in members]
    x = sum(item[0] for item in directions)
    y = sum(item[1] for item in directions)
    z = sum(item[2] for item in directions)
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 1e-12:
        return members[0].yaw, members[0].pitch
    return wrap_yaw(math.atan2(x, z)), math.asin(max(-1.0, min(1.0, y / norm)))


def _merge_members(members) -> SphericalCandidateEvidence:
    ordered = tuple(sorted(members, key=lambda item: item.candidate_id))
    if len(ordered) == 1:
        return ordered[0]
    yaw, pitch = _mean_direction(ordered)
    provenance: list[str] = []
    for member in ordered:
        provenance.append(f"duplicate-source:{member.candidate_id}")
        provenance.extend(member.observation_provenance)
    return SphericalCandidateEvidence(
        candidate_id="dedup:" + "+".join(item.candidate_id for item in ordered),
        track_id=None,
        yaw=yaw,
        pitch=pitch,
        h_fov=max(item.h_fov for item in ordered),
        candidate_type=ordered[0].candidate_type,
        signals=(),
        observation_provenance=tuple(provenance),
    )


def deduplicate_spherical_candidates(
    result: PerceptionResult,
    config: SphericalDedupConfig = SphericalDedupConfig(),
) -> SphericalDedupResult:
    """Cluster geometric duplicates with deterministic, confidence-free rules."""

    candidates = tuple(sorted(result.candidates, key=lambda item: item.candidate_id))
    adjacency: list[list[int]] = [[] for _ in candidates]
    for left in range(len(candidates)):
        for right in range(left + 1, len(candidates)):
            if _pair_gate(candidates[left], candidates[right], config):
                adjacency[left].append(right)
                adjacency[right].append(left)

    visited: set[int] = set()
    clusters: list[DuplicateCluster] = []
    for start in range(len(candidates)):
        if start in visited:
            continue
        stack = [start]
        visited.add(start)
        indices: list[int] = []
        while stack:
            current = stack.pop()
            indices.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        members = tuple(candidates[index] for index in sorted(indices))
        clusters.append(DuplicateCluster(_merge_members(members), members))

    merged = tuple(cluster.candidate for cluster in clusters)
    return SphericalDedupResult(
        PerceptionResult(result.sample, result.adapter, merged), tuple(clusters)
    )


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return value


def vision_gate_json_to_perception(
    document: str | bytes | Mapping[str, Any], *, width: int, height: int
) -> tuple[PerceptionResult, ...]:
    """Ingest Apple Vision gate v1 JSON and combine same-frame viewports."""

    root = json.loads(document) if isinstance(document, (str, bytes)) else document
    root = _require_mapping(root, "root")
    if root.get("schemaVersion") != 1:
        raise ValueError("unsupported Vision gate schemaVersion")
    provenance = _require_mapping(root.get("provenance"), "provenance")
    adapter = AdapterProvenance(
        str(provenance.get("adapterId", "")),
        str(provenance.get("adapterVersion", "")),
        str(provenance.get("backendId", "")),
        str(provenance.get("projectionStrategy", "")),
        provenance.get("weightsSha256"),
    )

    grouped: dict[tuple[str, int, float], list[SphericalCandidateEvidence]] = {}
    for frame_value in _require_list(root.get("frames"), "frames"):
        frame = _require_mapping(frame_value, "frame")
        key = (
            str(frame.get("sourceId", "")),
            int(frame.get("frameIndex")),
            float(frame.get("timestampSeconds")),
        )
        output = grouped.setdefault(key, [])
        for candidate_value in _require_list(frame.get("candidates"), "candidates"):
            candidate = _require_mapping(candidate_value, "candidate")
            confidence = float(candidate.get("confidence"))
            viewport_id = str(candidate.get("viewportId", ""))
            candidate_id = str(candidate.get("id", ""))
            kind = str(candidate.get("kind", ""))
            box = _require_mapping(candidate.get("boundingBox"), "boundingBox")
            provenance_record = json.dumps(
                {
                    "adapter": adapter.label,
                    "bounding_box": dict(box),
                    "candidate_id": candidate_id,
                    "confidence": confidence,
                    "viewport_id": viewport_id,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            output.append(
                SphericalCandidateEvidence(
                    candidate_id=candidate_id,
                    track_id=None,
                    yaw=wrap_yaw(float(candidate.get("yawRadians"))),
                    pitch=float(candidate.get("pitchRadians")),
                    h_fov=float(candidate.get("horizontalFovRadians")),
                    candidate_type=kind,
                    signals=(
                        SignalEvidence(
                            "detector_confidence",
                            confidence,
                            confidence,
                            f"{adapter.label};viewport:{viewport_id}",
                        ),
                    ),
                    observation_provenance=(provenance_record,),
                )
            )

    results: list[PerceptionResult] = []
    for (source_id, frame_index, timestamp), candidates in sorted(grouped.items()):
        sample = FrameSample(source_id, timestamp, frame_index, width, height)
        results.append(PerceptionResult(sample, adapter, tuple(candidates)))
    return tuple(results)
