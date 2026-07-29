import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.yolox_decode import decode_yolox


class YoloXDecodeTests(unittest.TestCase):
    def rows(self):
        return [[0.0] * 85 for _ in range(21)]

    def detection(self, rows, index, class_id, objectness, probability):
        rows[index][4] = objectness
        rows[index][5 + class_id] = probability

    def test_frozen_threshold_class_aware_nms_and_tie_break(self):
        rows = self.rows()
        self.detection(rows, 0, 1, .8, .5)
        self.detection(rows, 1, 1, .7, .5)
        self.detection(rows, 2, 2, .8, .5)
        rows[1][0] = -1
        rows[2][0] = -2
        detections = decode_yolox(
            rows, input_size=32,
            confidence_threshold=.25, nms_iou_threshold=.45,
        )
        self.assertEqual(
            [(item.class_id, item.source_index) for item in detections],
            [(1, 0), (2, 2)],
        )

    def test_below_threshold_is_excluded_and_bad_shape_fails(self):
        rows = self.rows()
        self.detection(rows, 0, 1, .5, .499)
        self.assertEqual(
            decode_yolox(rows, input_size=32), ()
        )
        with self.assertRaisesRegex(ValueError, "row count"):
            decode_yolox(rows[:-1], input_size=32)


if __name__ == "__main__":
    unittest.main()
