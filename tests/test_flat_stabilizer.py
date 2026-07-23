import math
import unittest

from aegis360.flat_stabilizer import plan


class FlatStabilizerTest(unittest.TestCase):
    def test_smooths_synthetic_jitter_and_records_crop(self):
        positions = [0, 7, -5, 8, -6, 6, -4, 3, 0]
        observations = [{
            "frameIndex": 0, "timestampSeconds": 0.0, "state": "reference",
            "homographyRowMajor": None,
        }]
        for index, (left, right) in enumerate(zip(positions, positions[1:]), 1):
            dx = right - left
            observations.append({
                "frameIndex": index,
                "timestampSeconds": index / 10,
                "state": "measured",
                "homographyRowMajor": [1, 0, dx, 0, 1, 0, 0, 0, 1],
            })
        result = plan({
            "schemaVersion": 1, "sourceId": "synthetic-jitter",
            "frameWidth": 640, "frameHeight": 360, "observations": observations,
        }, smoothing_radius_seconds=0.3, measurement_direction="previous_to_current")
        raw = [row["rawPath"][0] for row in result["frames"]]
        smooth = [row["smoothedPath"][0] for row in result["frames"]]
        raw_changes = [b - a for a, b in zip(raw, raw[1:])]
        smooth_changes = [b - a for a, b in zip(smooth, smooth[1:])]
        raw_rms = math.sqrt(sum(value * value for value in raw_changes) / len(raw_changes))
        smooth_rms = math.sqrt(sum(value * value for value in smooth_changes) / len(smooth_changes))
        self.assertLess(smooth_rms, raw_rms * 0.35)
        self.assertGreater(result["overscan"]["conservativeSymmetricMarginPixels"], 0)
        self.assertEqual(len(result["frames"][3]["correctionHomographyRowMajor"]), 9)

    def test_inverts_current_to_previous_measurements(self):
        document = {
            "sourceId": "direction", "frameWidth": 100, "frameHeight": 50,
            "observations": [
                {"timestampSeconds": 0, "state": "reference"},
                {"timestampSeconds": 1, "state": "measured",
                 "homographyRowMajor": [1, 0, -10, 0, 1, 0, 0, 0, 1]},
            ],
        }
        result = plan(document, smoothing_radius_seconds=1,
                      measurement_direction="current_to_previous")
        self.assertAlmostEqual(result["frames"][1]["rawPath"][0], 10)


if __name__ == "__main__":
    unittest.main()
