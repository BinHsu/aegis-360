"""Assemble privacy-safe source orientation from multiview ray matches."""

from __future__ import annotations

import math
import re
from typing import Any

from .so3 import fit_rotation

_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]+$")


def assemble_source_motion(document: dict[str, Any]) -> dict[str, Any]:
    """Validate a registration bundle and emit ``aegis360.source-motion.v1``.

    Each match identifies the same static-scene direction in the previous and
    current rig-local frames.  Fitting current -> previous therefore yields
    the active rig delta that maps the current source frame into the prior
    reference frame.
    """

    if document.get("schemaVersion") != "aegis360.multiview-ray-matches.v1":
        raise ValueError("unsupported input schemaVersion")
    source_id = _safe_id(document.get("sourceId"), "sourceId")
    config_id = _safe_id(document.get("configId"), "configId")
    proxy = _proxy(document.get("proxy"))
    viewports = _viewports(document.get("viewports"))
    pairs = document.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("pairs must be a non-empty array")

    first_time = _finite_nonnegative(pairs[0].get("previousPtsSeconds"), "previousPtsSeconds")
    orientation = (0.0, 0.0, 0.0, 1.0)
    samples = [_sample(first_time, orientation, 1.0, 1.0, 1.0, 0.0, "measured")]
    gaps: list[dict[str, Any]] = []
    prior_time = first_time
    connected = True

    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            raise ValueError(f"pairs[{index}] must be an object")
        previous = _finite_nonnegative(pair.get("previousPtsSeconds"), "previousPtsSeconds")
        current = _finite_nonnegative(pair.get("currentPtsSeconds"), "currentPtsSeconds")
        if not math.isclose(previous, prior_time, abs_tol=1e-9) or current <= previous:
            raise ValueError("pairs must be contiguous with increasing timestamps")
        matches = pair.get("matches")
        if not isinstance(matches, list):
            raise ValueError("matches must be an array")
        correspondences = []
        contributing_views: set[str] = set()
        for match_index, match in enumerate(matches):
            if not isinstance(match, dict):
                raise ValueError(f"matches[{match_index}] must be an object")
            viewport_id = _safe_id(match.get("viewportId"), "viewportId")
            if viewport_id not in viewports:
                raise ValueError("match references an undeclared viewport")
            previous_ray = _ray(match.get("previousRay"), "previousRay")
            current_ray = _ray(match.get("currentRay"), "currentRay")
            correspondences.append((current_ray, previous_ray))
            contributing_views.add(viewport_id)

        try:
            fit = fit_rotation(correspondences)
            if not connected:
                samples.append(
                    _sample(
                        current, orientation, 0.0, fit.inlier_ratio,
                        len(contributing_views) / len(viewports),
                        fit.residual_radians, "invalid"
                    )
                )
                gaps.append(
                    {
                        "startPtsSeconds": previous,
                        "endPtsSeconds": current,
                        "reason": "disconnected_absolute_path",
                    }
                )
                prior_time = current
                continue
            orientation = _multiply_continuous(orientation, fit.rotation_xyzw)
            coverage = len(contributing_views) / len(viewports)
            confidence = fit.confidence * math.sqrt(coverage)
            state = "measured"
            samples.append(
                _sample(
                    current, orientation, confidence, fit.inlier_ratio,
                    coverage, fit.residual_radians, state
                )
            )
        except ValueError as error:
            connected = False
            reason = _reason(error)
            samples.append(_sample(current, orientation, 0.0, 0.0, 0.0, math.pi, "invalid"))
            gaps.append(
                {
                    "startPtsSeconds": previous,
                    "endPtsSeconds": current,
                    "reason": reason,
                }
            )
        prior_time = current

    return {
        "schema_version": "aegis360.source-motion.v1",
        "source_id": source_id,
        "coordinate_convention": "aegis360-spherical-v1",
        "estimator": {
            "backend": "visual-multiview-so3",
            "proxy": proxy,
            "config_id": config_id,
            "viewport_count": len(viewports),
        },
        "samples": samples,
        "gaps": gaps,
        "privacy": {
            "contains_source_path": False,
            "contains_pixels": False,
            "contains_identity_data": False,
        },
        "limitations": [
            "Ray correspondences are registration evidence, not camera-motion ground truth.",
            "Translation parallax, rolling shutter, moving objects, blur, and stitching defects can bias the fitted rotation.",
            "Confidence is a diagnostic score combining fit quality and viewport coverage; it is not a calibrated probability.",
        ],
    }


