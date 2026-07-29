from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EvaluateNewTrackAcquisitionContractTests(unittest.TestCase):
    def test_cli_refuses_overwrite_and_serializes_strict_json(self):
        script = (
            ROOT / "scripts/evaluate_new_track_acquisition.py"
        ).read_text()
        self.assertIn("refusing to overwrite output", script)
        self.assertIn("allow_nan=False", script)
        self.assertIn("AcquisitionPolicy", script)
        self.assertNotIn("ffmpeg", script)


if __name__ == "__main__":
    unittest.main()
