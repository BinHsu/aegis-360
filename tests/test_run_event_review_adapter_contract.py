from pathlib import Path
import unittest


class RunEventReviewAdapterContractTests(unittest.TestCase):
    def test_runner_uses_bounded_temporary_media_and_no_shell(self):
        source = (Path(__file__).resolve().parents[1] / "scripts" / "run_event_review_adapter.py").read_text()
        self.assertIn("TemporaryDirectory", source)
        self.assertIn('"-frames:v", "1"', source)
        self.assertIn('"-an"', source)
        self.assertIn("AEGIS_REVIEW_MEDIA_INDEX", source)
        self.assertIn("validate_multi_signal_review_packet", source)
        self.assertNotIn("shell=True", source)


if __name__ == "__main__":
    unittest.main()
