"""Deterministic, review-only chapter proposals from visual-state features."""

from __future__ import annotations

import re
import statistics
from fractions import Fraction
from typing import Mapping, Sequence

from aegis360.visual_state_features import validate_visual_state_feature_document


SCHEMA = "aegis360.chapter-proposal-candidates.v1"
CONFIG_SCHEMA = "aegis360.chapter-proposal-candidates-config.v1"
SHA256 = re.compile(r"[0-9a-f]{64}")
FAMILIES = ("global", "spatial_luma", "rgb_histogram")
LIMITATIONS = [
    "candidates are visual-state review proposals, not semantic chapter labels",
    "fixed support windows cannot propose within 30 seconds of either endpoint",
    "distribution-relative thresholding does not manufacture weak candidates",
]


def validate_chapter_proposal_config(config: Mapping[str, object]) -> None:
    expected = {
        "schema_version", "config_id", "before_window_offsets_seconds",
        "after_window_offsets_seconds", "feature_families",
        "distance_aggregation", "edge_scope", "family_distance_definitions",
        "family_equal_component_weights",
        "state_center_rule", "within_window_dispersion_rule",
        "persistence_dispersion_penalty_multiplier", "persistence_score_rule",
        "family_score_aggregation", "robust_threshold_rule",
        "robust_threshold_mad_multiplier", "zero_mad_rule",
        "absolute_minimum_score", "absolute_minimum_score_hypothesis",
        "local_maximum_radius_seconds", "minimum_temporal_separation_seconds",
        "maximum_candidates", "dominant_family_order", "selection_rule",
        "dominant_family_diversity_rule", "hard_negative_role",
        "tie_break_rule", "uncertainty_radius_seconds", "feature_round_digits",
        "local_plateau_rule", "threshold_comparison", "window_interval_semantics",
    }
    invalid = (
        not isinstance(config, Mapping)
        or set(config) != expected
        or config.get("schema_version") != CONFIG_SCHEMA
        or config.get("config_id") != "chapter-proposals-persistent-state-v1"
        or config.get("before_window_offsets_seconds") != [-30, -10]
        or config.get("after_window_offsets_seconds") != [10, 30]
        or config.get("feature_families") != list(FAMILIES)
        or config.get("distance_aggregation") != "equal-component-mean"
        or config.get("edge_scope") != "global-family-edge-strength-component"
        or config.get("family_distance_definitions") != {
            "global": "mean absolute distance over luma-mean,luma-stddev,edge-strength; each range [0,1]",
            "rgb_histogram": "mean per-channel total-variation distance; each channel range [0,1]",
            "spatial_luma": "mean absolute distance over eight 4x2 luma cells; each range [0,1]",
        }
        or config.get("family_equal_component_weights") != {
            "global": [1 / 3, 1 / 3, 1 / 3],
            "rgb_histogram_channels": [1 / 3, 1 / 3, 1 / 3],
            "spatial_luma": [1 / 8] * 8,
        }
        or config.get("state_center_rule") != "component-wise-arithmetic-mean"
        or config.get("within_window_dispersion_rule")
        != "mean-family-distance-to-window-state-center"
        or config.get("persistence_dispersion_penalty_multiplier") != 1.0
        or config.get("persistence_score_rule")
        != "clip(state-distance-(before-dispersion+after-dispersion),0,1)"
        or config.get("family_score_aggregation") != "maximum"
        or config.get("robust_threshold_rule")
        != "max-absolute-minimum-and-median-plus-scaled-mad"
        or config.get("robust_threshold_mad_multiplier") != 3.0
        or config.get("zero_mad_rule")
        != "threshold-is-max-of-absolute-floor-and-median"
        or config.get("absolute_minimum_score") != 0.08
        or config.get("absolute_minimum_score_hypothesis")
        != "a persistent normalized family shift below 0.08 is too weak for generic review"
        or config.get("local_maximum_radius_seconds") != 10
        or config.get("local_plateau_rule") != "earliest"
        or config.get("minimum_temporal_separation_seconds") != 45
        or config.get("maximum_candidates") != 6
        or config.get("dominant_family_order") != list(FAMILIES)
        or config.get("dominant_family_diversity_rule")
        != "record-only-no-quota-no-backfill-family-order-resolves-dominant-score-ties"
        or config.get("hard_negative_role") != "evaluation-only-not-generator-input"
        or config.get("selection_rule")
        != "qualified-local-maxima-score-descending-with-temporal-separation"
        or config.get("tie_break_rule") != "score-descending-then-time-ascending"
        or config.get("threshold_comparison") != "greater-than-or-equal"
        or config.get("uncertainty_radius_seconds") != 10
        or config.get("feature_round_digits") != 8
        or config.get("window_interval_semantics") != "half-open"
        or type(config.get("persistence_dispersion_penalty_multiplier")) is not float
        or type(config.get("robust_threshold_mad_multiplier")) is not float
        or type(config.get("absolute_minimum_score")) is not float
        or type(config.get("local_maximum_radius_seconds")) is not int
        or type(config.get("minimum_temporal_separation_seconds")) is not int
        or type(config.get("maximum_candidates")) is not int
        or type(config.get("uncertainty_radius_seconds")) is not int
        or type(config.get("feature_round_digits")) is not int
    )
    if invalid:
        raise ValueError("chapter proposal config is invalid")


