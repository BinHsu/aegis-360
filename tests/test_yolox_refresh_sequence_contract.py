from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXRefreshSequenceContractTests(unittest.TestCase):
    def test_runner_is_load_once_bounded_and_privacy_safe(self):
        script = (
            ROOT / "scripts/run_yolox_refresh_sequence.py"
        ).read_text()
        self.assertEqual(script.count("ct.models.MLModel("), 1)
        self.assertIn("TemporaryDirectory", script)
        self.assertIn("confidence_threshold=.25", script)
        self.assertIn("nms_iou_threshold=.45", script)
        self.assertIn('"one-source-pixel-v1"', script)
        self.assertIn('"rejected_target_geometry"', script)
        self.assertIn('"rejected_max_boundary_overflow_pixels"', script)
        self.assertIn("except ValueError:", script)
        self.assertIn('"events_after_termination_rejected"', script)
        self.assertIn('"no_compatible_lifecycle_start"', script)
        self.assertIn('"rejected_before_start_count"', script)
        self.assertIn('"rejected_after_termination_count"', script)
        self.assertIn('"contains_pixels": False', script)
        self.assertIn('"contains_source_path": False', script)
        self.assertIn("refusing to overwrite output directory", script)
        self.assertNotIn("official_evaluation", script)


if __name__ == "__main__":
    unittest.main()
