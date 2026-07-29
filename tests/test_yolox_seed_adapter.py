import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.yolox_seed_adapter import vision_seed_box, yolox_refresh_event


class YoloXSeedAdapterTests(unittest.TestCase):
    def test_top_left_box_converts_to_vision_bottom_left(self):
        result = vision_seed_box({
            "class_id": 1,
            "score": .3,
            "box": [.5, .55, .2, .4],
        })
        self.assertEqual(result["x"], .5)
        self.assertAlmostEqual(result["y"], .05)
        self.assertEqual(result["width"], .2)
        self.assertEqual(result["height"], .4)

    def test_wrong_class_low_score_and_overflow_fail_closed(self):
        for detection in (
            {"class_id": 14, "score": .9, "box": [.1, .1, .2, .2]},
            {"class_id": 1, "score": .249, "box": [.1, .1, .2, .2]},
            {"class_id": 1, "score": .9, "box": [.9, .1, .2, .2]},
        ):
            with self.assertRaises(ValueError):
                vision_seed_box(detection)

    def test_refresh_filters_person_before_bicycle_geometry(self):
        event = yolox_refresh_event(
            {
                "timestampSeconds": 1,
                "state": "tracked",
                "yawRadians": 0,
                "pitchRadians": 0,
            },
            [
                {"class_id": 0, "score": .9, "box": [.9, .1, .2, .2]},
                {"class_id": 1, "score": .7, "box": [.4, .4, .2, .2]},
            ],
            track_id="bike-1",
            track_class="bicycle",
            viewport_yaw=0,
            viewport_pitch=0,
            horizontal_fov=1,
            aspect_ratio=1,
        )
        self.assertEqual(len(event.detections), 1)
        self.assertEqual(event.detections[0].semantic_class, "bicycle")


if __name__ == "__main__":
    unittest.main()
