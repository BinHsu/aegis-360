from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_real_erp_multiview_motion import distribution


class RealMotionReportTests(unittest.TestCase):
    def test_distribution_is_deterministic_and_uses_nearest_rank_p95(self):
        result = distribution([4.0, 1.0, 3.0, 2.0])
        self.assertEqual(result, {
            "median": 2.5,
            "p95": 4.0,
            "maximum": 4.0,
        })

    def test_empty_distribution_is_explicitly_missing(self):
        self.assertIsNone(distribution([]))


if __name__ == "__main__":
    unittest.main()
