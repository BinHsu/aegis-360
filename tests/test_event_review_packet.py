import copy
import unittest

from tests.test_event_timeline import build_fixture, digest

from aegis360.event_review_packet import (
    build_event_review_packet,
    validate_event_review_packet,
)
from aegis360.event_timeline import build_event_timeline


def build_packet_fixture():
    grid, grid_sha, roles, reactions, availability = build_fixture()
    timeline = build_event_timeline(
        grid, roles, reactions, availability,
        grid_sha256=grid_sha, roles_sha256=digest(roles),
        reactions_sha256=digest(reactions),
        availability_sha256=digest(availability),
    )
    return grid, grid_sha, roles, reactions, availability, timeline


class EventReviewPacketTests(unittest.TestCase):
    def setUp(self):
        (
            self.grid, self.grid_sha, self.roles, self.reactions,
            self.availability, self.timeline,
        ) = build_packet_fixture()
        self.timeline_sha = digest(self.timeline)

    def packet(self, event_id="event:reaction:0000"):
        return build_event_review_packet(
            self.timeline, self.grid, event_id=event_id,
            timeline_sha256=self.timeline_sha, grid_sha256=self.grid_sha,
        )

    def test_sparse_schedule_and_candidate_availability(self):
        packet = self.packet()
        self.assertEqual(
            [sample["timestamp_seconds"] for sample in packet["samples"]],
            [None, 11.0, 12.0, 13.0, 16.0],
        )
        self.assertEqual(packet["samples"][0]["candidate_ids"], [])
        self.assertEqual(len(packet["samples"][1]["candidate_ids"]), 1)
        self.assertEqual(len(packet["samples"][2]["candidate_ids"]), 2)
        self.assertFalse(packet["privacy"]["contains_editorial_decision"])
        self.assertFalse(packet["temporary_media_policy"]["durable_pixels_allowed"])

    def test_boundary_context_is_explicitly_missing(self):
        packet = self.packet()
        self.assertIsNone(packet["samples"][0]["timestamp_seconds"])
        second = self.packet("event:reaction:0001")
        self.assertIsNotNone(second["samples"][-1]["timestamp_seconds"])

    def test_exact_rebuild_rejects_decision_and_invented_candidate(self):
        packet = self.packet()
        validate_event_review_packet(
            packet, self.timeline, self.grid,
            timeline_sha256=self.timeline_sha, grid_sha256=self.grid_sha,
        )
        for mutation in (
            lambda value: value.update({"decision": "promote"}),
            lambda value: value["samples"][0]["candidate_ids"].append("invented"),
        ):
            broken = copy.deepcopy(packet)
            mutation(broken)
            with self.assertRaises(ValueError):
                validate_event_review_packet(
                    broken, self.timeline, self.grid,
                    timeline_sha256=self.timeline_sha, grid_sha256=self.grid_sha,
                )


if __name__ == "__main__":
    unittest.main()
