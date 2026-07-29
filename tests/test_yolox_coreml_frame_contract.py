from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXCoreMLFrameContractTests(unittest.TestCase):
    def test_real_frame_report_is_path_and_pixel_free(self):
        script = (
            ROOT / "scripts/compare_yolox_coreml_frame.py"
        ).read_text()
        self.assertIn("refusing to overwrite report", script)
        self.assertIn("ratio = min(416 / image.shape[0]", script)
        self.assertIn("np.full((416, 416, 3), 114.0", script)
        self.assertIn('choices=("current", "legacy")', script)
        self.assertIn('if args.preprocessing == "legacy"', script)
        self.assertIn("padded[:, :, ::-1] / 255.0", script)
        self.assertIn("(.485, .456, .406)", script)
        self.assertIn("(.229, .224, .225)", script)
        self.assertIn("decode_yolox", script)
        self.assertIn("top_candidate_before_threshold", script)
        self.assertIn('"source_id": args.source_id', script)
        self.assertNotIn('"source_path"', script)
        self.assertNotIn('"frame_path"', script)
        self.assertNotIn('"pixels"', script)


if __name__ == "__main__":
    unittest.main()
