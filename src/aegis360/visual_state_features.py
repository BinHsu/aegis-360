"""Closed, pixel-free visual-state evidence derived from a canonical proxy."""

from __future__ import annotations

import hashlib
import math
import re
from collections import deque
from fractions import Fraction
from typing import Iterable, Mapping


SCHEMA = "aegis360.visual-state-features.v1"
CONFIG_SCHEMA = "aegis360.visual-state-features-config.v1"
PROXY_SCHEMA = "aegis360.analysis-proxy-bundle.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:+-]+$")
LIMITATIONS = [
    "features describe low-resolution visual state and are not semantic labels",
    "change descriptors compare fixed past samples and do not declare boundaries",
    "the first 5 or 15 seconds have no corresponding long-baseline descriptor",
]


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def validate_visual_state_config(config: Mapping[str, object]) -> None:
    expected = {
        "schema_version", "config_id", "sample_fps", "frame_width",
        "frame_height", "spatial_grid_columns", "spatial_grid_rows",
        "color_bins_per_channel", "baseline_offsets_seconds",
        "luma_coefficients_q8", "edge_operator", "filter_order",
        "scale_flags", "decoder_threads", "feature_round_digits",
    }
    invalid = (
        not isinstance(config, Mapping)
        or set(config) != expected
        or config.get("schema_version") != CONFIG_SCHEMA
        or not isinstance(config.get("config_id"), str)
        or SAFE_ID.fullmatch(config["config_id"]) is None
        or config.get("sample_fps") != 1
        or (config.get("frame_width"), config.get("frame_height")) != (96, 48)
        or (config.get("spatial_grid_columns"), config.get("spatial_grid_rows"))
        != (4, 2)
        or config.get("color_bins_per_channel") != 4
        or config.get("baseline_offsets_seconds") != [5, 15]
        or config.get("luma_coefficients_q8") != [77, 150, 29]
        or config.get("edge_operator")
        != "mean-absolute-4-neighbour-luma-difference"
        or config.get("filter_order") != ["fps", "scale", "format_rgb24"]
        or config.get("scale_flags") != "area"
        or config.get("decoder_threads") != 2
        or config.get("feature_round_digits") != 8
    )
    if invalid:
        raise ValueError("visual-state feature config is invalid")


