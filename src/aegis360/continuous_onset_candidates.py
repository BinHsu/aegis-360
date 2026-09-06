"""Review-only continuous-onset candidates from frame-difference samples."""

from __future__ import annotations

import math
import re
from typing import Mapping


SCHEMA = "aegis360.continuous-onset-candidates.v1"
INPUT_SCHEMAS = {"aegis360.frame-difference-samples.v1",
                 "aegis360.frame-difference-samples.v2"}
POLICY_SCHEMA = "aegis360.continuous-onset-candidate-policy.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
SAFE_ID = re.compile(r"^[A-Za-z0-9._:+-]+$")


def _finite_number(value: object) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def build_continuous_onset_candidates(
    samples: Mapping[str, object], policy: Mapping[str, object], *,
    samples_sha256: str, policy_sha256: str,
) -> dict[str, object]:
    """Detect sustained high differences after a bounded quiet baseline.

    The onset is only known to lie between the last baseline sample and the
    first sustained-high sample. The result grants review authority only.
    """
    if any(not isinstance(value, str) or SHA256.fullmatch(value) is None
           for value in (samples_sha256, policy_sha256)):
        raise ValueError("continuous-onset checksums are invalid")
    if (not isinstance(samples, Mapping)
            or set(samples) != {"schema_version", "source_id", "window", "inputs",
                                "acquisition", "samples", "privacy", "limitations"}
            or samples.get("schema_version") not in INPUT_SCHEMAS
            or not isinstance(samples.get("source_id"), str)
            or SAFE_ID.fullmatch(samples["source_id"]) is None):
        raise ValueError("frame-difference sample input is invalid")
    privacy = samples["privacy"]
    if (not isinstance(privacy, Mapping)
            or set(privacy) != {"contains_source_path", "contains_pixels",
                                "contains_audio", "contains_identity"}
            or any(value is not False for value in privacy.values())):
        raise ValueError("frame-difference samples must be path-free and pixel-free")
    inputs = samples["inputs"]
    if (not isinstance(inputs, Mapping)
            or set(inputs) != {"source_sha256", "acquisition_config_sha256",
                               "metadata_sha256"}
            or any(not isinstance(value, str) or SHA256.fullmatch(value) is None
                   for value in inputs.values())):
        raise ValueError("frame-difference sample lineage is invalid")
    acquisition = samples["acquisition"]
    expected_acquisition = {"config_id", "pts_origin", "metadata_key",
                            "normalization_divisor"}
    if samples["schema_version"] == "aegis360.frame-difference-samples.v2":
        expected_acquisition |= {
            "sample_fps", "proxy_width", "difference_mode", "filter_order",
            "filter_contract_version", "ffmpeg_threads", "calibration_status",
        }
    if (not isinstance(acquisition, Mapping)
            or set(acquisition) != expected_acquisition
            or not isinstance(acquisition["config_id"], str)
            or SAFE_ID.fullmatch(acquisition["config_id"]) is None
            or acquisition["pts_origin"] != "interval_local"
            or acquisition["metadata_key"] != "lavfi.signalstats.YAVG"
            or acquisition["normalization_divisor"] != 255.0
            or not isinstance(samples["limitations"], list)
            or any(not isinstance(value, str) for value in samples["limitations"])):
        raise ValueError("frame-difference acquisition contract is invalid")
    if (samples["schema_version"] == "aegis360.frame-difference-samples.v2"
            and (acquisition["difference_mode"] != "absolute_difference"
                 or acquisition["filter_order"] != [
                     "fps", "scale", "format_gray", "tblend_difference",
                     "signalstats", "metadata_print",
                 ]
                 or acquisition["filter_contract_version"] !=
                 "ffmpeg-frame-difference-v1"
                 or acquisition["calibration_status"] !=
                 "benchmark_poc_not_calibrated"
                 or not _finite_number(acquisition["sample_fps"])
                 or not 0 < acquisition["sample_fps"] <= 60
                 or isinstance(acquisition["proxy_width"], bool)
                 or not isinstance(acquisition["proxy_width"], int)
                 or not 16 <= acquisition["proxy_width"] <= 4096
                 or isinstance(acquisition["ffmpeg_threads"], bool)
                 or not isinstance(acquisition["ffmpeg_threads"], int)
                 or not 1 <= acquisition["ffmpeg_threads"] <= 8)):
        raise ValueError("frame-difference v2 acquisition contract is invalid")
    required_policy = {
        "schema_version", "policy_id", "baseline_window_samples",
        "high_threshold", "release_threshold", "minimum_consecutive",
        "minimum_sample_cadence_seconds", "maximum_sample_cadence_seconds",
        "maximum_uncertainty_window_seconds",
    }
    if (not isinstance(policy, Mapping) or set(policy) != required_policy
            or policy.get("schema_version") != POLICY_SCHEMA
            or not isinstance(policy.get("policy_id"), str)
            or not policy["policy_id"]):
        raise ValueError("continuous-onset policy is invalid")
    for key in ("baseline_window_samples", "minimum_consecutive"):
        value = policy[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError("continuous-onset count policy is invalid")
    numeric_keys = (
        "high_threshold", "release_threshold",
        "minimum_sample_cadence_seconds", "maximum_sample_cadence_seconds",
        "maximum_uncertainty_window_seconds",
    )
    if any(not _finite_number(policy[key]) or policy[key] < 0
           for key in numeric_keys):
        raise ValueError("continuous-onset numeric policy is invalid")
    if (policy["high_threshold"] <= policy["release_threshold"]
            or policy["minimum_sample_cadence_seconds"] <= 0
            or policy["maximum_sample_cadence_seconds"]
            < policy["minimum_sample_cadence_seconds"]
            or policy["maximum_uncertainty_window_seconds"]
            < policy["minimum_sample_cadence_seconds"]):
        raise ValueError("continuous-onset policy bounds are invalid")

    window = samples["window"]
    if (not isinstance(window, Mapping)
            or set(window) != {"start_seconds", "duration_seconds"}
            or not _finite_number(window["start_seconds"])
            or not _finite_number(window["duration_seconds"])
            or window["duration_seconds"] <= 0):
        raise ValueError("frame-difference window is invalid")
    window_start = float(window["start_seconds"])
    window_end = window_start + float(window["duration_seconds"])
    rows = samples["samples"]
    if not isinstance(rows, list):
        raise ValueError("frame-difference samples must be a list")
    timestamps = []
    values = []
    for row in rows:
        if (not isinstance(row, Mapping)
                or set(row) != {"interval_pts_seconds", "pts_seconds",
                                "normalized_difference"}
                or not _finite_number(row["interval_pts_seconds"])
                or not _finite_number(row["pts_seconds"])
                or not _finite_number(row["normalized_difference"])
                or not 0 <= row["normalized_difference"] <= 1
                or not math.isclose(row["pts_seconds"],
                                    window_start + row["interval_pts_seconds"],
                                    rel_tol=0, abs_tol=1e-9)):
            raise ValueError("frame-difference sample is invalid")
        timestamp = float(row["pts_seconds"])
        if not window_start <= timestamp <= window_end:
            raise ValueError("frame-difference sample is outside the window")
        timestamps.append(timestamp)
        values.append(float(row["normalized_difference"]))
    if any(right <= left for left, right in zip(timestamps, timestamps[1:])):
        raise ValueError("frame-difference timestamps must increase uniquely")
    cadences = [right - left for left, right in zip(timestamps, timestamps[1:])]
    if any(cadence < policy["minimum_sample_cadence_seconds"]
           or cadence > policy["maximum_sample_cadence_seconds"]
           for cadence in cadences):
        raise ValueError("frame-difference cadence is outside policy bounds")

    baseline_count = policy["baseline_window_samples"]
    sustain_count = policy["minimum_consecutive"]
    high = policy["high_threshold"]
    release = policy["release_threshold"]
    candidates = []
    index = baseline_count
    while index + sustain_count <= len(rows):
        baseline = values[index - baseline_count:index]
        sustained = values[index:index + sustain_count]
        if (all(value <= release for value in baseline)
                and all(value >= high for value in sustained)):
            lower = timestamps[index - 1]
            upper = timestamps[index]
            if upper - lower > policy["maximum_uncertainty_window_seconds"]:
                raise ValueError("continuous-onset uncertainty exceeds policy bound")
            candidates.append({
                "candidate_id": f"continuous-onset:{len(candidates):04d}",
                "uncertainty_interval": {
                    "start_seconds": lower, "end_seconds": upper,
                },
                "support_interval": {
                    "start_seconds": timestamps[index],
                    "end_seconds": timestamps[index + sustain_count - 1],
                    "supporting_sample_count": sustain_count,
                },
                "evidence": {
                    "baseline_maximum": max(baseline),
                    "sustained_minimum": min(sustained),
                },
                "temporal_form": "continuous_onset",
                "hard_cut_claimed": False,
            })
            index += sustain_count
            while index < len(values) and values[index] > release:
                index += 1
        else:
            index += 1
    return {
        "schema_version": SCHEMA, "source_id": samples["source_id"],
        "window": {"start_seconds": window_start,
                   "duration_seconds": float(window["duration_seconds"])},
        "inputs": {"frame_difference_samples_sha256": samples_sha256,
                   "candidate_policy_sha256": policy_sha256},
        "policy": dict(policy), "candidates": candidates,
        "planner_authority": {
            "review_candidate_emitted": bool(candidates),
            "story_boundary_emitted": False,
            "candidate_selected": False,
            "production_eligible": False,
        },
        "privacy": dict(samples["privacy"]),
        "limitations": [
            "frame difference alone does not establish semantic importance",
            "candidate timing is an uncertainty interval, not a hard cut",
            "candidates require independent semantic review before downstream use",
        ],
    }


def validate_continuous_onset_candidates(
    document: Mapping[str, object], samples: Mapping[str, object],
    policy: Mapping[str, object], *, samples_sha256: str,
    policy_sha256: str,
) -> None:
    expected = build_continuous_onset_candidates(
        samples, policy, samples_sha256=samples_sha256,
        policy_sha256=policy_sha256,
    )
    if document != expected:
        raise ValueError("continuous-onset candidates must exactly derive from inputs")
