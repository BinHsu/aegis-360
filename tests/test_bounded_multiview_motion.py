import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.multiview_motion import assemble_source_motion


class BoundedMultiviewMotionTests(unittest.TestCase):
    def test_declared_bound_failure_becomes_explicit_gap(self):
        viewports = [
            {"id": name, "yawRadians": yaw, "pitchRadians": 0.0,
             "horizontalFovRadians": 1.9}
            for name, yaw in (
                ("front", 0.0), ("right", math.pi / 2),
                ("back", math.pi), ("left", -math.pi / 2))
        ]
        result = assemble_source_motion({
            "schemaVersion": "aegis360.multiview-ray-matches.v1",
            "sourceId": "bounded-fixture",
            "configId": "bounded-v1",
            "proxy": {"width": 640, "height": 360, "sampleFps": 2},
            "viewports": viewports,
            "pairs": [{
                "previousPtsSeconds": 0.0,
                "currentPtsSeconds": 0.5,
                "matches": [],
                "failureReason": "rotation_step_exceeds_configured_bound",
            }],
        })
        self.assertEqual(result["samples"][-1]["state"], "invalid")
        self.assertEqual(
            result["gaps"][-1]["reason"],
            "rotation_step_exceeds_configured_bound",
        )
        self.assertEqual(result["samples"][-1]["state"], "invalid")

    def test_declared_failure_cannot_hide_valid_matches(self):
        with self.assertRaisesRegex(ValueError, "failed pair"):
            assemble_source_motion({
                "schemaVersion": "aegis360.multiview-ray-matches.v1",
                "sourceId": "bounded-fixture",
                "configId": "bounded-v1",
                "proxy": {"width": 640, "height": 360, "sampleFps": 2},
                "viewports": [
                    {"id": str(index), "yawRadians": 0.0,
                     "pitchRadians": 0.0, "horizontalFovRadians": 1.9}
                    for index in range(4)
                ],
                "pairs": [{
                    "previousPtsSeconds": 0.0,
                    "currentPtsSeconds": 0.5,
                    "matches": [{
                        "viewportId": "0",
                        "previousRay": [1.0, 0.0, 0.0],
                        "currentRay": [1.0, 0.0, 0.0],
                    }],
                    "failureReason": "rotation_step_exceeds_configured_bound",
                }],
            })


if __name__ == "__main__":
    unittest.main()
