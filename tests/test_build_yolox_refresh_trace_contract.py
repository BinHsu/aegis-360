from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BuildYoloXRefreshTraceContractTests(unittest.TestCase):
    def test_only_current_acceptance_reports_can_enter_trace(self):
        script = (
            ROOT / "scripts/build_yolox_refresh_trace.py"
        ).read_text()
        self.assertIn('report.get("passed") is not True', script)
        self.assertIn('report.get("threshold_profile") != "acceptance"', script)
        self.assertIn('report.get("preprocessing") != "current"', script)
        self.assertIn("no tracker observation", script)
        self.assertIn("refusing to overwrite output", script)
        self.assertIn('choices=(0.0, 1.0)', script)
        self.assertIn("boundary_tolerance_pixels=args.boundary_tolerance_pixels", script)
        self.assertIn('"one-source-pixel-v1"', script)
        self.assertIn('"strict-v1"', script)


if __name__ == "__main__":
    unittest.main()
