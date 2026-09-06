import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.continuous_onset_candidates import (
    build_continuous_onset_candidates, validate_continuous_onset_candidates,
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class ContinuousOnsetCandidateTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "schema_version": "aegis360.continuous-onset-candidate-policy.v1",
            "policy_id": "fixture", "baseline_window_samples": 3,
            "high_threshold": 0.7, "release_threshold": 0.2,
            "minimum_consecutive": 2,
            "minimum_sample_cadence_seconds": 0.1,
            "maximum_sample_cadence_seconds": 0.5,
            "maximum_uncertainty_window_seconds": 0.5,
        }
        self.input = self.samples([0.1, 0.1, 0.1, 0.8, 0.9, 0.1])

    def samples(self, values):
        return {
            "schema_version": "aegis360.frame-difference-samples.v1",
            "source_id": "fixture",
            "window": {"start_seconds": 385.0, "duration_seconds": 2.0},
            "inputs": {"source_sha256": "a" * 64,
                       "acquisition_config_sha256": "b" * 64,
                       "metadata_sha256": "c" * 64},
            "acquisition": {"config_id": "fixture", "pts_origin": "interval_local",
                            "metadata_key": "lavfi.signalstats.YAVG",
                            "normalization_divisor": 255.0},
            "samples": [{"interval_pts_seconds": index * 0.25,
                         "pts_seconds": 385.0 + index * 0.25,
                         "normalized_difference": value}
                        for index, value in enumerate(values)],
            "privacy": {"contains_source_path": False, "contains_pixels": False,
                        "contains_audio": False, "contains_identity": False},
            "limitations": ["fixture"],
        }

    def build(self):
        return build_continuous_onset_candidates(
            self.input, self.policy, samples_sha256=digest(self.input),
            policy_sha256=digest(self.policy),
        )

    def test_sustained_onset_is_bounded_review_only_not_hard_cut(self):
        result = self.build()
        self.assertEqual(len(result["candidates"]), 1)
        candidate = result["candidates"][0]
        self.assertEqual(candidate["uncertainty_interval"],
                         {"start_seconds": 385.5, "end_seconds": 385.75})
        self.assertFalse(candidate["hard_cut_claimed"])
        self.assertFalse(result["planner_authority"]["story_boundary_emitted"])
        self.assertFalse(result["planner_authority"]["production_eligible"])
        validate_continuous_onset_candidates(
            result, self.input, self.policy,
            samples_sha256=digest(self.input), policy_sha256=digest(self.policy),
        )

    def test_spike_insufficient_baseline_and_unsustained_are_not_candidates(self):
        for values in ([.1, .1, .1, .9, .1, .1],
                       [.1, .8, .1, .8, .9, .1],
                       [.4, .4, .4, .8, .9, .1]):
            self.input = self.samples(values)
            self.assertEqual(self.build()["candidates"], [])

    def test_nan_bool_order_duplicate_bounds_and_cadence_fail_closed(self):
        mutations = []
        value = self.samples([.1, .1, .1, .8, .9])
        value["samples"][1]["normalized_difference"] = float("nan")
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["samples"][1]["normalized_difference"] = True
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["samples"][2]["pts_seconds"] = 385.1
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["samples"][2]["pts_seconds"] = value["samples"][1]["pts_seconds"]
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["samples"][0]["pts_seconds"] = 384.9
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["samples"][2]["pts_seconds"] = 386.0
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["privacy"]["contains_source_path"] = True
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["privacy"]["source_path"] = "/private/source.webm"
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["source_id"] = "/private/source.webm"
        mutations.append(value)
        value = self.samples([.1, .1, .1, .8, .9])
        value["schema_version"] = "aegis360.frame-difference-samples.v2"
        value["acquisition"].update({
            "sample_fps": True, "proxy_width": 320,
            "difference_mode": "absolute_difference",
            "filter_order": ["fps", "scale", "format_gray", "tblend_difference",
                             "signalstats", "metadata_print"],
            "filter_contract_version": "ffmpeg-frame-difference-v1",
            "ffmpeg_threads": 2,
            "calibration_status": "benchmark_poc_not_calibrated",
        })
        mutations.append(value)
        for mutation in mutations:
            self.input = mutation
            with self.assertRaises(ValueError):
                self.build()

    def test_policy_and_exact_rebuild_tamper_fail_closed(self):
        self.policy["high_threshold"] = self.policy["release_threshold"]
        with self.assertRaises(ValueError):
            self.build()
        self.setUp()
        result = self.build()
        result["candidates"][0]["hard_cut_claimed"] = True
        with self.assertRaises(ValueError):
            validate_continuous_onset_candidates(
                result, self.input, self.policy,
                samples_sha256=digest(self.input), policy_sha256=digest(self.policy),
            )

    def test_structurally_valid_v2_artifact_is_accepted(self):
        self.input["schema_version"] = "aegis360.frame-difference-samples.v2"
        self.input["acquisition"].update({
            "sample_fps": 4.0, "proxy_width": 320,
            "difference_mode": "absolute_difference",
            "filter_order": ["fps", "scale", "format_gray",
                             "tblend_difference", "signalstats", "metadata_print"],
            "filter_contract_version": "ffmpeg-frame-difference-v1",
            "ffmpeg_threads": 2,
            "calibration_status": "benchmark_poc_not_calibrated",
        })
        result = self.build()
        self.assertEqual(len(result["candidates"]), 1)
        self.input["acquisition"]["difference_mode"] = "subtract"
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
