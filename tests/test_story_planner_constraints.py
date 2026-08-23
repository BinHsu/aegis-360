import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.story_planner_constraints import build_story_planner_constraints


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def packet(event_id, start):
    return {"schema_version": "aegis360.scene-story-review-packet.v1",
            "source_id": "fixture", "event_id": event_id,
            "event": {"start_seconds": start, "end_seconds": start + 4}}


def semantic(event_id, packet_sha, role, value):
    functions = {"chapter_boundary": "activity_transition",
                 "within_chapter_cut": "action_continuation",
                 "ending_transition": "closing"}
    changes = {"ending_transition": "gradual_transition"}
    return {"schema_version": "aegis360.scene-story-semantics.v1",
            "source_id": "fixture", "event_id": event_id,
            "inputs": {"scene_story_review_packet_sha256": packet_sha},
            "evidence": {"status": "observed", "structural_role": role,
                         "narrative_function": functions[role],
                         "change_type": changes.get(role, "hard_cut"),
                         "viewer_value": value}}


class StoryPlannerConstraintTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / "config/story-planner-constraint-policy-v1.json").read_text())
        self.packets = [packet("e0", 10), packet("e1", 20), packet("e2", 30)]
        roles = [("chapter_boundary", "primary"),
                 ("within_chapter_cut", "supporting"),
                 ("ending_transition", "low")]
        self.semantics = [semantic(value["event_id"], digest(value), role, priority)
                          for value, (role, priority) in zip(self.packets, roles)]

    def build(self, semantics=None, packets=None):
        semantics = self.semantics if semantics is None else semantics
        packets = self.packets if packets is None else packets
        return build_story_planner_constraints(
            semantics, packets, self.policy,
            semantics_sha256s=[digest(value) for value in semantics],
            packet_sha256s=[digest(value) for value in packets],
            policy_sha256=digest(self.policy),
        )

    def test_maps_roles_without_selecting_candidates_or_costs(self):
        value = self.build()
        self.assertEqual([item["transition_preference"] for item in value["constraints"]],
                         ["change_permitted", "continuity_preferred", "closing_hold"])
        self.assertEqual([item["coverage_priority"] for item in value["constraints"]],
                         ["high", "medium", "low"])
        self.assertEqual(value["constraints"][0]["repetition_memory"], "reset")
        self.assertFalse(value["planner_authority"]["candidate_selected"])

    def test_abstain_reorder_and_policy_mutation_fail(self):
        abstain = copy.deepcopy(self.semantics)
        abstain[0]["evidence"]["status"] = "abstain"
        with self.assertRaises(ValueError):
            self.build(abstain)
        with self.assertRaises(ValueError):
            self.build(list(reversed(self.semantics)), list(reversed(self.packets)))
        broken = copy.deepcopy(self.policy)
        broken["structural_rules"]["chapter_boundary"]["repetition_memory"] = "retain"
        with self.assertRaises(ValueError):
            build_story_planner_constraints(
                self.semantics, self.packets, broken,
                semantics_sha256s=[digest(value) for value in self.semantics],
                packet_sha256s=[digest(value) for value in self.packets],
                policy_sha256=digest(broken),
            )


if __name__ == "__main__":
    unittest.main()
