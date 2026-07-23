import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.vision_homography import (
    vision_native_to_source_target_top_left,
)


class VisionHomographyConventionTests(unittest.TestCase):
    def test_converts_native_alignment_translation(self):
        # Target content is (+18,+12) from source in top-left coordinates.
        # Vision aligns target back to source in bottom-left coordinates.
        native = (1, 0, -18, 0, 1, 12, 0, 0, 1)
        converted = vision_native_to_source_target_top_left(native, 360)
        expected = (1, 0, 18, 0, 1, 12, 0, 0, 1)
        for actual, wanted in zip(converted, expected):
            self.assertAlmostEqual(actual, wanted)

    def test_round_trip_keeps_projective_terms_and_normalizes_scale(self):
        native = (1.01, 0.03, -7, -0.02, 0.99, 5, 1e-4, -2e-4, 1)
        converted = vision_native_to_source_target_top_left(native, 360)
        self.assertEqual(len(converted), 9)
        self.assertTrue(all(math.isfinite(value) for value in converted))
        self.assertAlmostEqual(converted[8], 1.0)

    def test_rejects_invalid_transform(self):
        with self.assertRaisesRegex(ValueError, "nine finite"):
            vision_native_to_source_target_top_left([1.0] * 8, 360)
        with self.assertRaisesRegex(ValueError, "height"):
            vision_native_to_source_target_top_left(
                (1, 0, 0, 0, 1, 0, 0, 0, 1), 0
            )
        with self.assertRaisesRegex(ValueError, "singular"):
            vision_native_to_source_target_top_left(
                (0, 0, 0, 0, 0, 0, 0, 0, 0), 360
            )


if __name__ == "__main__":
    unittest.main()