def _mean_vectors(vectors: Sequence[Sequence[float]]) -> list[float]:
    return [statistics.fmean(values) for values in zip(*vectors)]


def _distance(family: str, left: Sequence[float], right: Sequence[float]) -> float:
    absolute = [abs(a - b) for a, b in zip(left, right)]
    if family == "rgb_histogram":
        return statistics.fmean(
            0.5 * sum(absolute[channel * 4:(channel + 1) * 4])
            for channel in range(3)
        )
    return statistics.fmean(absolute)


def _family_vector(sample: Mapping[str, object], family: str) -> list[float]:
    features = sample["features"]
    if family == "global":
        return [features["global_luma_mean"], features["global_luma_stddev"],
                features["edge_strength"]]
    if family == "spatial_luma":
        return list(features["spatial_luma_grid"])
    return sum(features["rgb_histogram"], [])


def _family_metrics(family, before_samples, after_samples, penalty, digits):
    before_vectors = [_family_vector(sample, family) for sample in before_samples]
    after_vectors = [_family_vector(sample, family) for sample in after_samples]
    before_state = _mean_vectors(before_vectors)
    after_state = _mean_vectors(after_vectors)
    distance = _distance(family, before_state, after_state)
    before_dispersion = statistics.fmean(
        _distance(family, vector, before_state) for vector in before_vectors)
    after_dispersion = statistics.fmean(
        _distance(family, vector, after_state) for vector in after_vectors)
    adjusted = min(1.0, max(
        0.0, distance - penalty * (before_dispersion + after_dispersion)))
    return {
        "state_distance": round(distance, digits),
        "before_dispersion": round(before_dispersion, digits),
        "after_dispersion": round(after_dispersion, digits),
        "dispersion_penalty": round(
            penalty * (before_dispersion + after_dispersion), digits),
        "persistence_adjusted_score": round(adjusted, digits),
    }


def _source_time(origin: Fraction, seconds: int) -> dict[str, int]:
    value = origin + seconds
    return {"numerator": value.numerator, "denominator": value.denominator}


def _local_peaks(scored, radius):
    local = []
    for row in scored:
        timestamp = row["center_proxy_time_seconds"]
        neighbours = [other for other in scored if abs(
            other["center_proxy_time_seconds"] - timestamp) <= radius]
        if row["score"] == max(other["score"] for other in neighbours):
            local.append(row)
    representatives = []
    index = 0
    while index < len(local):
        end = index + 1
        while (end < len(local)
               and local[end]["score"] == local[index]["score"]
               and local[end]["center_proxy_time_seconds"]
               == local[end - 1]["center_proxy_time_seconds"] + 1):
            end += 1
        representatives.append(local[index])  # frozen earliest-plateau rule
        index = end
    return representatives


def _select(peaks, config):
    ranked = sorted(peaks, key=lambda row: (
        -row["score"], row["center_proxy_time_seconds"]))
    selected = []
    dispositions = {}
    for row in ranked:
        separated = all(abs(row["center_proxy_time_seconds"]
                            - existing["center_proxy_time_seconds"])
                        >= config["minimum_temporal_separation_seconds"]
                        for existing in selected)
        if not separated:
            dispositions[row["center_proxy_time_seconds"]] = "minimum_separation"
        elif len(selected) < config["maximum_candidates"]:
            selected.append(row)
            dispositions[row["center_proxy_time_seconds"]] = "emitted"
        else:
            dispositions[row["center_proxy_time_seconds"]] = "maximum_candidate_cap"
    return sorted(selected, key=lambda row: row["center_proxy_time_seconds"]), dispositions