def validate_proxy_bundle_for_features(
    bundle: Mapping[str, object], *, proxy_sha256: str,
    proxy_config_sha256: str,
) -> None:
    """Validate the closed subset needed to trust the canonical proxy."""
    top = {
        "schema_version", "source_id", "inputs", "source_interval", "proxy",
        "timing", "probe", "runtime", "privacy", "performance_claims",
        "limitations",
    }
    if not isinstance(bundle, Mapping) or set(bundle) != top:
        raise ValueError("analysis proxy bundle shape is invalid")
    inputs = bundle.get("inputs")
    source_interval = bundle.get("source_interval")
    proxy = bundle.get("proxy")
    privacy = bundle.get("privacy")
    timing = bundle.get("timing")
    mapping = timing.get("proxy_zero_affine_mapping") if isinstance(timing, Mapping) else None
    expected_proxy = {
        "external_file": "analysis-proxy.mkv", "contains_pixels": True,
        "codec": "ffv1", "container": "matroska", "width": 960,
        "height": 480, "pixel_format": "yuv420p", "frame_rate": "10/1",
        "sample_aspect_ratio": "1:1", "video_only": True,
    }
    invalid = (
        bundle.get("schema_version") != PROXY_SCHEMA
        or not isinstance(bundle.get("source_id"), str)
        or SAFE_ID.fullmatch(bundle["source_id"]) is None
        or not isinstance(inputs, Mapping)
        or set(inputs) != {"source_sha256", "config_sha256", "proxy_sha256"}
        or any(not isinstance(inputs.get(k), str) or SHA256.fullmatch(inputs[k]) is None
               for k in inputs)
        or inputs.get("proxy_sha256") != proxy_sha256
        or inputs.get("config_sha256") != proxy_config_sha256
        or proxy != expected_proxy
        or privacy != {
            "manifest_contains_source_path": False,
            "manifest_contains_pixels": False,
            "external_proxy_contains_pixels": True,
        }
        or not isinstance(timing, Mapping)
        or set(timing) != {"proxy_zero_affine_mapping", "maximum_selection_error_seconds"}
        or timing.get("maximum_selection_error_seconds") != 0.05
        or not isinstance(mapping, Mapping)
        or set(mapping) != {"proxy_time_base", "source_origin", "rule"}
        or mapping.get("proxy_time_base") != {"numerator": 1, "denominator": 10}
        or mapping.get("rule") != "source_seconds=source_origin+proxy_pts*(1/10)"
    )
    if invalid:
        raise ValueError("analysis proxy bundle is not canonical or does not match inputs")
    if (not isinstance(source_interval, Mapping)
            or set(source_interval) != {"start", "duration"}):
        raise ValueError("analysis proxy source interval is invalid")
    for name, allow_none in (("start", False), ("duration", True)):
        value = source_interval[name]
        if value is None and allow_none:
            continue
        if (not isinstance(value, Mapping)
                or set(value) != {"numerator", "denominator"}
                or any(isinstance(value.get(k), bool) or not isinstance(value.get(k), int)
                       for k in value)
                or value["denominator"] <= 0
                or (name == "start" and value["numerator"] < 0)
                or (name == "duration" and value["numerator"] <= 0)):
            raise ValueError("analysis proxy source interval is invalid")
    origin = mapping["source_origin"]
    if (not isinstance(origin, Mapping) or set(origin) != {"numerator", "denominator"}
            or any(isinstance(origin.get(k), bool) or not isinstance(origin.get(k), int)
                   for k in origin)
            or origin["denominator"] <= 0):
        raise ValueError("analysis proxy affine source origin is invalid")
    probe = bundle.get("probe")
    probe_keys = {"stream_count", "stream_types", "codec_name", "width", "height",
                  "pixel_format", "frame_rate", "time_base", "start_pts",
                  "start_time_seconds", "duration_seconds", "sample_aspect_ratio",
                  "format_name", "color_range", "color_space", "color_transfer",
                  "color_primaries"}
    if (not isinstance(probe, Mapping) or set(probe) != probe_keys
            or type(probe.get("stream_count")) is not int
            or probe.get("stream_count") != 1
            or probe.get("stream_types") != ["video"]
            or probe.get("codec_name") != "ffv1"
            or (probe.get("width"), probe.get("height"), probe.get("pixel_format"))
            != (960, 480, "yuv420p")
            or probe.get("frame_rate") != "10/1"
            or probe.get("time_base") != "1/1000"
            or type(probe.get("start_pts")) is not int
            or probe.get("start_pts") != 0
            or type(probe.get("start_time_seconds")) is not float
            or probe.get("start_time_seconds") != 0.0
            or probe.get("sample_aspect_ratio") != "1:1"
            or probe.get("format_name") != "matroska,webm"):
        raise ValueError("analysis proxy probe is invalid")
    if _finite(probe.get("duration_seconds"), "proxy duration") <= 0:
        raise ValueError("analysis proxy probe duration is invalid")


def expected_sample_count(duration_seconds: float, sample_fps: int = 1) -> int:
    duration = _finite(duration_seconds, "proxy duration")
    if duration <= 0 or sample_fps != 1:
        raise ValueError("sample-count inputs are invalid")
    # FFmpeg 8.1.1 fps=1 uses its default near rounding at the output boundary.
    return int(math.floor(duration * sample_fps + 0.5))


def _rounded(value: float, digits: int) -> float:
    return round(value, digits)


