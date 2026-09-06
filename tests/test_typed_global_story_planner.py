import copy, hashlib, json, math, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.typed_global_story_planner import (build_typed_global_story_plan,
                                                validate_typed_global_story_plan)
from tests.test_typed_story_segment_timeline import TypedStorySegmentTimelineTests

def digest(value): return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

class TypedGlobalStoryPlannerTests(unittest.TestCase):
    def setUp(self):
        fixture = TypedStorySegmentTimelineTests(); fixture.setUp()
        self.grid = fixture.grid; self.timeline = fixture.build()
        self.ids = [row["candidate_id"] for row in self.grid["candidates"]]
        self.initial, self.proposed = self.ids[:2]
        self.policy = json.loads((ROOT / "config/global-story-segment-planner-policy-v1.json").read_text())
        self.policy["minimum_dwell_seconds"] = 0.5
        self.utilities = [self.utility(s["segment_id"], "abstain") for s in self.timeline["segments"]]
        self.continuity = self.edges()
    def utility(self, segment, status="observed", proposed=0):
        totals = {self.initial: 0, self.proposed: proposed}
        rows = [{"candidate_id": cid, "eligible": status == "observed",
                 "components": {"segment_relevance": (totals.get(cid, -10)
                                                       if status == "observed" else 0), "visibility": 0,
                                "temporal_consistency": 0},
                 "total": totals.get(cid, -10) if status == "observed" else 0.0}
                for cid in self.ids]
        return {"schema_version": "aegis360.segment-candidate-utility.v1",
                "source_id": "fixture", "segment_id": segment,
                "inputs": {"segment_view_relevance_sha256": "a"*64,
                           "context_view_grid_sha256": digest(self.grid),
                           "utility_policy_sha256": "b"*64},
                "policy_id":"fixture", "evidence_status": status, "utilities": rows,
                "planner_authority":{"candidate_selected":False,
                    "transition_costs_applied":False,"minimum_dwell_applied":False},
                "limitations":["fixture"]}
    def edges(self):
        edges=[]
        for left,right in zip(self.timeline["segments"],self.timeline["segments"][1:]):
            transitions=[]
            for a in self.ids:
                for b in self.ids:
                    transitions.append({"previous_candidate_id":a,"next_candidate_id":b,
                        "components":{"from_cue_support":0,"to_cue_support":0,
                                      "same_candidate_preservation":0},"total":0})
            edges.append({"from_segment_id":left["segment_id"],"to_segment_id":right["segment_id"],
                          "evidence_status":"observed","transitions":transitions})
        return {"schema_version":"aegis360.continuity-transition-utility.v1",
                "source_id":"fixture","inputs":{"causal_continuity_evidence_sha256":"a"*64,
                    "context_view_grid_sha256":digest(self.grid),
                    "continuity_transition_utility_policy_sha256":"b"*64},
                "policy_id":"fixture", "edge_utilities":edges,
                "planner_authority":{"candidate_selected":False,"transition_selected":False,
                    "transition_costs_applied":False,"renderer_command_emitted":False},
                "limitations":["fixture"]}
    def build(self, timeline=None, utilities=None, continuity=None):
        timeline=timeline or self.timeline; utilities=self.utilities if utilities is None else utilities
        continuity=self.continuity if continuity is None else continuity
        return build_typed_global_story_plan(timeline,utilities,continuity,self.grid,self.policy,
            timeline_sha256=digest(timeline),utility_sha256s=[digest(x) for x in utilities],
            continuity_sha256=digest(continuity),grid_sha256=digest(self.grid),policy_sha256=digest(self.policy))
    def test_chapter_maps_change_and_numeric_dp_switches_once(self):
        self.timeline["segments"][1]["left_boundary"]["typed_labels"]["structural_role"] = "chapter_boundary"
        self.timeline["segments"][0]["right_boundary"]["typed_labels"]["structural_role"] = "chapter_boundary"
        self.utilities[1]=self.utility(self.timeline["segments"][1]["segment_id"], proposed=4)
        result=self.build(); decision=result["decisions"][1]
        self.assertEqual(decision["transition_preference"],"change_permitted")
        self.assertEqual(decision["selected_candidate_id"],self.proposed)
        self.assertGreater(decision["planning_cost"],0)
        validate_typed_global_story_plan(result,self.timeline,self.utilities,self.continuity,self.grid,self.policy,
            timeline_sha256=digest(self.timeline),utility_sha256s=[digest(x) for x in self.utilities],
            continuity_sha256=digest(self.continuity),grid_sha256=digest(self.grid),policy_sha256=digest(self.policy))
    def test_zero_boundary_abstain_retains_initial(self):
        timeline=copy.deepcopy(self.timeline); timeline["segments"]=[{
            "segment_id":"only","start_seconds":385.0,"end_seconds":387.0,
            "left_boundary":None,"right_boundary":None}]
        utilities=[self.utility("only","abstain")]
        continuity=copy.deepcopy(self.continuity); continuity["edge_utilities"]=[]
        result=self.build(timeline,utilities,continuity)
        self.assertEqual(result["decisions"][0]["selected_candidate_id"],self.initial)
        self.assertEqual(result["decisions"][0]["transition_preference"],"no_constraint")
        self.assertFalse(result["planner_authority"]["production_eligible"])
    def test_within_and_ending_roles_map_without_legacy_constraints(self):
        for role,expected in (("within_chapter_cut","continuity_preferred"),
                              ("ending_transition","closing_hold")):
            timeline=copy.deepcopy(self.timeline)
            timeline["segments"][1]["left_boundary"]["typed_labels"]["structural_role"]=role
            timeline["segments"][0]["right_boundary"]["typed_labels"]["structural_role"]=role
            utilities=copy.deepcopy(self.utilities); utilities[1]=self.utility(timeline["segments"][1]["segment_id"],proposed=10)
            result=self.build(timeline,utilities)
            self.assertEqual(result["decisions"][1]["transition_preference"],expected)
            if role=="ending_transition": self.assertEqual(result["decisions"][1]["selected_candidate_id"],self.initial)
    def test_lineage_order_edge_and_exact_tamper_fail(self):
        legacy=copy.deepcopy(self.timeline); legacy["schema_version"]="aegis360.story-segment-timeline.v1"
        with self.assertRaises(ValueError): self.build(legacy)
        with self.assertRaises(ValueError): self.build(utilities=list(reversed(self.utilities)))
        broken=copy.deepcopy(self.continuity); broken["edge_utilities"]=[]
        with self.assertRaises(ValueError): self.build(continuity=broken)
        result=self.build(); result["objective"]+=1
        with self.assertRaises(ValueError):
            validate_typed_global_story_plan(result,self.timeline,self.utilities,self.continuity,self.grid,self.policy,
                timeline_sha256=digest(self.timeline),utility_sha256s=[digest(x) for x in self.utilities],
                continuity_sha256=digest(self.continuity),grid_sha256=digest(self.grid),policy_sha256=digest(self.policy))
    def test_audit_closed_shapes_eligibility_and_abstention_authority(self):
        malformed = copy.deepcopy(self.timeline); malformed["segments"][0] = None
        with self.assertRaises(ValueError): self.build(malformed)
        utility = self.utility(self.timeline["segments"][0]["segment_id"], proposed=2)
        utility["utilities"][0]["eligible"] = False
        utilities = copy.deepcopy(self.utilities); utilities[0] = utility
        with self.assertRaises(ValueError): self.build(utilities=utilities)
        continuity = copy.deepcopy(self.continuity)
        continuity["edge_utilities"][0]["evidence_status"] = "abstain"
        result = self.build(continuity=continuity)
        self.assertFalse(result["planner_authority"]["production_eligible"])
        self.assertIn("pre-cost local pruning", result["limitations"][2])
        broken = copy.deepcopy(self.continuity); broken["planner_authority"] = None
        with self.assertRaises(ValueError): self.build(continuity=broken)

if __name__ == "__main__": unittest.main()
