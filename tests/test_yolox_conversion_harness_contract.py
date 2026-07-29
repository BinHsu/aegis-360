from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXConversionHarnessContractTests(unittest.TestCase):
    def test_harness_is_external_asset_only_and_frozen_shape(self):
        script = (
            ROOT / "scripts/convert_yolox_tiny_coreml.py"
        ).read_text()
        self.assertIn("refusing to overwrite output directory", script)
        self.assertIn("strict=True", script)
        self.assertIn("decode_in_inference = False", script)
        self.assertIn("width = 416", script)
        self.assertIn("torch.zeros(1, 3, width, width)", script)
        self.assertIn('torch.Generator().manual_seed(360)', script)
        for name in (
            "midgray", "horizontal-gradient", "vertical-gradient",
            "seeded-noise",
        ):
            self.assertIn(name, script)
        self.assertIn("np.array_equal(reference, traced_reference)", script)
        self.assertIn("compare_detector_outputs", script)
        self.assertIn("decode_yolox", script)
        self.assertIn("detection_document", script)
        self.assertIn('choices=("default", "float32")', script)
        self.assertIn("ct.precision.FLOAT32", script)
        self.assertNotIn("requests.", script)
        self.assertNotIn("urlopen", script)


if __name__ == "__main__":
    unittest.main()
