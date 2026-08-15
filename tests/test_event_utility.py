import copy
import unittest

from tests.test_event_semantics import build_semantics_fixture
from tests.test_event_timeline import digest

from aegis360.event_utility import build_event_candidate_utility


class EventUtilityTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.config = build_semantics_fixture()
        from aegis360.event_semantics import build_event_semantics
        self.semantics = build_event_semantics(
            self.config, self.packet, config_sha256=digest(self.config),
            packet_sha256=digest(self.packet),
        )
        self.policy = {
            "schema_version": "aegis360.event-utility-policy.v1",
            "policy_id": "poc-explainable-v1",
            "relevance_weights": {"primary": 2, "supporting": 1, "unrelated": -2, "unknown": 0},
            "visibility_weights": {"clear": 1, "partial": 0, "obstructed": -2, "unknown": 0},
            "temporal_weights": {"stable": 0.5, "changing": 0, "unknown": 0},
            "relationship_weights": {"complements_current": 2, "duplicates_current": -1, "unrelated": -2, "unknown": 0},
        }

    def build(self):
        return build_event_candidate_utility(
            self.semantics, self.packet, self.policy,
            semantics_sha256=digest(self.semantics), packet_sha256=digest(self.packet),
            policy_sha256=digest(self.policy),
        )

    def test_explainable_components_do_not_select_candidate(self):
        value = self.build()
        current, proposed = value["utilities"]
        self.assertEqual(current["total"], 3.5)
        self.assertEqual(proposed["total"], 4.5)
        self.assertFalse(value["planner_authority"]["candidate_selected"])

    def test_abstention_fails_closed_to_current_eligibility(self):
        config = copy.deepcopy(self.config)
        config.update({"status": "abstain", "event_class": "unknown", "view_relationship": "unknown", "candidate_observations": []})
        from aegis360.event_semantics import build_event_semantics
        self.semantics = build_event_semantics(
            config, self.packet, config_sha256=digest(config), packet_sha256=digest(self.packet),
        )
        current, proposed = self.build()["utilities"]
        self.assertTrue(current["eligible"])
        self.assertFalse(proposed["eligible"])
        self.assertEqual(current["total"], 0.0)

    def test_policy_shape_and_lineage_fail_closed(self):
        broken = copy.deepcopy(self.policy)
        del broken["visibility_weights"]["unknown"]
        self.policy = broken
        with self.assertRaises(ValueError):
            self.build()
        self.policy = {
            "schema_version": "aegis360.event-utility-policy.v1", "policy_id": "bad",
            "relevance_weights": {"primary": 2, "supporting": 1, "unrelated": -2, "unknown": 0},
            "visibility_weights": {"clear": 1, "partial": 0, "obstructed": -2, "unknown": 0},
            "temporal_weights": {"stable": .5, "changing": 0, "unknown": 0},
            "relationship_weights": {"complements_current": 2, "duplicates_current": -1, "unrelated": -2, "unknown": 0},
        }
        with self.assertRaises(ValueError):
            build_event_candidate_utility(
                self.semantics, self.packet, self.policy,
                semantics_sha256=digest(self.semantics), packet_sha256="0" * 64,
                policy_sha256=digest(self.policy),
            )


if __name__ == "__main__":
    unittest.main()
