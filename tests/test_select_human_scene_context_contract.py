from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "select_human_scene_context.py"


class SelectHumanSceneContextContractTests(unittest.TestCase):
    def test_selection_is_atomic_closed_and_model_free(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("validate_scene_context(document)", text)
        self.assertIn("os.link(temporary_name, args.output_json)", text)
        self.assertIn('"reviewer_kind": "human"', text)
        self.assertIn('"model_id": None', text)
        self.assertNotIn("source_media", text)


if __name__ == "__main__":
    unittest.main()
