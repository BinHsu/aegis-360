from pathlib import Path
import unittest


class SceneBoundaryReviewRendererContractTests(unittest.TestCase):
    def test_renderer_is_silent_equal_layout_and_atomic(self):
        source = (Path(__file__).resolve().parents[1] / "scripts" / "render_scene_boundary_review.py").read_text()
        self.assertIn("validate_multi_signal_review_packet", source)
        self.assertIn('"-an"', source)
        self.assertIn("split=4", source)
        self.assertIn("hstack=inputs=2", source)
        self.assertIn("vstack=inputs=2", source)
        self.assertIn("os.rename(staging, args.output_directory)", source)
        self.assertIn('"contains_editorial_decision": False', source)


if __name__ == "__main__":
    unittest.main()
