"""Ensure frozen Stage A instructions and schema match the closed binder contract."""

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_semantics import ABSTENTION, FIELDS, VALUES


BUNDLE = ROOT / "prompts/sparse-story-stage-a-v1"


def check_schema_contract(schema):
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("raw object must be closed")
    if set(schema.get("required", [])) != set(FIELDS) or set(schema.get("properties", {})) != set(FIELDS):
        raise ValueError("raw fields differ from binder")
    for field in FIELDS:
        prop = schema["properties"][field]
        if set(prop) != {"type", "enum"} or prop["type"] != "string" or set(prop["enum"]) != VALUES[field] or len(prop["enum"]) != len(VALUES[field]):
            raise ValueError(f"raw enum differs: {field}")
    if schema.get("if") != {"properties": {"status": {"const": "abstain"}}, "required": ["status"]}:
        raise ValueError("abstention condition differs")
    then = schema.get("then", {}).get("properties", {})
    if then != {field: {"const": ABSTENTION[field]} for field in FIELDS if field != "status"}:
        raise ValueError("abstention values differ")


class StageAPromptBundleTest(unittest.TestCase):
    def test_schema_matches_binder(self):
        schema = json.loads((BUNDLE / "raw-observation-schema.json").read_text())
        check_schema_contract(schema)
        self.assertEqual(schema["title"], "aegis360.sparse-story-raw-observation.v1")

    def test_changed_enum_is_rejected(self):
        schema = json.loads((BUNDLE / "raw-observation-schema.json").read_text())
        changed = copy.deepcopy(schema)
        changed["properties"]["activity_relation"]["enum"] = ["same", "different", "unclear"]
        with self.assertRaisesRegex(ValueError, "raw enum differs"):
            check_schema_contract(changed)

    def test_prompt_names_only_closed_output_fields(self):
        prompt = (BUNDLE / "prompt.txt").read_text()
        declared = [line.split(":", 1)[0] for line in prompt.splitlines() if " | " in line]
        self.assertEqual(declared, list(FIELDS))
        for forbidden in ("Old Ghost", "Skiing", "205.6", "132.4", "327.25", "386.5"):
            self.assertNotIn(forbidden, prompt)


if __name__ == "__main__":
    unittest.main()
