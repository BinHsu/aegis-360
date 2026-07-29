import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.detector_equivalence import compare_detector_outputs


class DetectorEquivalenceTests(unittest.TestCase):
    def output(self, offset=0, box=None, class_id=1):
        values = [index / 100 + offset for index in range(25)]
        return {
            "tensors": [{"name": "output", "shape": [1, 25], "values": values}],
            "detections": [{
                "class_id": class_id,
                "score": .8 + offset,
                "box": box or [.1, .2, .3, .4],
            }],
        }

    def test_equivalent_outputs_pass_and_remain_path_free(self):
        report = compare_detector_outputs(
            self.output(), self.output(offset=.001)
        )
        self.assertTrue(report["passed"])
        self.assertFalse(report["privacy"]["contains_source_path"])

    def test_tensor_error_and_decoded_mismatch_fail(self):
        raw = compare_detector_outputs(self.output(), self.output(offset=.03))
        self.assertFalse(raw["raw"]["passed"])
        decoded = compare_detector_outputs(
            self.output(), self.output(class_id=2)
        )
        self.assertFalse(decoded["decoded"]["passed"])

    def test_bad_shape_nonfinite_and_box_fail_closed(self):
        candidate = self.output()
        candidate["tensors"][0]["shape"] = [25]
        with self.assertRaisesRegex(ValueError, "shapes"):
            compare_detector_outputs(self.output(), candidate)
        candidate = self.output()
        candidate["tensors"][0]["values"][0] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            compare_detector_outputs(self.output(), candidate)
        candidate = self.output(box=[.1, .2, -.3, .4])
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            compare_detector_outputs(self.output(), candidate)


if __name__ == "__main__":
    unittest.main()
