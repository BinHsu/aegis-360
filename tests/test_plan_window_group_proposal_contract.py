from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_window_group_proposal.py"


class PlanWindowGroupProposalContractTests(unittest.TestCase):
    def test_context_must_reproduce_proposal_and_plan_stays_nonidentity(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("validate_scene_context(context_document)", text)
        self.assertIn("context candidates do not reproduce the proposal", text)
        self.assertIn('"identity_verified": False', text)
        self.assertIn('"editorial_persistence_allowed": False', text)
        self.assertIn('"render_contract": "shot_static_v360_only"', text)
        self.assertIn('"deterministic_context_fallback"', text)
        self.assertIn('"review_selected_group"', text)
        self.assertNotIn("source_media", text)


if __name__ == "__main__":
    unittest.main()
