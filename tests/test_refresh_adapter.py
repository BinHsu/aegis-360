import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.refresh_adapter import (
    native_refresh_event, vision_box_center_to_angles,
)


class RefreshAdapterTests(unittest.TestCase):
    def test_center_box_preserves_viewport_pose(self):
        yaw, pitch = vision_box_center_to_angles(
            {"x": .4, "y": .4, "width": .2, "height": .2},
            viewport_yaw=1, viewport_pitch=.2,
            horizontal_fov=math.radians(100), aspect_ratio=1,
        )
        self.assertAlmostEqual(yaw, 1)
        self.assertAlmostEqual(pitch, .2)

    def test_native_event_keeps_class_and_geometry_separate(self):
        event = native_refresh_event(
            {
                "timestampSeconds": 1.0, "state": "tracked",
                "yawRadians": 0.1, "pitchRadians": 0.2,
            },
            {"detections": [{
                "labels": [{"identifier": "person", "confidence": .9}],
                "boundingBox": {
                    "x": .4, "y": .4, "width": .2, "height": .2,
                },
            }]},
            track_id="track-1", track_class="person",
            viewport_yaw=0, viewport_pitch=0,
            horizontal_fov=math.radians(100), aspect_ratio=1,
        )
        self.assertEqual(event.track_class, "person")
        self.assertEqual(event.detections[0].semantic_class, "person")
        self.assertEqual(event.detections[0].detection_id, "refresh:1.000:0")

    def test_untracked_refresh_fails_closed(self):
        with self.assertRaises(ValueError):
            native_refresh_event(
                {
                    "timestampSeconds": 1, "state": "lost",
                    "yawRadians": None, "pitchRadians": None,
                },
                {"detections": []},
                track_id="track", track_class="person",
                viewport_yaw=0, viewport_pitch=0,
                horizontal_fov=1, aspect_ratio=1,
            )


if __name__ == "__main__":
    unittest.main()
