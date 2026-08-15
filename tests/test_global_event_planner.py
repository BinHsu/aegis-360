import copy
from pathlib import Path
import sys
import unittest
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.global_event_planner import plan_global_events
from aegis360.context_views import build_context_view_grid

CURRENT = "context:cardinal:0"
PROPOSED = "context:cardinal:1"


def packet(event_id, start, end):
    return {
        "schema_version": "aegis360.event-review-packet.v1", "source_id": "fixture",
        "event_id": event_id,
        "event_evidence": {"start_seconds": start, "end_seconds": end,
                           "current_candidate_id": CURRENT, "proposed_candidate_id": PROPOSED},
    }


def utility(event_id, current, proposed, eligible=True):
    return {
        "schema_version": "aegis360.event-candidate-utility.v1", "source_id": "fixture",
        "event_id": event_id, "utilities": [
            {"candidate_id": CURRENT, "eligible": True, "total": current},
            {"candidate_id": PROPOSED, "eligible": eligible, "total": proposed},
        ],
    }


class GlobalEventPlannerTests(unittest.TestCase):
    def setUp(self):
        self.policy = {
            "schema_version": "aegis360.global-event-planner-policy.v1",
            "policy_id": "fixture", "minimum_advantage": 0.5,
            "minimum_proposed_dwell_seconds": 2.0, "switch_cost_each_way": 0.5,
            "repeated_proposed_cost": 1.5,
            "angular_cost_per_radian_each_way": 0.1,
        }
        self.grid = build_context_view_grid(
            source_id="fixture", start_seconds=0, duration_seconds=30,
        )

    def plan(self, utilities, packets, policy=None):
        policy = self.policy if policy is None else policy
        digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        return plan_global_events(
            utilities, packets, self.grid, policy,
            utility_sha256s=[digest(value) for value in utilities],
            packet_sha256s=[digest(value) for value in packets],
            grid_sha256=digest(self.grid),
            policy_sha256=digest(policy),
        )

    def test_global_repetition_cost_changes_second_event(self):
        packets = [packet("e0", 10, 15), packet("e1", 20, 25)]
        utilities = [utility("e0", 1, 4), utility("e1", 1, 3)]
        plan = self.plan(utilities, packets)
        self.assertEqual([row["selected_candidate_id"] for row in plan["decisions"]], [PROPOSED, CURRENT])
        self.assertGreater(
            plan["decisions"][0]["planning_cost_components"]["angular_two_way_transition"], 0,
        )

    def test_abstain_and_short_event_fail_closed(self):
        packets = [packet("e0", 10, 11), packet("e1", 20, 25)]
        utilities = [utility("e0", 0, 10), utility("e1", 0, 10, eligible=False)]
        plan = self.plan(utilities, packets)
        self.assertEqual([row["selected_candidate_id"] for row in plan["decisions"]], [CURRENT, CURRENT])

    def test_overlap_and_policy_mutation_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(
                [utility("e0", 0, 1), utility("e1", 0, 1)],
                [packet("e0", 10, 15), packet("e1", 14, 20)],
            )
        broken = copy.deepcopy(self.policy)
        broken["switch_cost_each_way"] = -1
        with self.assertRaises(ValueError):
            self.plan([utility("e0", 0, 1)], [packet("e0", 10, 15)], broken)


if __name__ == "__main__":
    unittest.main()
