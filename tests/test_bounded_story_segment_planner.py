import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.bounded_story_segment_planner import plan_bounded_story_segments
from aegis360.context_views import build_context_view_grid


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class BoundedStorySegmentPlannerTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                            duration_seconds=30)
        self.timeline = {"schema_version": "aegis360.story-segment-timeline.v1",
                         "source_id": "fixture", "segments": [
            {"segment_id": "s0", "start_seconds": 0, "end_seconds": 10,
             "left_boundary": None, "right_boundary": {"event_id": "e0"}},
            {"segment_id": "s1", "start_seconds": 10, "end_seconds": 20,
             "left_boundary": {"event_id": "e0"}, "right_boundary": {"event_id": "e1"}},
            {"segment_id": "s2", "start_seconds": 20, "end_seconds": 30,
             "left_boundary": {"event_id": "e1"}, "right_boundary": None},
        ]}
        self.constraints = {"schema_version": "aegis360.story-planner-constraints.v1",
                            "source_id": "fixture", "constraints": [
            {"event_id": "e0", "transition_preference": "continuity_preferred"},
            {"event_id": "e1", "transition_preference": "change_permitted"},
        ]}
        self.policy = json.loads((ROOT / "config/bounded-story-segment-planner-policy-v1.json").read_text())

    def relevance(self, segment, primary, status="observed", current_relevance="supporting"):
        observations = []
        if status == "observed":
            for candidate in self.grid["candidates"]:
                candidate_id = candidate["candidate_id"]
                observations.append({"candidate_id": candidate_id, "visibility": "clear",
                                     "segment_relevance": ("primary" if candidate_id == primary else
                                                           current_relevance if candidate_id == "context:cardinal:0" else "low"),
                                     "temporal_consistency": "stable"})
        return {"schema_version": "aegis360.segment-view-relevance.v1",
                "source_id": "fixture", "segment_id": segment,
                "evidence": {"status": status, "candidate_observations": observations}}

    def plan(self, relevances, start=0, end=30, policy=None):
        policy = self.policy if policy is None else policy
        return plan_bounded_story_segments(
            self.timeline, self.constraints, relevances, self.grid, policy,
            start_seconds=start, end_seconds=end,
            segment_timeline_sha256=digest(self.timeline),
            constraints_sha256=digest(self.constraints),
            relevance_sha256s=[digest(value) for value in relevances],
            grid_sha256=digest(self.grid), policy_sha256=digest(policy),
        )

    def test_continuity_keeps_supporting_then_chapter_switches(self):
        proposed = "context:cardinal:1"
        value = self.plan([self.relevance("s1", proposed), self.relevance("s2", proposed)])
        self.assertEqual([item["selected_candidate_id"] for item in value["decisions"]],
                         ["context:cardinal:0", "context:cardinal:0", proposed])
        self.assertEqual(value["decisions"][1]["reason"], "continuity_keeps_usable_current")
        self.assertFalse(value["planner_authority"]["numeric_costs_applied"])
        self.assertFalse(value["planner_authority"]["production_eligible"])

    def test_abstain_unreviewed_and_aligned_window_retain(self):
        value = self.plan([self.relevance("s1", "context:cardinal:1", "abstain")],
                          start=10, end=30)
        self.assertEqual([item["evidence_status"] for item in value["decisions"]],
                         ["abstain", "unreviewed"])
        self.assertEqual({item["selected_candidate_id"] for item in value["decisions"]},
                         {"context:cardinal:0"})
        with self.assertRaises(ValueError):
            self.plan([], start=5, end=30)

    def test_policy_mutation_and_candidate_order_fail(self):
        broken_policy = copy.deepcopy(self.policy)
        broken_policy["abstain_behavior"] = "choose_primary"
        with self.assertRaises(ValueError):
            self.plan([], policy=broken_policy)
        relevance = self.relevance("s1", "context:cardinal:1")
        relevance["evidence"]["candidate_observations"].reverse()
        with self.assertRaises(ValueError):
            self.plan([relevance])


if __name__ == "__main__":
    unittest.main()
