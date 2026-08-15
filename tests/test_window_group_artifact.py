import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.window_group_artifact import build_window_group_proposal_artifact


def person(identifier, yaw, pitch=-25):
    return {
        "candidate_id": identifier, "class_name": "person",
        "yaw_radians": math.radians(yaw), "pitch_radians": math.radians(pitch),
        "horizontal_extent_radians": math.radians(15),
    }


class WindowGroupArtifactTests(unittest.TestCase):
    def test_geometry_precedes_context_and_remains_path_free(self):
        spherical = {
            "schema_version": "aegis360.semantic-spherical-dedup.v1",
            "samples": [
                {"timestamp_seconds": 10 + i * .25, "clusters": (
                    [person(f"left:{i}", 48), person(f"right:{i}", 61)]
                    if i % 2 == 0 else [person(f"right:{i}", 61)]
                )}
                for i in range(4)
            ],
        }
        faces = {
            "schemaVersion": 1,
            "frames": [
                {"timestampSeconds": 10 + i * .25, "candidates": [{
                    "kind": "face_rectangle", "yawRadians": math.radians(61),
                    "pitchRadians": math.radians(-6),
                }]}
                for i in range(4)
            ],
        }
        result = build_window_group_proposal_artifact(
            spherical, faces, source_id="fixture", window_id="t10",
            start_seconds=10, duration_seconds=1,
        )
        self.assertEqual(result["geometry"]["observation_ratio"], .5)
        self.assertLess(math.degrees(result["geometry"]["pitch"]), -19)
        self.assertGreater(math.degrees(result["geometry"]["pitch"]), -21)
        self.assertEqual(
            result["composition_policy"]["maximum_face_pitch_correction_degrees"], 5,
        )
        self.assertIsNone(result["selection"]["selected_candidate_id"])
        group = next(c for c in result["candidates"] if c["candidate_type"] == "group")
        self.assertEqual(len(group["member_candidate_ids"]), 2)
        self.assertFalse(result["privacy"]["contains_source_path"])

    def test_insufficient_group_observations_fail(self):
        spherical = {
            "schema_version": "aegis360.semantic-spherical-dedup.v1",
            "samples": [
                {"timestamp_seconds": i, "clusters": [person(str(i), 0)]}
                for i in range(2)
            ],
        }
        faces = {"schemaVersion": 1, "frames": []}
        with self.assertRaisesRegex(ValueError, "floor"):
            build_window_group_proposal_artifact(
                spherical, faces, source_id="fixture", window_id="w",
                start_seconds=0, duration_seconds=2,
            )

    def test_v2_complete_vertical_bounds_replace_face_guard(self):
        spherical = {
            "schema_version": "aegis360.semantic-spherical-dedup.v2",
            "samples": [{"timestamp_seconds": i * .25, "clusters": [
                {**person(f"a:{i}", 0), "pitch_min_radians": math.radians(-45), "pitch_max_radians": math.radians(5)},
                {**person(f"b:{i}", 10), "pitch_min_radians": math.radians(-40), "pitch_max_radians": math.radians(10)},
            ]} for i in range(4)],
        }
        faces = {"schemaVersion": 1, "frames": [{
            "timestampSeconds": i * .25,
            "candidates": [{"kind": "face_rectangle", "yawRadians": 0, "pitchRadians": math.radians(30)}],
        } for i in range(4)]}
        result = build_window_group_proposal_artifact(
            spherical, faces, source_id="fixture", window_id="v2",
            start_seconds=0, duration_seconds=1,
            use_vertical_bounds_midpoint=True,
        )
        self.assertAlmostEqual(math.degrees(result["geometry"]["pitch"]), -17.5)
        self.assertEqual(
            result["composition_policy"]["status"],
            "experimental_complete_vertical_bounds_union_midpoint",
        )
        baseline = build_window_group_proposal_artifact(
            spherical, faces, source_id="fixture", window_id="v2-default",
            start_seconds=0, duration_seconds=1,
        )
        self.assertAlmostEqual(
            math.degrees(baseline["geometry"]["pitch"]), -20.0837712492,
            places=6,
        )
        self.assertGreater(
            result["geometry"]["pitch"], baseline["geometry"]["pitch"],
        )
        self.assertEqual(
            baseline["composition_policy"]["status"],
            "tunable_poc_guard_not_validated_default",
        )


if __name__ == "__main__":
    unittest.main()
