import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.scene_context import NONIDENTITY_LIMITATION, validate_scene_context


def fixture():
    return {
        "schema_version": "aegis360.scene-context.v2",
        "window": {
            "source_id": "old-ghost-road", "window_id": "t68p5-4s",
            "start_seconds": 68.5, "duration_seconds": 4.0,
        },
        "candidates": [
            {"candidate_id": "person:1", "candidate_type": "person", "member_candidate_ids": []},
            {"candidate_id": "person:2", "candidate_type": "person", "member_candidate_ids": []},
            {"candidate_id": "group:1", "candidate_type": "group", "member_candidate_ids": ["person:1", "person:2"]},
            {"candidate_id": "context:forward", "candidate_type": "context", "member_candidate_ids": []},
        ],
        "provenance": {
            "reviewer_kind": "human", "adapter_id": "owner-review-v1",
            "model_id": None, "model_sha256": None,
        },
        "decision": {
            "context_class": "conversation", "subject_scope": "group",
            "selected_candidate_id": "group:1",
            "evidence_flags": {
                "multiple_people_visible": "present", "face_visible": "present",
                "mouth_motion_visible": "present", "reciprocal_orientation": "unknown",
                "speech_audio_present": "unknown",
            },
        },
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_names": False, "contains_embeddings": False,
        },
        "limitations": [NONIDENTITY_LIMITATION],
    }


class SceneContextTests(unittest.TestCase):
    def test_human_group_context_is_closed_and_path_free(self):
        decision = validate_scene_context(fixture())
        self.assertEqual(decision.subject_scope, "group")
        self.assertEqual(decision.selected_candidate_id, "group:1")
        self.assertEqual(decision.candidates[2].member_candidate_ids, ("person:1", "person:2"))
        self.assertNotIn("/Users/", json.dumps(fixture()))

    def test_scope_must_match_selected_candidate_count(self):
        value = fixture()
        value["decision"]["selected_candidate_id"] = "person:1"
        with self.assertRaisesRegex(ValueError, "type conflicts"):
            validate_scene_context(value)

    def test_group_members_must_reference_declared_person_proposals(self):
        value = fixture()
        value["candidates"][2]["member_candidate_ids"] = ["person:1", "person:missing"]
        with self.assertRaisesRegex(ValueError, "declared person"):
            validate_scene_context(value)

    def test_vlm_requires_checksum_and_cannot_add_geometry_or_text(self):
        value = fixture()
        value["provenance"] = {
            "reviewer_kind": "local_vlm", "adapter_id": "vlm-json-v1",
            "model_id": "local-vlm", "model_sha256": "a" * 64,
        }
        validate_scene_context(value)
        value["decision"]["yaw_degrees"] = 20
        with self.assertRaisesRegex(ValueError, "closed schema"):
            validate_scene_context(value)

    def test_privacy_and_nonidentity_fail_closed(self):
        for mutate in ("path", "limitation"):
            value = copy.deepcopy(fixture())
            if mutate == "path":
                value["privacy"]["contains_source_path"] = True
            else:
                value["limitations"] = []
            with self.assertRaises(ValueError):
                validate_scene_context(value)


if __name__ == "__main__":
    unittest.main()
