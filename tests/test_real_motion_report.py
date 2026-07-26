from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_real_erp_multiview_motion import distribution, summarize_leave_one_out


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


if __name__ == "__main__":
    unittest.main()
