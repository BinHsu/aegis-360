import unittest

from tests.test_event_review_packet import build_packet_fixture

from aegis360.event_review_packet import build_event_review_packet
from aegis360.review_media import build_review_render_jobs, build_transient_media_index
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


if __name__ == "__main__":
    unittest.main()
