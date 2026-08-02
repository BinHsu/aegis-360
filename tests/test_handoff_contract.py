from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_handoff import (
    MAX_HANDOFF_LINES,
    MAX_STATUS_LINES,
    REQUIRED_HEADINGS,
    parse_handoff,
    requires_handoff_update,
    validate_status,
)


def valid_document() -> str:
    headings = "\n\n".join(
        f"{heading}\n\nContent."
        + ("\n\n```sh\ntrue\n```" if heading == "## Next commands" else "")
        for heading in REQUIRED_HEADINGS
    )
    return (
        "# Current handoff\n\n"
        "Updated: 2026-07-26T12:00:00+08:00\n"
        "Repository: aegis-360\n"
        "Branch: main\n"
        "Baseline commit: deadbeef\n"
        "Remote status: unknown\n"
        "Working tree at checkpoint: clean\n\n"
        f"{headings}\n"
    )


class HandoffContractTests(unittest.TestCase):
    def test_complete_vendor_neutral_document_passes_content_validation(self):
        metadata, errors = parse_handoff(valid_document())
        self.assertFalse(errors)
        self.assertEqual(metadata["Repository"], "aegis-360")

    def test_missing_heading_and_shell_command_fail(self):
        document = valid_document().replace(
            "## Pending\n\nContent.\n\n", ""
        ).replace("```sh\ntrue\n```", "true")
        _, errors = parse_handoff(document)
        self.assertIn("missing heading: ## Pending", errors)
        self.assertIn("Next commands must contain a sh code fence", errors)

    def test_absolute_paths_and_chat_dependencies_fail(self):
        document = valid_document().replace(
            "## Objective\n\nContent.",
            "## Objective\n\nSee the previous conversation and /Users/alice/file.",
        )
        _, errors = parse_handoff(document)
        self.assertTrue(any("absolute macOS user path" in error for error in errors))
        self.assertTrue(any("prior-chat dependency" in error for error in errors))

    def test_significant_change_requires_current_handoff_in_same_diff(self):
        self.assertTrue(requires_handoff_update(["src/aegis360/so3.py"]))
        self.assertTrue(requires_handoff_update(["docs/README.md"]))
        self.assertFalse(requires_handoff_update([
            "src/aegis360/so3.py",
            "docs/handoff/current.md",
        ]))
        self.assertFalse(requires_handoff_update(["LICENSE"]))

    def test_current_documents_reject_embedded_history_and_unbounded_growth(self):
        handoff = valid_document().replace(
            "## Pending\n", "## History\n\nOld checkpoint.\n\n## Pending\n"
        )
        _, handoff_errors = parse_handoff(handoff)
        self.assertTrue(any("history or timeline" in error for error in handoff_errors))

        oversized_handoff = valid_document() + ("filler\n" * MAX_HANDOFF_LINES)
        _, oversized_errors = parse_handoff(oversized_handoff)
        self.assertTrue(any("exceeds" in error for error in oversized_errors))

        status_errors = validate_status(
            "# Project status\n\n## Timeline\n\nOld checkpoint.\n"
        )
        self.assertTrue(any("history or timeline" in error for error in status_errors))

        oversized_status = "# Project status\n" + ("filler\n" * MAX_STATUS_LINES)
        self.assertTrue(any("exceeds" in error for error in validate_status(oversized_status)))


if __name__ == "__main__":
    unittest.main()