def build_chapter_proposal_candidates(
    *, visual_state_features: Mapping[str, object],
    visual_state_features_sha256: str, config: Mapping[str, object],
    config_sha256: str,
) -> dict[str, object]:
    validate_visual_state_feature_document(visual_state_features)
    validate_chapter_proposal_config(config)
    if (not isinstance(visual_state_features_sha256, str)
            or SHA256.fullmatch(visual_state_features_sha256) is None
            or not isinstance(config_sha256, str)
            or SHA256.fullmatch(config_sha256) is None):
        raise ValueError("chapter proposal input hashes are invalid")

    samples = visual_state_features["samples"]
    sample_by_second = {sample["proxy_time_seconds"]: sample for sample in samples}
    if len(sample_by_second) != len(samples):
        raise ValueError("visual-state cadence contains duplicate timestamps")
    digits = config["feature_round_digits"]
    scored = []
    for center in range(30, len(samples) - 29):
        before_seconds = range(center - 30, center - 10)
        after_seconds = range(center + 10, center + 30)
        required = list(before_seconds) + list(after_seconds)
        if any(float(second) not in sample_by_second for second in required):
            raise ValueError("visual-state support window is missing")
        before = [sample_by_second[float(second)]
                  for second in range(center - 30, center - 10)]
        after = [sample_by_second[float(second)]
                 for second in range(center + 10, center + 30)]
        metrics = {family: _family_metrics(
            family, before, after,
            config["persistence_dispersion_penalty_multiplier"], digits)
            for family in FAMILIES}
        dominant = max(FAMILIES, key=lambda family: (
            metrics[family]["persistence_adjusted_score"],
            -FAMILIES.index(family)))
        scored.append({
            "center_proxy_time_seconds": center,
            "family_metrics": metrics,
            "dominant_family": dominant,
            "score": metrics[dominant]["persistence_adjusted_score"],
        })

    scores = [row["score"] for row in scored]
    median = statistics.median(scores) if scores else 0.0
    mad = (statistics.median(abs(score - median) for score in scores)
           if scores else 0.0)
    relative = median + config["robust_threshold_mad_multiplier"] * mad
    threshold = round(max(config["absolute_minimum_score"], relative), digits)
    all_peaks = _local_peaks(scored, config["local_maximum_radius_seconds"])
    peaks = [row for row in all_peaks if row["score"] >= threshold]
    selected, qualified_dispositions = _select(peaks, config)
    local_maxima_audit = []
    for row in all_peaks:
        center = row["center_proxy_time_seconds"]
        local_maxima_audit.append({
            "center_proxy_time_seconds": center,
            "score": row["score"],
            "dominant_family": row["dominant_family"],
            "family_metrics": row["family_metrics"],
            "disposition": qualified_dispositions.get(center, "below_threshold"),
        })
    disposition_counts = {
        disposition: sum(row["disposition"] == disposition
                         for row in local_maxima_audit)
        for disposition in (
            "below_threshold", "minimum_separation",
            "maximum_candidate_cap", "emitted")
    }

    origin_raw = visual_state_features["timing"]["source_origin"]
    origin = Fraction(origin_raw["numerator"], origin_raw["denominator"])
    candidates = []
    for index, row in enumerate(selected, start=1):
        center = row["center_proxy_time_seconds"]
        candidates.append({
            "candidate_id": f"chapter-proposal-{index:02d}",
            "center_proxy_time_seconds": center,
            "center_source_time": _source_time(origin, center),
            "support_windows": {
                "before_proxy_seconds_half_open": [center - 30, center - 10],
                "after_proxy_seconds_half_open": [center + 10, center + 30],
                "samples_per_window": 20,
            },
            "uncertainty": {
                "kind": "symmetric-temporal-review-radius",
                "radius_seconds": config["uncertainty_radius_seconds"],
            },
            "family_metrics": row["family_metrics"],
            "dominant_family": row["dominant_family"],
            "persistence_adjusted_score": row["score"],
        })

    return {
        "schema_version": SCHEMA,
        "source_id": visual_state_features["source_id"],
        "inputs": {
            "visual_state_features_sha256": visual_state_features_sha256,
            "chapter_proposal_config_sha256": config_sha256,
        },
        "policy": {
            "config_id": config["config_id"],
            "eligible_center_count": len(scored),
            "score_median": round(median, digits),
            "score_mad": round(mad, digits),
            "mad_zero": mad == 0,
            "emission_threshold": threshold,
            "threshold_comparison": config["threshold_comparison"],
            "local_maximum_radius_seconds": config["local_maximum_radius_seconds"],
            "local_plateau_rule": config["local_plateau_rule"],
            "minimum_temporal_separation_seconds": config[
                "minimum_temporal_separation_seconds"],
            "maximum_candidates": config["maximum_candidates"],
            "selection_rule": config["selection_rule"],
            "dominant_family_diversity_rule": config[
                "dominant_family_diversity_rule"],
            "local_maxima_audit": local_maxima_audit,
            "local_maxima_disposition_counts": disposition_counts,
        },
        "candidates": candidates,
        "privacy": {
            "contains_source_path": False,
            "contains_pixels": False,
            "contains_audio": False,
            "contains_identity": False,
        },
        "authority": {
            "review_candidate_emitted": bool(candidates),
            "story_boundary": False,
            "candidate_selected": False,
            "production_eligible": False,
            "render": False,
        },
        "limitations": list(LIMITATIONS),
    }


def validate_chapter_proposal_document(
    document: Mapping[str, object], *,
    visual_state_features: Mapping[str, object],
    visual_state_features_sha256: str, config: Mapping[str, object],
    config_sha256: str,
) -> None:
    expected = build_chapter_proposal_candidates(
        visual_state_features=visual_state_features,
        visual_state_features_sha256=visual_state_features_sha256,
        config=config, config_sha256=config_sha256)
    if document != expected:
        raise ValueError("chapter proposal document must exactly derive from inputs")
