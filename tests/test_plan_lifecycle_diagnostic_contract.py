from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PlanLifecycleDiagnosticContractTests(unittest.TestCase):
    def test_diagnostic_is_planning_only_and_refuses_overwrite(self):
        script = (
            ROOT / "scripts/plan_lifecycle_diagnostic.py"
        ).read_text()
        self.assertIn("refusing to overwrite output", script)
        self.assertIn('"rendered": False', script)
        self.assertIn('"geometric_only"', script)
        self.assertIn("editorial_persistence_allowed", script)
        self.assertNotIn("ffmpeg", script)


if __name__ == "__main__":
    unittest.main()
