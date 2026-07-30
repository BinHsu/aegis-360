from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXNumpyDecodeContractTests(unittest.TestCase):
    def test_candidate_preserves_reference_threshold_order_and_failures(self):
        module = (ROOT / "src/aegis360/yolox_decode_numpy.py").read_text()
        runner = (
            ROOT / "scripts/benchmark_yolox_coreml_stream.py"
        ).read_text()
        self.assertIn("confidence_threshold: float = .25", module)
        self.assertIn("nms_iou_threshold: float = .45", module)
        self.assertIn("np.argmax", module)
        self.assertIn("np.lexsort((source_indices, class_ids, -scores))", module)
        self.assertIn("iou > nms_iou_threshold", module)
        self.assertIn("decode_yolox_numpy", runner)
        self.assertIn('choices=("reference", "numpy")', runner)
        self.assertIn("decoder equivalence count mismatch", runner)
        self.assertIn("decoder equivalence value mismatch", runner)


if __name__ == "__main__":
    unittest.main()
