import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.context_views import build_context_view_grid
from aegis360.global_story_segment_planner import (plan_global_story_segments,
                                                   plan_global_story_segments_v2,
                                                   validate_global_story_segment_plan,
                                                   validate_global_story_segment_plan_v2)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class GlobalStorySegmentPlannerTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                            duration_seconds=30)
        self.current = "context:cardinal:0"
        self.proposed = "context:cardinal:1"
        self.timeline = {
            "schema_version": "aegis360.story-segment-timeline.v1",
            "source_id": "fixture", "segments": [
                {"segment_id": "s0", "start_seconds": 0, "end_seconds": 10,
                 "left_boundary": None, "right_boundary": {"event_id": "e0"}},
                {"segment_id": "s1", "start_seconds": 10, "end_seconds": 20,
                 "left_boundary": {"event_id": "e0"}, "right_boundary": {"event_id": "e1"}},
                {"segment_id": "s2", "start_seconds": 20, "end_seconds": 30,
                 "left_boundary": {"event_id": "e1"}, "right_boundary": None},
            ],
        }
        self.constraints = {
            "schema_version": "aegis360.story-planner-constraints.v1",
            "source_id": "fixture", "constraints": [
                {"event_id": "e0", "transition_preference": "change_permitted"},
                {"event_id": "e1", "transition_preference": "closing_hold"},
            ],
        }
        self.policy = json.loads(
            (ROOT / "config/global-story-segment-planner-policy-v1.json").read_text()
        )

    def utility(self, segment, current, proposed, status="observed"):
        rows = []
        if status == "observed":
            totals = {self.current: current, self.proposed: proposed}
            rows = [{"candidate_id": candidate["candidate_id"], "eligible": True,
                     "components": {"segment_relevance": totals.get(candidate["candidate_id"], -10),
                                    "visibility": 0, "temporal_consistency": 0},
                     "total": totals.get(candidate["candidate_id"], -10)}
                    for candidate in self.grid["candidates"]]
        else:
            rows = [{"candidate_id": candidate["candidate_id"], "eligible": False,
                     "components": {"segment_relevance": 0, "visibility": 0,
                                    "temporal_consistency": 0}, "total": 0.0}
                    for candidate in self.grid["candidates"]]
        return {"schema_version": "aegis360.segment-candidate-utility.v1",
                "source_id": "fixture", "segment_id": segment,
                "inputs": {"context_view_grid_sha256": digest(self.grid)},
                "evidence_status": status, "utilities": rows}

    def complete(self, overrides=()):
        by_id = {item["segment_id"]: item for item in overrides}
        return [by_id.get(segment["segment_id"],
                          self.utility(segment["segment_id"], 0, 0, "abstain"))
                for segment in self.timeline["segments"]]

    def plan(self, utilities, timeline=None, constraints=None):
        timeline = self.timeline if timeline is None else timeline
        constraints = self.constraints if constraints is None else constraints
        return plan_global_story_segments(
            timeline, constraints, utilities, self.grid, self.policy,
            timeline_sha256=digest(timeline), constraints_sha256=digest(constraints),
            utility_sha256s=[digest(value) for value in utilities],
            grid_sha256=digest(self.grid), policy_sha256=digest(self.policy),
        )

    def continuity(self, same_bonus=0.0):
        ids = [item["candidate_id"] for item in self.grid["candidates"]]
        edges = []
        for left, right in zip(self.timeline["segments"], self.timeline["segments"][1:]):
            transitions = []
            for previous in ids:
                for following in ids:
                    value = same_bonus if previous == following else 0.0
                    transitions.append({
                        "previous_candidate_id": previous,
                        "next_candidate_id": following,
                        "components": {"from_cue_support": 0.0,
                                       "to_cue_support": 0.0,
                                       "same_candidate_preservation": value},
                        "total": value,
                    })
            edges.append({"from_segment_id": left["segment_id"],
                          "to_segment_id": right["segment_id"],
                          "evidence_status": "observed",
                          "transitions": transitions})
        return {
            "schema_version": "aegis360.continuity-transition-utility.v1",
            "source_id": "fixture",
            "inputs": {"context_view_grid_sha256": digest(self.grid)},
            "edge_utilities": edges,
        }

    def plan_v2(self, utilities, continuity):
        return plan_global_story_segments_v2(
            self.timeline, self.constraints, utilities, continuity,
            self.grid, self.policy,
            timeline_sha256=digest(self.timeline),
            constraints_sha256=digest(self.constraints),
            utility_sha256s=[digest(value) for value in utilities],
            continuity_utility_sha256=digest(continuity),
            grid_sha256=digest(self.grid), policy_sha256=digest(self.policy),
        )

    def test_equal_utility_ninety_degree_view_retains_current(self):
        utilities = self.complete([self.utility("s1", 2, 2)])
        value = self.plan(utilities)
        self.assertEqual({row["selected_candidate_id"] for row in value["decisions"]},
                         {self.current})
        self.assertTrue(value["planner_authority"]["numeric_costs_applied"])
        self.assertTrue(value["planner_authority"]["production_eligible"])
        validate_global_story_segment_plan(
            value, self.timeline, self.constraints, utilities, self.grid, self.policy,
            timeline_sha256=digest(self.timeline),
            constraints_sha256=digest(self.constraints),
            utility_sha256s=[digest(item) for item in utilities],
            grid_sha256=digest(self.grid), policy_sha256=digest(self.policy),
        )
        value["decisions"][0]["selected_candidate_id"] = self.proposed
        with self.assertRaises(ValueError):
            validate_global_story_segment_plan(
                value, self.timeline, self.constraints, utilities, self.grid, self.policy,
                timeline_sha256=digest(self.timeline),
                constraints_sha256=digest(self.constraints),
                utility_sha256s=[digest(item) for item in utilities],
                grid_sha256=digest(self.grid), policy_sha256=digest(self.policy),
            )

    def test_gain_must_pay_single_transition_cost(self):
        transition = self.policy["switch_cost"] + math.pi / 2 * self.policy["angular_cost_per_radian"]
        rejected = self.plan(self.complete([self.utility("s1", 0, transition - 0.01)]))
        accepted = self.plan(self.complete([self.utility("s1", 0, transition + 0.01)]))
        self.assertEqual(rejected["decisions"][1]["selected_candidate_id"], self.current)
        decision = accepted["decisions"][1]
        self.assertEqual(decision["selected_candidate_id"], self.proposed)
        self.assertAlmostEqual(decision["planning_cost"], transition)
        self.assertAlmostEqual(decision["angular_distance_radians"], math.pi / 2)

    def test_missing_abstain_and_closing_retain_persistent_candidate(self):
        value = self.plan(self.complete([
            self.utility("s1", 0, 4),
            self.utility("s2", 0, 10),
        ]))
        self.assertEqual([row["selected_candidate_id"] for row in value["decisions"]],
                         [self.current, self.proposed, self.proposed])
        self.assertEqual(value["decisions"][0]["evidence_status"], "abstain")
        abstained = self.plan(self.complete([self.utility("s1", 0, 10, status="abstain")]))
        self.assertEqual({row["selected_candidate_id"] for row in abstained["decisions"]},
                         {self.current})

    def test_lineage_and_complete_window_fail_closed(self):
        broken = copy.deepcopy(self.timeline)
        broken["segments"][-1]["end_seconds"] = 29
        with self.assertRaises(ValueError):
            self.plan(self.complete(), timeline=broken)
        wrong_source = self.utility("s1", 0, 4)
        wrong_source["source_id"] = "other"
        with self.assertRaises(ValueError):
            self.plan(self.complete([wrong_source]))
        duplicate = self.complete()
        with self.assertRaises(ValueError):
            self.plan(duplicate + [duplicate[-1]])
        missing_constraint = copy.deepcopy(self.constraints)
        missing_constraint["constraints"].pop()
        with self.assertRaises(ValueError):
            self.plan(self.complete(), constraints=missing_constraint)

    def test_v2_continuity_ablation_changes_a_like_switch_to_baseline(self):
        utilities = self.complete([self.utility("s1", 0, 2)])
        zero = self.continuity(same_bonus=0)
        observed = self.continuity(same_bonus=2)
        a_like = self.plan_v2(utilities, zero)
        baseline_like = self.plan_v2(utilities, observed)
        self.assertEqual(a_like["schema_version"],
                         "aegis360.global-story-segment-plan.v2")
        self.assertEqual(a_like["decisions"][1]["selected_candidate_id"],
                         self.proposed)
        self.assertEqual(baseline_like["decisions"][1]["selected_candidate_id"],
                         self.current)
        self.assertTrue(baseline_like["planner_authority"]["continuity_utility_applied"])
        validate_global_story_segment_plan_v2(
            baseline_like, self.timeline, self.constraints, utilities, observed,
            self.grid, self.policy,
            timeline_sha256=digest(self.timeline),
            constraints_sha256=digest(self.constraints),
            utility_sha256s=[digest(value) for value in utilities],
            continuity_utility_sha256=digest(observed),
            grid_sha256=digest(self.grid), policy_sha256=digest(self.policy),
        )

    def test_v2_rejects_tampered_matrix_and_edge_mismatch(self):
        utilities = self.complete([self.utility("s1", 0, 2)])
        tampered = self.continuity()
        tampered["edge_utilities"][0]["transitions"][0]["total"] = 1
        with self.assertRaises(ValueError):
            self.plan_v2(utilities, tampered)
        mismatch = self.continuity()
        mismatch["edge_utilities"][0]["to_segment_id"] = "s2"
        with self.assertRaises(ValueError):
            self.plan_v2(utilities, mismatch)


if __name__ == "__main__":
    unittest.main()