def _proxy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"width", "height", "sampleFps"}:
        raise ValueError("proxy must contain exactly width, height, sampleFps")
    width, height = value["width"], value["height"]
    fps = value["sampleFps"]
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise ValueError("proxy width must be a positive integer")
    if not isinstance(height, int) or isinstance(height, bool) or height <= 0:
        raise ValueError("proxy height must be a positive integer")
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or not math.isfinite(fps) or fps <= 0:
        raise ValueError("proxy sampleFps must be positive and finite")
    return {"width": width, "height": height, "sample_fps": float(fps)}


def _viewports(value: Any) -> set[str]:
    if not isinstance(value, list) or len(value) < 4:
        raise ValueError("viewports must contain at least four fixed overlapping views")
    ids: set[str] = set()
    for viewport in value:
        if not isinstance(viewport, dict):
            raise ValueError("viewport must be an object")
        if set(viewport) != {"id", "yawRadians", "pitchRadians", "horizontalFovRadians"}:
            raise ValueError("viewport fields must be id, yawRadians, pitchRadians, horizontalFovRadians")
        viewport_id = _safe_id(viewport["id"], "viewport id")
        if viewport_id in ids:
            raise ValueError("viewport ids must be unique")
        for field in ("yawRadians", "pitchRadians", "horizontalFovRadians"):
            number = viewport[field]
            if not isinstance(number, (int, float)) or isinstance(number, bool) or not math.isfinite(number):
                raise ValueError(f"{field} must be finite")
        if not 0 < viewport["horizontalFovRadians"] < math.pi:
            raise ValueError("horizontalFovRadians must be in (0, pi)")
        if not -math.pi / 2 <= viewport["pitchRadians"] <= math.pi / 2:
            raise ValueError("pitchRadians must remain between the poles")
        ids.add(viewport_id)
    return ids


def _sample(
    timestamp: float,
    orientation: tuple[float, float, float, float],
    confidence: float,
    inlier_ratio: float,
    coverage: float,
    residual: float,
    state: str,
) -> dict[str, Any]:
    return {
        "pts_seconds": timestamp,
        "raw_orientation_xyzw": list(orientation),
        "confidence": confidence,
        "inlier_ratio": inlier_ratio,
        "face_coverage": coverage,
        "residual_radians": residual,
        "state": state,
    }


def _multiply_continuous(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    result = (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )
    norm = math.sqrt(sum(value * value for value in result))
    result = tuple(value / norm for value in result)
    # q and -q encode the same rotation. Preserve the hemisphere nearest the
    # prior sample so downstream interpolation and derivatives remain
    # continuous when the accumulated path crosses 180 degrees.
    dot = sum(left * right for left, right in zip(first, result))
    return tuple(-value for value in result) if dot < 0 else result  # type: ignore[return-value]


def _ray(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must contain three values")
    if any(not isinstance(item, (int, float)) or isinstance(item, bool) or not math.isfinite(item) for item in value):
        raise ValueError(f"{label} must contain finite numbers")
    norm = math.sqrt(sum(item * item for item in value))
    if not math.isclose(norm, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        raise ValueError(f"{label} must be unit length")
    return tuple(item / norm for item in value)  # type: ignore[return-value]


def _safe_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must be privacy-safe")
    return value


def _finite_nonnegative(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return float(value)


def _reason(error: ValueError) -> str:
    text = str(error)
    if "at least two" in text:
        return "insufficient_correspondences"
    if "angular diversity" in text:
        return "insufficient_angular_diversity"
    return "rotation_fit_failed"
