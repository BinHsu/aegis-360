import unittest

from tests.test_event_review_packet import build_packet_fixture

from aegis360.event_review_packet import build_event_review_packet
from aegis360.review_media import (build_review_render_jobs, build_story_review_render_jobs,
                                   build_story_transient_media_index,
                                   build_transient_media_index)
from tests.test_scene_story_packet import build_story_fixture, digest as story_digest
from tests.test_event_timeline import digest


class ReviewMediaTests(unittest.TestCase):
    def setUp(self):
        self.grid, grid_sha, _, _, _, timeline = build_packet_fixture()
        self.packet = build_event_review_packet(
            timeline, self.grid, event_id="event:reaction:0000",
            timeline_sha256=digest(timeline), grid_sha256=grid_sha,
        )

    def test_jobs_resolve_only_scheduled_candidates(self):
        jobs = build_review_render_jobs(self.packet, self.grid)
        self.assertEqual(len(jobs), 6)
        self.assertNotIn("context-cardinal-1", jobs[0]["filename"])
        self.assertEqual({job["width"] for job in jobs}, {384})
        index = build_transient_media_index(self.packet, jobs)
        self.assertFalse(index["audio_provided"])
        self.assertNotIn("yaw_degrees", index["frames"][0])

    def test_dimensions_and_invented_candidate_fail_closed(self):
        with self.assertRaises(ValueError):
            build_review_render_jobs(self.packet, self.grid, width=4000)
        self.packet["samples"][1]["candidate_ids"].append("invented")
        with self.assertRaises(ValueError):
            build_review_render_jobs(self.packet, self.grid)

    def test_story_jobs_bound_six_composites_and_hide_geometry_from_index(self):
        grid, grid_sha, timeline = build_story_fixture()
        from aegis360.scene_story_packet import build_scene_story_packet
        packet = build_scene_story_packet(
            timeline, grid, event_id="event:multi:0001",
            timeline_sha256=story_digest(timeline), grid_sha256=grid_sha,
        )
        jobs = build_story_review_render_jobs(packet, grid)
        self.assertEqual(len(jobs), 6)
        self.assertEqual((jobs[0]["width"], jobs[0]["height"]), (768, 432))
        self.assertEqual(len(jobs[0]["viewports"]), 4)
        index = build_story_transient_media_index(packet, jobs)
        self.assertEqual(len(index["frames"]), 6)
        self.assertNotIn("yaw_degrees", index["frames"][0])
        self.assertEqual(index["frames"][0]["representation"],
                         "four_cardinal_contact_sheet")


if __name__ == "__main__":
    unittest.main()
