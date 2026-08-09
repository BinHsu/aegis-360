import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.group_shot import GroupShot
from aegis360.scene_context import SceneContextCandidate, SceneContextDecision
from aegis360.window_group import (
    build_window_group_shot, window_group_candidate_frames,
    window_group_scene_candidates,
)


def context(scope="group"):
    return SceneContextDecision(
        "conversation", scope, "group:1" if scope == "group" else "person:1",
        (
            SceneContextCandidate("person:1", "person", ()),
            SceneContextCandidate("person:2", "person", ()),
            SceneContextCandidate("group:1", "group", ("person:1", "person:2")),
        ), {},
    )


def shot(yaw, pitch=-6, fov=90):
    return GroupShot(
        ("left", "right"), math.radians(yaw), math.radians(pitch),
        math.radians(fov), math.radians(40), True,
    )


class WindowGroupTests(unittest.TestCase):
    def test_half_observed_window_builds_nonidentity_stable_pose(self):
        result = build_window_group_shot(
            context(), [shot(53.9), shot(54.1), shot(54.4), shot(54.0)],
            total_sample_count=8,
        )
        self.assertEqual(result.observed_sample_count, 4)
        self.assertEqual(result.observation_ratio, 0.5)
        self.assertEqual(result.minimum_observed_member_count, 2)
        self.assertAlmostEqual(math.degrees(result.yaw), 54.05, places=1)
        self.assertEqual(result.association_provenance, "simultaneous_group_geometry_nonidentity")
        self.assertFalse(hasattr(result, "member_ids"))

    def test_geometry_declares_nonidentity_group_member_slots(self):
        aggregate = build_window_group_shot(
            context(), [shot(54), shot(54.2)], total_sample_count=4,
        )
        candidates = window_group_scene_candidates(aggregate)
        self.assertEqual(
            [candidate.candidate_id for candidate in candidates],
            ["person-slot:1", "person-slot:2", "group:window:1", "context:forward"],
        )
        self.assertEqual(
            candidates[2].member_candidate_ids,
            ("person-slot:1", "person-slot:2"),
        )

    def test_insufficient_coverage_returns_none(self):
        self.assertIsNone(build_window_group_shot(
            context(), [shot(54)], total_sample_count=3,
        ))

    def test_non_group_context_and_invalid_observation_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "group subject scope"):
            build_window_group_shot(context("single"), [shot(54)], total_sample_count=1)
        bad = GroupShot(("only",), 0, 0, 1, 1, True)
        with self.assertRaisesRegex(ValueError, "group shot"):
            build_window_group_shot(context(), [bad], total_sample_count=1)

    def test_seam_aggregation_uses_short_direction(self):
        result = build_window_group_shot(
            context(), [shot(179), shot(-179)], total_sample_count=2,
        )
        self.assertAlmostEqual(abs(math.degrees(result.yaw)), 180, places=6)

    def test_selected_group_proposal_becomes_nonidentity_window_candidate(self):
        aggregate = build_window_group_shot(
            context(), [shot(54), shot(54.2)], total_sample_count=4,
        )
        frames = window_group_candidate_frames(
            context(), aggregate, [0.0, 0.25, 0.5, 0.75],
        )
        self.assertEqual(len(frames), 4)
        for frame in frames:
            group = next(c for c in frame.candidates if c.candidate_type == "group_context")
            self.assertEqual(group.candidate_id, "group:1")
            self.assertEqual(group.covered_candidate_ids, ("person:1", "person:2"))
            self.assertIsNone(group.track_id)
            self.assertFalse(group.editorial_persistence_valid)
            self.assertLess(group.h_fov, math.radians(110))


if __name__ == "__main__":
    unittest.main()
