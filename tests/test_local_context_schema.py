from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.local_context_schema import local_context_json_schema
from tests.test_local_context_adapter import proposal


class LocalContextSchemaTests(unittest.TestCase):
    def test_scope_candidate_relationships_are_grammar_bounded(self):
        schema = local_context_json_schema(proposal(), audio_provided=False)
        pairs = {
            (branch["properties"]["subject_scope"]["const"],
             tuple(branch["properties"]["selected_candidate_id"].get("enum", [None])))
            for branch in schema["anyOf"]
        }
        self.assertIn(("group", ("group:window:1",)), pairs)
        self.assertIn(("single", ("person-slot:1", "person-slot:2")), pairs)
        self.assertEqual(
            schema["properties"]["evidence_flags"]["properties"]["speech_audio_present"],
            {"const": "unknown"},
        )

    def test_unknown_candidate_type_fails_closed(self):
        value = proposal()
        value["candidates"][0]["candidate_type"] = "invented"
        with self.assertRaises(ValueError):
            local_context_json_schema(value, audio_provided=False)

    def test_absent_group_proposal_removes_group_branch(self):
        value = proposal()
        value["candidates"] = [
            candidate for candidate in value["candidates"]
            if candidate["candidate_type"] != "group"
        ]
        schema = local_context_json_schema(value, audio_provided=False)
        scopes = {
            branch["properties"]["subject_scope"]["const"]
            for branch in schema["anyOf"]
        }
        self.assertNotIn("group", scopes)
        self.assertNotIn(
            "group:window:1", schema["properties"]["selected_candidate_id"]["enum"],
        )


if __name__ == "__main__":
    unittest.main()
