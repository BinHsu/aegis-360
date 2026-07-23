import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.greedy_planner import (  # noqa: E402
    CandidateObservation,
    GreedyConfig,
    Observation,
    ScoreComponent,
    dumps_trace,
    plan_greedy_with_hysteresis,
)


def candidate(candidate_id, score, yaw=0.0):
    return CandidateObservation(
        candidate_id=candidate_id,
        yaw=math.radians(yaw),
        pitch=0.0,
        h_fov=math.radians(90),
        candidate_type="subject",
        components=(ScoreComponent("interest", score, score, 1.0, "fixture"),),
    )


def decisions(rows, config=GreedyConfig(minimum_dwell_seconds=1, switch_margin=0.1, challenger_hold_seconds=1)):
    observations = tuple(
        Observation(timestamp, tuple(candidate(*values) for values in candidates))
        for timestamp, candidates in rows
    )
    return plan_greedy_with_hysteresis(observations, config)["decisions"]


class GreedyPlannerBehaviorTests(unittest.TestCase):
    def test_transient_distraction_does_not_switch(self):
        result = decisions(((0, (("a", .7), ("b", .2))), (1, (("a", .5), ("b", .9))), (2, (("a", .7), ("b", .2)))))
        self.assertEqual([item["selected_candidate_id"] for item in result], ["a", "a", "a"])
        self.assertEqual(result[1]["reason"], "challenger_hysteresis")

    def test_sustained_better_candidate_switches_after_hold(self):
        result = decisions(((0, (("a", .7), ("b", .2))), (1, (("a", .5), ("b", .9))), (2, (("a", .4), ("b", .9)))))
        self.assertEqual([item["selected_candidate_id"] for item in result], ["a", "a", "b"])
        self.assertEqual(result[2]["reason"], "sustained_challenger")

    def test_tie_break_is_deterministic(self):
        result = decisions(((0, (("z", .5), ("a", .5))),))
        self.assertEqual(result[0]["selected_candidate_id"], "a")

    def test_missing_incumbent_uses_best_fallback_and_warns(self):
        trace = plan_greedy_with_hysteresis((
            Observation(0, (candidate("a", .8),)),
            Observation(1, (candidate("b", .2), candidate("c", .7))),
        ))
        self.assertEqual(trace["decisions"][1]["selected_candidate_id"], "c")
        self.assertEqual(trace["decisions"][1]["reason"], "incumbent_missing_fallback")
        self.assertTrue(trace["warnings"])

    def test_seam_transition_uses_short_spherical_distance(self):
        result = decisions(
            ((0, (("a", .8, 179),)), (1, (("b", .9, -179),))),
            GreedyConfig(minimum_dwell_seconds=0, switch_margin=0, challenger_hold_seconds=0),
        )
        distance = result[1]["transition"]["angular_distance_radians"]
        self.assertAlmostEqual(math.degrees(distance), 2.0, places=6)

    def test_trace_contains_components_and_is_strict_deterministic_json(self):
        observation = Observation(0, (candidate("a", .75),))
        first = dumps_trace(plan_greedy_with_hysteresis((observation,)))
        second = dumps_trace(plan_greedy_with_hysteresis((observation,)))
        self.assertEqual(first, second)
        decoded = json.loads(first)
        component = decoded["decisions"][0]["candidates"][0]["score_components"][0]
        self.assertEqual(component["contribution"], .75)
        self.assertEqual(component["provenance"], "fixture")


if __name__ == "__main__":
    unittest.main()
