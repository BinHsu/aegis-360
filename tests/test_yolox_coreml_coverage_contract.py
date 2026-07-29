from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXCoreMLCoverageContractTests(unittest.TestCase):
    def test_profiles_are_separate_pixels_temporary_and_load_once(self):
        script = (
            ROOT / "scripts/run_yolox_coreml_coverage.py"
        ).read_text()
        self.assertEqual(script.count("ct.models.MLModel("), 1)
        self.assertIn('confidence_threshold=.25', script)
        self.assertIn('nms_iou_threshold=.45', script)
        self.assertIn('confidence_threshold=.01', script)
        self.assertIn('nms_iou_threshold=.65', script)
        self.assertIn('"editorial_acceptance_allowed": False', script)
        self.assertIn("TemporaryDirectory", script)
        self.assertIn('"contains_source_path": False', script)
        self.assertIn('"contains_pixels": False', script)
        self.assertIn('"maximum_rss_bytes"', script)


if __name__ == "__main__":
    unittest.main()
