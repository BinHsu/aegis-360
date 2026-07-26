from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_real_erp_multiview_motion import (
    distribution,
    causal_rotation_steps_document,
    summarize_leave_one_out,
    summarize_causal_view_reliability,
    summarize_spatial_residuals,
    summarize_spatial_mask_fit,
    summarize_view_consensus,
)


class RealMotionReportTests(unittest.TestCase):
    def test_distribution_is_deterministic_and_uses_nearest_rank_p95(self):
        result = distribution([4.0, 1.0, 3.0, 2.0])
        self.assertEqual(result, {
            "median": 2.5,
            "p95": 4.0,
            "maximum": 4.0,
        })

    def test_empty_distribution_is_explicitly_missing(self):
        self.assertIsNone(distribution([]))

    def test_leave_one_out_summary_preserves_failure_reasons(self):
        diagnostics = [{
            "leave_one_view_out": [
                {
                    "omitted_viewport_id": "front",
                    "state": "measured",
                    "failure_reason": None,
                    "step_rotation_radians": 0.1,
                    "residual_radians": 0.01,
                },
                {
                    "omitted_viewport_id": "back",
                    "state": "invalid",
                    "failure_reason": "rotation_fit_residual_exceeds_bound",
                    "step_rotation_radians": 0.2,
                    "residual_radians": 0.03,
                },
            ],
        }]
        summary = summarize_leave_one_out(
            diagnostics, ["front", "back", "missing"]
        )
        self.assertEqual(summary["front"]["measured_pair_fraction"], 1.0)
        self.assertEqual(summary["front"]["residual_radians"]["median"], 0.01)
        self.assertEqual(summary["back"]["measured_pair_count"], 0)
        self.assertEqual(summary["back"]["failure_reasons"], {
            "rotation_fit_residual_exceeds_bound": 1,
        })
        self.assertIsNone(summary["missing"]["measured_pair_fraction"])

    def test_view_consensus_summary_records_selection_not_pixels(self):
        diagnostics = [
            {"view_consensus": {
                "state": "measured",
                "failure_reason": None,
                "selected_viewport_ids": ["front", "right", "up", "left"],
                "rejected_viewport_ids": ["back", "down"],
                "step_rotation_radians": 0.01,
                "residual_radians": 0.005,
            }},
            {"view_consensus": {
                "state": "invalid",
                "failure_reason": "insufficient_view_consensus",
                "selected_viewport_ids": ["front", "right", "up"],
                "rejected_viewport_ids": ["back", "down", "left"],
                "step_rotation_radians": None,
                "residual_radians": None,
            }},
        ]
        summary = summarize_view_consensus(diagnostics)
        self.assertEqual(summary["measured_pair_fraction"], 0.5)
        self.assertEqual(summary["rejected_viewport_counts"]["back"], 2)
        self.assertEqual(summary["selected_viewport_count_histogram"], {
            "3": 1, "4": 1,
        })
        self.assertEqual(summary["failure_reasons"], {
            "insufficient_view_consensus": 1,
        })

    def test_causal_summary_records_selected_view_frequency(self):
        diagnostics = [
            {"causal_view_reliability": {
                "state": "measured",
                "failure_reason": None,
                "selected_viewport_ids": ["front", "right", "up", "left"],
                "step_rotation_radians": 0.01,
                "residual_radians": 0.005,
            }},
            {"causal_view_reliability": {
                "state": "invalid",
                "failure_reason": "rotation_fit_residual_exceeds_bound",
                "selected_viewport_ids": ["front", "right", "up", "down"],
                "step_rotation_radians": 0.02,
                "residual_radians": 0.03,
            }},
        ]
        summary = summarize_causal_view_reliability(diagnostics)
        self.assertEqual(summary["measured_pair_fraction"], 0.5)
        self.assertEqual(summary["selected_viewport_counts"], {
            "down": 1, "front": 2, "left": 1, "right": 2, "up": 2,
        })
        self.assertEqual(summary["failure_reasons"], {
            "rotation_fit_residual_exceeds_bound": 1,
        })

    def test_causal_steps_keep_gaps_explicit_and_paths_private(self):
        motion = {"estimator": {"fit_bounds": {"pair_diagnostics": [
            {
                "previous_pts_seconds": 0.0,
                "current_pts_seconds": 0.04,
                "causal_view_reliability": {
                    "state": "measured",
                    "failure_reason": None,
                    "rotation_xyzw": [0.0, 0.0, 0.0, 1.0],
                    "selected_viewport_ids": ["a", "b", "c", "d"],
                    "fit_confidence": 0.8,
                    "inlier_ratio": 1.0,
                    "residual_radians": 0.01,
                },
            },
            {
                "previous_pts_seconds": 0.04,
                "current_pts_seconds": 0.08,
                "causal_view_reliability": {
                    "state": "invalid",
                    "failure_reason": "rotation_fit_failed",
                    "rotation_xyzw": [1.0, 0.0, 0.0, 0.0],
                    "selected_viewport_ids": ["a", "b", "c", "d"],
                    "fit_confidence": 0.0,
                    "inlier_ratio": 0.0,
                    "residual_radians": None,
                },
            },
        ]}}}
        result = causal_rotation_steps_document(
            motion, {"configId": "causal-v1"}, "safe-source"
        )
        self.assertEqual(
            result["schema_version"], "aegis360.causal-rotation-steps.v1"
        )
        self.assertIsNone(result["steps"][1]["rotation_xyzw"])
        self.assertFalse(result["privacy"]["contains_source_path"])

    def test_spatial_summary_groups_only_privacy_safe_band_metrics(self):
        diagnostics = [{"causal_view_reliability": {
            "spatial_residuals": [
                {
                    "viewport_id": "front",
                    "vertical_band": "bottom",
                    "rms_residual_radians": 0.03,
                },
                {
                    "viewport_id": "front",
                    "vertical_band": "bottom",
                    "rms_residual_radians": 0.01,
                },
            ],
        }}]
        summary = summarize_spatial_residuals(diagnostics)
        bottom = summary["front"]["bottom"]
        self.assertEqual(bottom["pair_count"], 2)
        self.assertAlmostEqual(
            bottom["pair_rms_residual_radians"]["median"], 0.02
        )

    def test_spatial_mask_summary_preserves_failure_counts(self):
        diagnostics = [
            {"spatial_mask_fit": {
                "state": "measured", "failure_reason": None,
                "residual_radians": 0.01, "step_rotation_radians": 0.02,
            }},
            {"spatial_mask_fit": {
                "state": "invalid",
                "failure_reason": "rotation_fit_residual_exceeds_bound",
                "residual_radians": 0.03, "step_rotation_radians": 0.02,
            }},
        ]
        summary = summarize_spatial_mask_fit(diagnostics)
        self.assertEqual(summary["measured_pair_fraction"], 0.5)
        self.assertEqual(summary["failure_reasons"], {
            "rotation_fit_residual_exceeds_bound": 1,
        })


if __name__ == "__main__":
    unittest.main()
