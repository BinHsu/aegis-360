import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BuildRefreshLifecycleTraceTests(unittest.TestCase):
    def test_cli_joins_exact_timestamps_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            refresh = work / "refresh.json"
            tracking = work / "tracking.json"
            output = work / "lifecycle.json"
            refresh.write_text(json.dumps({
                "schema_version": "aegis360.detector-refresh-trace.v1",
                "source_id": "fixture",
                "events": [
                    self.row(1, "compatible_not_identity_verified"),
                    self.row(2, "no_compatible_detection"),
                    self.row(3, "compatible_not_identity_verified"),
                ],
            }))
            tracking.write_text(json.dumps({"observations": [
                self.observation(1, .9),
                self.observation(2, .8),
                self.observation(3, .7),
            ]}))
            command = [
                sys.executable,
                str(ROOT / "scripts/build_refresh_lifecycle_trace.py"),
                str(refresh), str(tracking), str(output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            document = json.loads(output.read_text())
            self.assertEqual(
                [row["phase"] for row in document["states"]],
                ["active", "missing_grace", "active"],
            )
            self.assertFalse(document["privacy"]["contains_source_path"])
            repeated = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)

    @staticmethod
    def row(timestamp, outcome):
        return {
            "timestamp": timestamp,
            "track_id": "person-1",
            "outcome": outcome,
            "editorial_persistence_allowed": False,
        }

    @staticmethod
    def observation(timestamp, confidence):
        return {
            "timestampSeconds": timestamp,
            "state": "tracked",
            "confidence": confidence,
        }


if __name__ == "__main__":
    unittest.main()