def _frame_features(frame: bytes, config: Mapping[str, object]) -> dict[str, object]:
    width = int(config["frame_width"])
    height = int(config["frame_height"])
    if len(frame) != width * height * 3:
        raise ValueError("decoded RGB frame has an invalid byte count")
    pixels = width * height
    luma = [0] * pixels
    hist = [[0] * 4 for _ in range(3)]
    total = 0
    total_sq = 0
    for i in range(pixels):
        r, g, b = frame[i * 3:i * 3 + 3]
        y = (77 * r + 150 * g + 29 * b + 128) >> 8
        luma[i] = y
        total += y
        total_sq += y * y
        hist[0][r >> 6] += 1
        hist[1][g >> 6] += 1
        hist[2][b >> 6] += 1
    digits = int(config["feature_round_digits"])
    mean = total / pixels
    variance = max(0.0, total_sq / pixels - mean * mean)
    edge_total = 0
    edge_pairs = 0
    for y in range(height):
        row = y * width
        for x in range(width):
            here = luma[row + x]
            if x + 1 < width:
                edge_total += abs(here - luma[row + x + 1])
                edge_pairs += 1
            if y + 1 < height:
                edge_total += abs(here - luma[row + width + x])
                edge_pairs += 1
    grid = []
    tile_w, tile_h = width // 4, height // 2
    for gy in range(2):
        for gx in range(4):
            tile_total = 0
            for y in range(gy * tile_h, (gy + 1) * tile_h):
                start = y * width + gx * tile_w
                tile_total += sum(luma[start:start + tile_w])
            grid.append(_rounded(tile_total / (tile_w * tile_h * 255), digits))
    return {
        "global_luma_mean": _rounded(mean / 255, digits),
        "global_luma_stddev": _rounded(math.sqrt(variance) / 255, digits),
        "edge_strength": _rounded(edge_total / (edge_pairs * 255), digits),
        "spatial_luma_grid": grid,
        "rgb_histogram": [
            [_rounded(value / pixels, digits) for value in channel]
            for channel in hist
        ],
    }


def _change(current: Mapping[str, object], baseline: Mapping[str, object], digits: int):
    grid = sum(abs(a - b) for a, b in zip(
        current["spatial_luma_grid"], baseline["spatial_luma_grid"])) / 8
    flat_current = sum(current["rgb_histogram"], [])
    flat_baseline = sum(baseline["rgb_histogram"], [])
    histogram = sum(abs(a - b) for a, b in zip(flat_current, flat_baseline)) / 6
    return {
        "global_luma_delta": _rounded(
            abs(current["global_luma_mean"] - baseline["global_luma_mean"]), digits),
        "spatial_luma_l1": _rounded(grid, digits),
        "rgb_histogram_distance": _rounded(histogram, digits),
        "edge_strength_delta": _rounded(
            abs(current["edge_strength"] - baseline["edge_strength"]), digits),
    }


