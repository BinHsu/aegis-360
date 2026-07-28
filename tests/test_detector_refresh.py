import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.detector_refresh import (
    RefreshDetection, RefreshOutcome, associate_refresh,
)


def detection(identifier, semantic_class, yaw):
    return RefreshDetection(identifier, semantic_class, math.radians(yaw), 0)


class DetectorRefreshTests(unittest.TestCase):
    def test_one_same_class_nearby_detection_is_only_compatible(self):
        result = associate_refresh(
            track_class="person", track_yaw=0, track_pitch=0,
            detections=(detection("p1", "person", 5),),
        )
        self.assertEqual(result.outcome, RefreshOutcome.COMPATIBLE)
        self.assertEqual(result.compatible_detection_id, "p1")
        self.assertIn("do not establish", result.limitation)

    def test_multiple_nearby_people_are_ambiguous_not_nearest_winner(self):
        result = associate_refresh(
            track_class="person", track_yaw=0, track_pitch=0,
            detections=(
                detection("nearer", "person", 1),
                detection("farther", "person", 5),
            ),
        )
        self.assertEqual(result.outcome, RefreshOutcome.AMBIGUOUS)
        self.assertIsNone(result.compatible_detection_id)
        self.assertEqual(result.compatible_ids, ("farther", "nearer"))

    def test_wrong_class_and_distant_detection_remain_missing(self):
        result = associate_refresh(
            track_class="person", track_yaw=0, track_pitch=0,
            detections=(
                detection("bike", "bicycle", 1),
                detection("person", "person", 20),
            ),
        )
        self.assertEqual(result.outcome, RefreshOutcome.MISSING)

    def test_seam_distance_is_short_path(self):
        result = associate_refresh(
            track_class="person",
            track_yaw=math.radians(179),
            track_pitch=0,
            detections=(detection("seam", "person", -179),),
        )
        self.assertEqual(result.outcome, RefreshOutcome.COMPATIBLE)


if __name__ == "__main__":
    unittest.main()
