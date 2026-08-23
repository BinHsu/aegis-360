import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.local_scene_story_schema import local_scene_story_json_schema
from aegis360.scene_story_packet import build_scene_story_packet
from aegis360.scene_story_semantics import build_scene_story_semantics, validate_scene_story_semantics
from tests.test_scene_story_packet import build_story_fixture, digest


class SceneStorySemanticsTests(unittest.TestCase):
    def setUp(self):
        grid, grid_sha, timeline = build_story_fixture()
        self.packet = build_scene_story_packet(
            timeline, grid, event_id="event:multi:0001",
            timeline_sha256=digest(timeline), grid_sha256=grid_sha,
        )
        self.config = {
            "schema_version": "aegis360.scene-story-semantics-config.v1",
            "reviewer_type": "agent", "reviewer_id": "source-context-review-v1",
            "reviewer_asset_sha256": None, "status": "observed",
            "structural_role": "chapter_boundary",
            "narrative_function": "activity_transition",
            "change_type": "hard_cut", "viewer_value": "supporting",
        }

    def build(self, config=None):
        config = self.config if config is None else config
        return build_scene_story_semantics(
            config, self.packet, config_sha256=digest(config),
            packet_sha256=digest(self.packet),
        )

    def test_closed_complete_observation_binds_packet(self):
        value = self.build()
        validate_scene_story_semantics(
            value, self.config, self.packet, config_sha256=digest(self.config),
            packet_sha256=digest(self.packet),
        )
        self.assertFalse(value["privacy"]["contains_editorial_decision"])

    def test_abstain_has_no_claims(self):
        self.config.update({"status": "abstain", "structural_role": "unknown",
                            "narrative_function": "unknown", "change_type": "unknown",
                            "viewer_value": "unknown"})
        self.assertEqual(self.build()["evidence"]["status"], "abstain")
        self.config["viewer_value"] = "low"
        with self.assertRaises(ValueError):
            self.build()

    def test_model_requires_asset_and_agent_forbids_it(self):
        model = copy.deepcopy(self.config)
        model["reviewer_type"] = "local_model"
        with self.assertRaises(ValueError):
            self.build(model)
        model["reviewer_asset_sha256"] = "a" * 64
        self.assertEqual(self.build(model)["provenance"]["reviewer_type"], "local_model")
        agent = copy.deepcopy(self.config)
        agent["reviewer_asset_sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            self.build(agent)

    def test_raw_schema_is_closed(self):
        schema = local_scene_story_json_schema()
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("chapter_boundary", schema["properties"]["structural_role"]["enum"])


if __name__ == "__main__":
    unittest.main()