def build_visual_state_features(
    *, bundle: Mapping[str, object], proxy_sha256: str,
    proxy_config_sha256: str, config: Mapping[str, object],
    config_sha256: str, frames: Iterable[bytes], frame_count: int,
) -> dict[str, object]:
    validate_visual_state_config(config)
    if not isinstance(config_sha256, str) or SHA256.fullmatch(config_sha256) is None:
        raise ValueError("visual-state config hash is invalid")
    validate_proxy_bundle_for_features(
        bundle, proxy_sha256=proxy_sha256,
        proxy_config_sha256=proxy_config_sha256,
    )
    expected = expected_sample_count(bundle["probe"]["duration_seconds"])
    if isinstance(frame_count, bool) or not isinstance(frame_count, int) or frame_count != expected:
        raise ValueError("decoded frame count does not match proxy duration and cadence")
    origin_raw = bundle["timing"]["proxy_zero_affine_mapping"]["source_origin"]
    origin = Fraction(origin_raw["numerator"], origin_raw["denominator"])
    history: deque[tuple[int, dict[str, object]]] = deque(maxlen=16)
    samples = []
    for index, frame in enumerate(frames):
        if index >= frame_count:
            raise ValueError("decoded stream contains extra frames")
        features = _frame_features(frame, config)
        previous = {sample_index: value for sample_index, value in history}
        changes = {}
        for offset in config["baseline_offsets_seconds"]:
            baseline = previous.get(index - offset)
            changes[f"from_{offset}s"] = (
                None if baseline is None else _change(
                    features, baseline, int(config["feature_round_digits"])))
        source = origin + index
        samples.append({
            "sample_index": index,
            "proxy_pts": index * 10,
            "proxy_time_seconds": float(index),
            "source_time": {"numerator": source.numerator, "denominator": source.denominator},
            "features": features,
            "long_baseline_change": changes,
        })
        history.append((index, features))
    if len(samples) != frame_count:
        raise ValueError("decoded stream ended before its declared frame count")
    return {
        "schema_version": SCHEMA,
        "source_id": bundle["source_id"],
        "inputs": {
            "source_sha256": bundle["inputs"]["source_sha256"],
            "analysis_proxy_sha256": proxy_sha256,
            "analysis_proxy_config_sha256": proxy_config_sha256,
            "visual_state_config_sha256": config_sha256,
        },
        "acquisition": {
            "config_id": config["config_id"], "sample_fps": 1,
            "frame_width": 96, "frame_height": 48, "frame_pixel_format": "rgb24",
            "filter_order": list(config["filter_order"]),
            "sample_count": frame_count,
            "expected_count_rule": "floor(proxy_duration_seconds*1fps+0.5)",
            "bounded_history_frames": 16,
        },
        "timing": {
            "proxy_pts_time_base": {"numerator": 1, "denominator": 10},
            "sample_cadence_proxy_pts": 10,
            "source_origin": dict(origin_raw),
            "rule": "source_seconds=source_origin+proxy_pts*(1/10)",
        },
        "samples": samples,
        "privacy": {
            "contains_source_path": False, "contains_proxy_path": False,
            "contains_pixels": False, "contains_audio": False,
            "contains_identity": False,
        },
        "authority": {
            "semantic_labels": False, "event_proposals": False,
            "story_boundaries": False, "camera_commands": False,
            "render_commands": False,
        },
        "limitations": list(LIMITATIONS),
    }


def artifact_sha256(document_bytes: bytes) -> str:
    return hashlib.sha256(document_bytes).hexdigest()


