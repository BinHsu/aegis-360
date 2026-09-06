"""Strict path-free manifest for the canonical reusable analysis proxy."""

from __future__ import annotations

import math
import re
from fractions import Fraction
from typing import Mapping


SCHEMA = "aegis360.analysis-proxy-bundle.v1"
CONFIG = "aegis360.analysis-proxy-config.v1"
SHA = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:+-]+$")


def _num(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def validate_analysis_proxy_config(c):
    config = c
    expected_keys = {
        "schema_version",
        "config_id",
        "container",
        "video_codec",
        "width",
        "height",
        "pixel_format",
        "frame_rate",
        "sample_aspect_ratio",
        "video_only",
        "threads",
        "filter_order",
        "scale_flags",
        "pts_rule",
        "maximum_selection_error_seconds",
    }
    invalid = (
        not isinstance(config, Mapping)
        or set(config) != expected_keys
        or config.get("schema_version") != CONFIG
        or not isinstance(config.get("config_id"), str)
        or SAFE_ID.fullmatch(config["config_id"]) is None
        or config["container"] != "matroska"
        or config["video_codec"] != "ffv1"
        or (config["width"], config["height"], config["pixel_format"])
        != (960, 480, "yuv420p")
        or config["frame_rate"] != {"numerator": 10, "denominator": 1}
        or config["sample_aspect_ratio"] != "1:1"
        or config["video_only"] is not True
        or config["threads"] != 2
        or config["filter_order"] != ["fps", "scale", "format", "setsar", "setpts"]
        or config["scale_flags"] != "lanczos"
        or config["pts_rule"]
        != "proxy_zero_maps_to_source_stream_first_pts_plus_requested_start"
        or config["maximum_selection_error_seconds"] != 0.05
    )
    if invalid:
        raise ValueError("analysis proxy config is invalid")


def _validate_source_interval(source_interval):
    invalid = (
        not isinstance(source_interval, Mapping)
        or set(source_interval) != {"start", "duration"}
        or not isinstance(source_interval["start"], Mapping)
        or set(source_interval["start"]) != {"numerator", "denominator"}
        or any(
            isinstance(source_interval["start"].get(key), bool)
            or not isinstance(source_interval["start"].get(key), int)
            for key in ("numerator", "denominator")
        )
        or source_interval["start"]["numerator"] < 0
        or source_interval["start"]["denominator"] <= 0
        or source_interval["duration"] is not None
        and (
            not isinstance(source_interval["duration"], Mapping)
            or set(source_interval["duration"]) != {"numerator", "denominator"}
            or any(
                isinstance(source_interval["duration"].get(key), bool)
                or not isinstance(source_interval["duration"].get(key), int)
                for key in ("numerator", "denominator")
            )
            or source_interval["duration"]["numerator"] <= 0
            or source_interval["duration"]["denominator"] <= 0
        )
    )
    if invalid:
        raise ValueError("source interval is invalid")


def _validate_probe(probe):
    expected_keys = {
        "stream_count",
        "stream_types",
        "codec_name",
        "width",
        "height",
        "pixel_format",
        "frame_rate",
        "time_base",
        "start_pts",
        "start_time_seconds",
        "duration_seconds",
        "sample_aspect_ratio",
        "format_name",
        "color_range",
        "color_space",
        "color_transfer",
        "color_primaries",
    }
    color_keys = ("color_range", "color_space", "color_transfer", "color_primaries")
    invalid = (
        not isinstance(probe, Mapping)
        or set(probe) != expected_keys
        or probe["stream_count"] != 1
        or probe["stream_types"] != ["video"]
        or probe["codec_name"] != "ffv1"
        or (probe["width"], probe["height"], probe["pixel_format"])
        != (960, 480, "yuv420p")
        or probe["frame_rate"] != "10/1"
        or probe["time_base"] != "1/1000"
        or probe["sample_aspect_ratio"] != "1:1"
        or probe["format_name"] != "matroska,webm"
        or probe["start_pts"] != 0
        or probe["start_time_seconds"] != 0.0
        or not _num(probe["duration_seconds"])
        or probe["duration_seconds"] <= 0
        or any(
            not isinstance(probe[key], str) or not probe[key] for key in color_keys
        )
    )
    if invalid:
        raise ValueError("analysis proxy probe is invalid")


def build_analysis_proxy_bundle(
    *,
    source_id,
    source_sha256,
    config,
    config_sha256,
    proxy_sha256,
    source_timing,
    source_interval,
    probe,
    runtime,
):
    validate_analysis_proxy_config(config)

    invalid_provenance = (
        not isinstance(source_id, str)
        or SAFE_ID.fullmatch(source_id) is None
        or any(
            not isinstance(value, str) or SHA.fullmatch(value) is None
            for value in (source_sha256, config_sha256, proxy_sha256)
        )
    )
    if invalid_provenance:
        raise ValueError("analysis proxy provenance must be path-free and checksummed")

    timing_keys = {"first_pts", "time_base_numerator", "time_base_denominator"}
    invalid_timing = (
        not isinstance(source_timing, Mapping)
        or set(source_timing) != timing_keys
        or any(
            isinstance(source_timing[key], bool)
            or not isinstance(source_timing[key], int)
            for key in source_timing
        )
        or source_timing["time_base_denominator"] <= 0
    )
    if invalid_timing:
        raise ValueError("source timing is invalid")

    _validate_source_interval(source_interval)
    _validate_probe(probe)

    invalid_runtime = (
        not isinstance(runtime, Mapping)
        or set(runtime) != {"elapsed_seconds", "output_bytes"}
        or not _num(runtime["elapsed_seconds"])
        or runtime["elapsed_seconds"] < 0
        or isinstance(runtime["output_bytes"], bool)
        or not isinstance(runtime["output_bytes"], int)
        or runtime["output_bytes"] <= 0
    )
    if invalid_runtime:
        raise ValueError("analysis proxy runtime is invalid")

    origin_numerator = (
        source_timing["first_pts"]
        * source_timing["time_base_numerator"]
        * source_interval["start"]["denominator"]
        + source_interval["start"]["numerator"]
        * source_timing["time_base_denominator"]
    )
    origin_denominator = (
        source_timing["time_base_denominator"]
        * source_interval["start"]["denominator"]
    )
    origin = Fraction(origin_numerator, origin_denominator)
    start = Fraction(
        source_interval["start"]["numerator"],
        source_interval["start"]["denominator"],
    )
    duration = (
        None
        if source_interval["duration"] is None
        else Fraction(
            source_interval["duration"]["numerator"],
            source_interval["duration"]["denominator"],
        )
    )
    if (
        duration is not None
        and abs(probe["duration_seconds"] - float(duration)) > 0.100001
    ):
        raise ValueError("analysis proxy duration does not cover the requested interval")

    normalized_interval = {
        "start": {"numerator": start.numerator, "denominator": start.denominator},
        "duration": (
            None
            if duration is None
            else {"numerator": duration.numerator, "denominator": duration.denominator}
        ),
    }
    return {
        "schema_version": SCHEMA,
        "source_id": source_id,
        "inputs": {
            "source_sha256": source_sha256,
            "config_sha256": config_sha256,
            "proxy_sha256": proxy_sha256,
        },
        "source_interval": normalized_interval,
        "proxy": {
            "external_file": "analysis-proxy.mkv",
            "contains_pixels": True,
            "codec": "ffv1",
            "container": "matroska",
            "width": 960,
            "height": 480,
            "pixel_format": "yuv420p",
            "frame_rate": "10/1",
            "sample_aspect_ratio": "1:1",
            "video_only": True,
        },
        "timing": {
            "proxy_zero_affine_mapping": {
                "proxy_time_base": {"numerator": 1, "denominator": 10},
                "source_origin": {
                    "numerator": origin.numerator,
                    "denominator": origin.denominator,
                },
                "rule": "source_seconds=source_origin+proxy_pts*(1/10)",
            },
            "maximum_selection_error_seconds": 0.05,
        },
        "probe": dict(probe),
        "runtime": dict(runtime),
        "privacy": {
            "manifest_contains_source_path": False,
            "manifest_contains_pixels": False,
            "external_proxy_contains_pixels": True,
        },
        "performance_claims": {
            "peak_rss_measured": False,
            "swap_measured": False,
        },
        "limitations": [
            "CFR sampling can select within 0.05 seconds of the target timestamp",
            "bounded proxy duration may differ by at most one 10 fps frame",
            "color metadata is recorded as probed; unknown values are not inferred",
        ],
    }


def validate_analysis_proxy_bundle(doc, **kwargs):
    if doc != build_analysis_proxy_bundle(**kwargs):
        raise ValueError("analysis proxy bundle must exactly derive from inputs")
