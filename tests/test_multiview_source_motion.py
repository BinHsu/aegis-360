import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.so3 import rotate_ray


def axis_angle(axis, angle):
    scale = math.sin(angle / 2)
    return (axis[0] * scale, axis[1] * scale, axis[2] * scale, math.cos(angle / 2))


VIEWPORTS = [
    {"id": "front", "yawRadians": 0.0, "pitchRadians": 0.0, "horizontalFovRadians": 1.9},
    {"id": "right", "yawRadians": math.pi / 2, "pitchRadians": 0.0, "horizontalFovRadians": 1.9},
    {"id": "back", "yawRadians": math.pi, "pitchRadians": 0.0, "horizontalFovRadians": 1.9},
    {"id": "left", "yawRadians": -math.pi / 2, "pitchRadians": 0.0, "horizontalFovRadians": 1.9},
    {"id": "up", "yawRadians": 0.0, "pitchRadians": math.pi / 2, "horizontalFovRadians": 1.9},
    {"id": "down", "yawRadians": 0.0, "pitchRadians": -math.pi / 2, "horizontalFovRadians": 1.9},
]
RAYS = [
    (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
    (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, -1.0),
]


class MultiviewSourceMotionTests(unittest.TestCase):
    def test_cli_recovers_known_rig_path_and_emits_no_paths(self):
        rig_delta = axis_angle((0.0, 1.0, 0.0), math.radians(8))
        # current -> previous is the rig delta; make current rays by inverse.
        inverse = tuple(-value for value in rig_delta[:3]) + (rig_delta[3],)
        matches = []
        for index, previous in enumerate(RAYS):
            matches.append({
                "viewportId": VIEWPORTS[index]["id"],
                "previousRay": list(previous),
                "currentRay": list(rotate_ray(inverse, previous)),
            })
        source = {
            "schemaVersion": "aegis360.multiview-ray-matches.v1",
            "sourceId": "synthetic-rig",
            "configId": "six-view-110-v1",
            "proxy": {"width": 640, "height": 360, "sampleFps": 10},
            "viewports": VIEWPORTS,
            "pairs": [
                {"previousPtsSeconds": 0, "currentPtsSeconds": 0.1, "matches": matches},
                {"previousPtsSeconds": 0.1, "currentPtsSeconds": 0.2, "matches": matches},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory)
            input_path = private / "private-rays.json"
            output_path = private / "source-motion.json"
            input_path.write_text(json.dumps(source), encoding="utf-8")
            subprocess.run(
                [sys.executable, ROOT / "scripts/assemble_multiview_source_motion.py",
                 input_path, output_path],
                check=True,
            )
            result = json.loads(output_path.read_text(encoding="utf-8"))
            encoded = json.dumps(result)
            self.assertEqual(result["schema_version"], "aegis360.source-motion.v1")
            self.assertEqual(len(result["samples"]), 3)
            self.assertFalse(result["gaps"])
            self.assertNotIn(str(private), encoded)
            self.assertNotIn("private-rays.json", encoded)
            final = result["samples"][-1]["raw_orientation_xyzw"]
            expected = axis_angle((0.0, 1.0, 0.0), math.radians(16))
            self.assertAlmostEqual(abs(sum(a * b for a, b in zip(final, expected))), 1.0, places=7)
            self.assertGreater(result["samples"][1]["confidence"], 0.9)
            self.assertEqual(result["samples"][1]["face_coverage"], 1.0)

    def test_failed_pair_is_explicit_gap_and_held_invalid_sample(self):
        source = {
            "schemaVersion": "aegis360.multiview-ray-matches.v1",
            "sourceId": "synthetic-gap", "configId": "six-view-110-v1",
            "proxy": {"width": 640, "height": 360, "sampleFps": 10},
            "viewports": VIEWPORTS,
            "pairs": [{"previousPtsSeconds": 0, "currentPtsSeconds": 0.1, "matches": []}],
        }
        from aegis360.multiview_motion import assemble_source_motion
        result = assemble_source_motion(source)
        self.assertEqual(result["samples"][-1]["state"], "invalid")
        self.assertEqual(result["gaps"][0]["reason"], "insufficient_correspondences")


if __name__ == "__main__":
    unittest.main()