def validate_visual_state_feature_document(document: Mapping[str, object]) -> None:
    """Reject schema drift, timing drift, paths, pixels and added authority."""
    top = {"schema_version", "source_id", "inputs", "acquisition", "timing",
           "samples", "privacy", "authority", "limitations"}
    inputs = document.get("inputs") if isinstance(document, Mapping) else None
    acquisition = document.get("acquisition") if isinstance(document, Mapping) else None
    timing = document.get("timing") if isinstance(document, Mapping) else None
    samples = document.get("samples") if isinstance(document, Mapping) else None
    invalid = (
        not isinstance(document, Mapping) or set(document) != top
        or document.get("schema_version") != SCHEMA
        or not isinstance(document.get("source_id"), str)
        or SAFE_ID.fullmatch(document["source_id"]) is None
        or not isinstance(inputs, Mapping)
        or set(inputs) != {"source_sha256", "analysis_proxy_sha256",
                           "analysis_proxy_config_sha256", "visual_state_config_sha256"}
        or any(not isinstance(v, str) or SHA256.fullmatch(v) is None for v in inputs.values())
        or not isinstance(acquisition, Mapping)
        or set(acquisition) != {"config_id", "sample_fps", "frame_width",
                                "frame_height", "frame_pixel_format", "filter_order",
                                "sample_count", "expected_count_rule",
                                "bounded_history_frames"}
        or not isinstance(acquisition.get("config_id"), str)
        or SAFE_ID.fullmatch(acquisition["config_id"]) is None
        or type(acquisition.get("sample_fps")) is not int
        or acquisition.get("sample_fps") != 1
        or (acquisition.get("frame_width"), acquisition.get("frame_height"),
            acquisition.get("frame_pixel_format")) != (96, 48, "rgb24")
        or type(acquisition.get("sample_count")) is not int
        or acquisition.get("sample_count") != (len(samples) if isinstance(samples, list) else -1)
        or acquisition.get("expected_count_rule") != "floor(proxy_duration_seconds*1fps+0.5)"
        or acquisition.get("bounded_history_frames") != 16
        or acquisition.get("filter_order") != ["fps", "scale", "format_rgb24"]
        or not isinstance(timing, Mapping)
        or set(timing) != {"proxy_pts_time_base", "sample_cadence_proxy_pts",
                           "source_origin", "rule"}
        or timing.get("proxy_pts_time_base") != {"numerator": 1, "denominator": 10}
        or type(timing.get("sample_cadence_proxy_pts")) is not int
        or timing.get("sample_cadence_proxy_pts") != 10
        or timing.get("rule") != "source_seconds=source_origin+proxy_pts*(1/10)"
        or document.get("privacy") != {
            "contains_source_path": False, "contains_proxy_path": False,
            "contains_pixels": False, "contains_audio": False, "contains_identity": False}
        or document.get("authority") != {
            "semantic_labels": False, "event_proposals": False,
            "story_boundaries": False, "camera_commands": False,
            "render_commands": False}
        or document.get("limitations") != LIMITATIONS
    )
    if invalid:
        raise ValueError("visual-state feature document contract is invalid")
    origin = timing.get("source_origin")
    if (not isinstance(origin, Mapping) or set(origin) != {"numerator", "denominator"}
            or any(isinstance(origin.get(k), bool) or not isinstance(origin.get(k), int)
                   for k in origin) or origin["denominator"] <= 0):
        raise ValueError("visual-state source origin is invalid")
    origin_value = Fraction(origin["numerator"], origin["denominator"])
    sample_keys = {"sample_index", "proxy_pts", "proxy_time_seconds", "source_time",
                   "features", "long_baseline_change"}
    feature_keys = {"global_luma_mean", "global_luma_stddev", "edge_strength",
                    "spatial_luma_grid", "rgb_histogram"}
    change_keys = {"global_luma_delta", "spatial_luma_l1",
                   "rgb_histogram_distance", "edge_strength_delta"}
    for index, sample in enumerate(samples):
        source_time = origin_value + index
        if (not isinstance(sample, Mapping) or set(sample) != sample_keys
                or type(sample.get("sample_index")) is not int
                or sample.get("sample_index") != index
                or type(sample.get("proxy_pts")) is not int
                or sample.get("proxy_pts") != index * 10
                or type(sample.get("proxy_time_seconds")) is not float
                or sample.get("proxy_time_seconds") != float(index)
                or sample.get("source_time") != {"numerator": source_time.numerator,
                                                  "denominator": source_time.denominator}
                or not isinstance(sample.get("features"), Mapping)
                or set(sample["features"]) != feature_keys
                or not isinstance(sample.get("long_baseline_change"), Mapping)
                or set(sample["long_baseline_change"]) != {"from_5s", "from_15s"}):
            raise ValueError("visual-state samples are malformed or non-monotonic")
        features = sample["features"]
        values = [features["global_luma_mean"], features["global_luma_stddev"],
                  features["edge_strength"]]
        grid, histogram = features["spatial_luma_grid"], features["rgb_histogram"]
        if (not isinstance(grid, list) or len(grid) != 8
                or not isinstance(histogram, list) or len(histogram) != 3
                or any(not isinstance(channel, list) or len(channel) != 4
                       for channel in histogram)
                or any(not 0 <= _finite(value, "feature") <= 1
                       for value in values + grid + sum(histogram, []))
                or any(abs(sum(channel) - 1.0) > 0.00000005
                       for channel in histogram)):
            raise ValueError("visual-state feature values are malformed")
        for offset in (5, 15):
            change = sample["long_baseline_change"][f"from_{offset}s"]
            if index < offset:
                if change is not None:
                    raise ValueError("visual-state baseline availability is invalid")
            elif (not isinstance(change, Mapping) or set(change) != change_keys
                  or any(not 0 <= _finite(value, "change feature") <= 1
                         for value in change.values())):
                raise ValueError("visual-state change descriptors are malformed")
