import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.group_shot import (
    CompositionAnchor,
    GroupMember,
    GroupShotConfig,
    apply_vertical_composition_anchors,
    build_group_shot,
    build_group_shots,
)


def member(identifier, yaw, pitch=0.0, extent=10.0):
    return GroupMember(
        identifier,
        math.radians(yaw),
        math.radians(pitch),
        math.radians(extent),
    )


class GroupShotTests(unittest.TestCase):
    def test_face_anchor_shifts_pitch_without_changing_group_coverage(self):
        shot = build_group_shot([
            member("left", 48, -27), member("right", 61, -24),
        ])
        corrected = apply_vertical_composition_anchors(
            shot, [CompositionAnchor(math.radians(61), math.radians(-6))],
        )
        self.assertAlmostEqual(math.degrees(corrected.pitch), -6)
        self.assertEqual(corrected.member_ids, shot.member_ids)
        self.assertEqual(corrected.yaw, shot.yaw)
        self.assertEqual(corrected.horizontal_fov, shot.horizontal_fov)
        self.assertEqual(corrected.fully_contains_members, shot.fully_contains_members)

    def test_unrelated_face_is_ignored_and_correction_is_bounded(self):
        shot = build_group_shot([member("a", 0, -30), member("b", 10, -30)])
        unrelated = apply_vertical_composition_anchors(
            shot, [CompositionAnchor(math.radians(150), 0)],
        )
        self.assertEqual(unrelated, shot)
        bounded = apply_vertical_composition_anchors(
            shot, [CompositionAnchor(math.radians(5), math.radians(30))],
            maximum_pitch_correction=math.radians(20),
        )
        self.assertAlmostEqual(
            bounded.pitch, shot.pitch + math.radians(20), places=12,
        )

    def test_seam_neighbors_center_at_seam_not_forward(self):
        result = build_group_shot([
            member("left", -179.0),
            member("right", 179.0),
        ])
        self.assertIsNotNone(result)
        self.assertGreater(abs(math.degrees(result.yaw)), 179.0)
        self.assertTrue(result.fully_contains_members)
        self.assertAlmostEqual(
            math.degrees(result.horizontal_fov), 90.0
        )

    def test_wide_group_clamps_and_reports_incomplete_coverage(self):
        result = build_group_shot([
            member("a", -70.0),
            member("b", 70.0),
        ])
        self.assertIsNotNone(result)
        self.assertAlmostEqual(
            math.degrees(result.horizontal_fov), 110.0
        )
        self.assertFalse(result.fully_contains_members)
        self.assertGreater(
            result.required_horizontal_fov, result.horizontal_fov
        )

    def test_distant_regions_form_bounded_local_groups(self):
        shots = build_group_shots([
            member("a", -150.0),
            member("b", -140.0),
            member("c", 10.0),
            member("d", 20.0),
            member("isolated", 90.0),
        ])
        self.assertEqual(
            {shot.member_ids for shot in shots},
            {("a", "b"), ("c", "d")},
        )
        self.assertTrue(all(shot.fully_contains_members for shot in shots))

    def test_pole_geometry_remains_finite_and_bounded(self):
        result = build_group_shot([
            member("a", -45.0, 85.0),
            member("b", 45.0, 85.0),
        ])
        self.assertIsNotNone(result)
        self.assertTrue(math.isfinite(result.yaw))
        self.assertLessEqual(abs(result.pitch), math.pi / 2.0)

    def test_membership_is_deterministic_and_single_is_no_group(self):
        first = build_group_shot([
            member("z", 5.0),
            member("a", -5.0),
        ])
        second = build_group_shot([
            member("a", -5.0),
            member("z", 5.0),
        ])
        self.assertEqual(first, second)
        self.assertEqual(first.member_ids, ("a", "z"))
        self.assertIsNone(build_group_shot([member("only", 0.0)]))

    def test_padding_and_configuration_validation(self):
        result = build_group_shot([
            member("a", -35.0, extent=0.0),
            member("b", 35.0, extent=0.0),
        ], GroupShotConfig(
            padding_radians=math.radians(12.0),
            minimum_horizontal_fov=math.radians(80.0),
            maximum_horizontal_fov=math.radians(120.0),
        ))
        self.assertAlmostEqual(
            math.degrees(result.required_horizontal_fov), 94.0
        )
        with self.assertRaises(ValueError):
            GroupShotConfig(
                minimum_horizontal_fov=math.radians(120.0),
                maximum_horizontal_fov=math.radians(110.0),
            )


if __name__ == "__main__":
    unittest.main()
