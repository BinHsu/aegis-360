"""Review-only continuous-onset candidates from frame-difference samples."""

from __future__ import annotations

import math
import re
from typing import Mapping


SCHEMA = "aegis360.continuous-onset-candidates.v1"
INPUT_SCHEMA = "aegis360.frame-difference-samples.v1"
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
            or set(samples) != {"schema_version", "source_id", "window",
                                "samples", "privacy"}
            or samples.get("schema_version") != INPUT_SCHEMA
            or not isinstance(samples.get("source_id"), str)
            or SAFE_ID.fullmatch(samples["source_id"]) is None):
        raise ValueError("frame-difference sample input is invalid")
    privacy = samples["privacy"]
    if (not isinstance(privacy, Mapping)
            or set(privacy) != {"contains_source_path", "contains_pixels"}
            or privacy["contains_source_path"] is not False
            or privacy["contains_pixels"] is not False):
        raise ValueError("frame-difference samples must be path-free and pixel-free")
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
                or set(row) != {"timestamp_seconds", "frame_difference"}
                or not _finite_number(row["timestamp_seconds"])
                or not _finite_number(row["frame_difference"])
                or row["frame_difference"] < 0):
            raise ValueError("frame-difference sample is invalid")
        timestamp = float(row["timestamp_seconds"])
        if not window_start <= timestamp <= window_end:
            raise ValueError("frame-difference sample is outside the window")
        timestamps.append(timestamp)
        values.append(float(row["frame_difference"]))
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
