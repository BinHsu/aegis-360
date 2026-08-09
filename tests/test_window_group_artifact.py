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


if __name__ == "__main__":
    unittest.main()
