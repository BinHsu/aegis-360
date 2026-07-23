import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.shake_metrics import (  # noqa: E402
    MotionSample,
    estimate_translation,
    summarize_samples,
)


def textured_frame(width, height):
    return bytes(
        ((x * 37 + y * 73 + x * y * 11) ^ (x * 19 + y * 7)) % 256
        for y in range(height)
        for x in range(width)
    )


def translate(frame, width, height, dx, dy):
    output = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            source_x = x - dx
            source_y = y - dy
            if 0 <= source_x < width and 0 <= source_y < height:
                output[y * width + x] = frame[source_y * width + source_x]
    return bytes(output)


class ShakeMetricsTests(unittest.TestCase):
    def test_estimates_integer_translation(self):
        width, height = 48, 32
        before = textured_frame(width, height)
        after = translate(before, width, height, 3, -2)
        dx, dy, best_sad, zero_sad = estimate_translation(
            before, after, width, height, search_radius=5
        )
        self.assertEqual((dx, dy), (3, -2))
        self.assertLess(best_sad, zero_sad)

    def test_static_frame_prefers_zero_motion(self):
        width, height = 32, 24
        frame = textured_frame(width, height)
        dx, dy, best_sad, zero_sad = estimate_translation(
            frame, frame, width, height, search_radius=4
        )
        self.assertEqual((dx, dy), (0, 0))
        self.assertEqual(best_sad, 0)
        self.assertEqual(zero_sad, 0)

    def test_summary_compares_equal_leading_and_trailing_windows(self):
        samples = [
            MotionSample(i, dx, 0, abs(dx), 20, 1)
            for i, dx in enumerate((1, 1, 1, 1, -3, 3, -3, 3), start=1)
        ]
        report = summarize_samples(samples, width=100, segment_fraction=0.5)
        self.assertEqual(report["first"]["pair_count"], 4)
        self.assertEqual(report["last"]["pair_count"], 4)
        self.assertEqual(report["first"]["median_vector_change_pixels"], 0)
        self.assertEqual(report["last"]["median_vector_change_pixels"], 6)
        self.assertIsNone(report["last_vs_first_median_vector_change_ratio"])
        self.assertTrue(math.isclose(report["all"]["p95_step_width_fraction"], 0.03))


if __name__ == "__main__":
    unittest.main()
