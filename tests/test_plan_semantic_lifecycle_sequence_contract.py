import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PlanSemanticLifecycleSequenceContractTests(unittest.TestCase):
    def test_cli_is_planning_only_path_free_atomic_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lifecycle = root / "lifecycle.json"
            tracking = root / "tracking.json"
            manifest = root / "manifest.json"
            output = root / "output"
            lifecycle.write_text(json.dumps({
                "schema_version": "aegis360.refresh-lifecycle-trace.v1",
                "source_id": "synthetic",
                "track_id": "bike-1",
                "states": [
                    {
                        "timestamp": timestamp,
                        "phase": "active",
                        "consecutive_missing": 0,
                        "editorial_persistence_allowed": False,
                        "identity_verified": False,
                    }
                    for timestamp in (0, 1, 2)
                ],
            }))
            tracking.write_text(json.dumps({
                "schemaVersion": "synthetic.v1",
                "trackId": "bike-1",
                "observations": [
                    {
                        "timestampSeconds": timestamp,
                        "state": "tracked",
                        "yawRadians": 1.0,
                        "pitchRadians": 0.0,
                    }
                    for timestamp in (0, 1, 2)
                ],
            }))
            manifest.write_text(json.dumps({
                "schema_version": "aegis360.semantic-plan-input.v1",
                "source_id": "synthetic",
                "start_seconds": 12,
                "duration_seconds": 3,
                "tracks": [{
                    "lifecycle_json": str(lifecycle),
                    "tracking_json": str(tracking),
                    "candidate_type": "bicycle",
                }],
            }))
            command = [
                sys.executable,
                str(ROOT / "scripts/plan_semantic_lifecycle_sequence.py"),
                str(manifest),
                str(ROOT / "config/greedy-group-context-v1.toml"),
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            trace = json.loads((output / "trace.json").read_text())
            gate = json.loads((output / "planning-gate.json").read_text())
            camera = json.loads((output / "camera-path.json").read_text())
            config = json.loads((output / "config.json").read_text())
            serialized = json.dumps({
                "trace": trace, "gate": gate, "camera": camera,
                "config": config,
            })
            self.assertNotIn(str(root), serialized)
            self.assertFalse(trace["input_contract"]["rendered"])
            self.assertFalse(gate["rendered"])
            self.assertTrue(gate["passed_pose_differentiation"])
            self.assertEqual(config["slice"]["start_seconds"], 12)
            self.assertEqual(config["render_contract"], "shot_static_v360_only")
            self.assertEqual(camera["schema_version"], "aegis360.camera-path.v1")
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    unittest.main()
