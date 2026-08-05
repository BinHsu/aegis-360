from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SemanticVisionSeedRunnerContractTests(unittest.TestCase):
    def test_tracking_runner_preserves_pitch_and_fov(self):
        script = (ROOT / "scripts/run_vision_tracking_gate.sh").read_text()
        self.assertIn("[ \"$#\" -ne 16 ]", script)
        self.assertIn("pitch=$viewport_pitch", script)
        self.assertIn("h_fov=$horizontal_fov", script)
        self.assertIn('"viewportPitchDegrees":%s', script)
        self.assertIn('"horizontalFovDegrees":%s', script)

    def test_seed_wrapper_uses_only_manifest_fields_and_existing_runner(self):
        script = (ROOT / "scripts/run_semantic_vision_seed_gate.sh").read_text()
        self.assertIn("aegis360.semantic-vision-seed.v1", script)
        self.assertIn("run_vision_tracking_gate.sh", script)
        self.assertIn(".viewport.pitch_degrees", script)
        self.assertIn(".viewport.horizontal_fov_degrees", script)


if __name__ == "__main__":
    unittest.main()
