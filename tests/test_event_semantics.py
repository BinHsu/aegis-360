import copy
import unittest

from tests.test_event_review_packet import build_packet_fixture
from tests.test_event_timeline import digest

from aegis360.event_review_packet import build_event_review_packet
from aegis360.event_semantics import build_event_semantics, validate_event_semantics
from aegis360.local_event_semantics_schema import local_event_semantics_json_schema


def build_semantics_fixture():
    grid, grid_sha, _, _, _, timeline = build_packet_fixture()
    packet = build_event_review_packet(
        timeline, grid, event_id="event:reaction:0000",
        timeline_sha256=digest(timeline), grid_sha256=grid_sha,
    )
    config = {
        "schema_version": "aegis360.event-semantic-evidence-config.v1",
        "adapter_id": "fixture-adapter", "model_id": "fixture/model",
        "model_sha256": "a" * 64, "status": "observed",
        "event_class": "audience_reaction",
        "view_relationship": "complements_current",
        "candidate_observations": [
            {"candidate_id": "context:cardinal:3", "visibility": "clear", "event_relevance": "primary", "temporal_consistency": "stable"},
            {"candidate_id": "context:cardinal:1", "visibility": "clear", "event_relevance": "supporting", "temporal_consistency": "stable"},
        ],
    }
    return packet, config


class EventSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.packet, self.config = build_semantics_fixture()

    def build(self):
        return build_event_semantics(
            self.config, self.packet, config_sha256=digest(self.config),
            packet_sha256=digest(self.packet),
        )

    def test_closed_observations_bind_packet_candidates(self):
        value = self.build()
        validate_event_semantics(
            value, self.config, self.packet, config_sha256=digest(self.config),
            packet_sha256=digest(self.packet),
        )
        self.assertFalse(value["privacy"]["contains_editorial_decision"])

    def test_abstention_carries_no_claims(self):
        self.config.update({
            "status": "abstain", "event_class": "unknown",
            "view_relationship": "unknown", "candidate_observations": [],
        })
        self.assertEqual(self.build()["evidence"]["candidate_observations"], [])
        self.config["event_class"] = "audience_reaction"
        with self.assertRaises(ValueError):
            self.build()

    def test_invented_or_reordered_candidates_fail(self):
        for ids in (
            ["invented", "context:cardinal:1"],
            ["context:cardinal:1", "context:cardinal:3"],
        ):
            broken = copy.deepcopy(self.config)
            for item, candidate_id in zip(broken["candidate_observations"], ids):
                item["candidate_id"] = candidate_id
            with self.assertRaises(ValueError):
                build_event_semantics(
                    broken, self.packet, config_sha256=digest(broken),
                    packet_sha256=digest(self.packet),
                )

    def test_raw_schema_is_closed_and_candidate_bounded(self):
        schema = local_event_semantics_json_schema([
            "context:cardinal:3", "context:cardinal:1",
        ])
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["candidate_observations"]["maxItems"], 2)


if __name__ == "__main__":
    unittest.main()
