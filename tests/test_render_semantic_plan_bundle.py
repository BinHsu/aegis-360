import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "render_semantic_plan_bundle.py"


class RenderSemanticPlanBundleTests(unittest.TestCase):
    def make_plan(self, root: Path, *, passed: bool = True) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        plan = root / "plan"
        plan.mkdir()
        (plan / "trace.json").write_text("{}\n", encoding="utf-8")
        (plan / "camera-path.json").write_text("{}\n", encoding="utf-8")
        (plan / "config.json").write_text(json.dumps({
            "schema_version": "aegis360.semantic-plan-config.v1",
            "slice": {"start_seconds": 2.0, "duration_seconds": 4.0},
            "versioned_greedy_config": {
                "camera": {"framing_safety": {"minimum_horizontal_fov_degrees": 110}}
            },
            "render_contract": "shot_static_v360_only",
        }), encoding="utf-8")
        (plan / "planning-gate.json").write_text(json.dumps({
            "schema_version": "aegis360.semantic-planning-gate.v1",
            "passed_pose_differentiation": passed,
        }), encoding="utf-8")
        return plan

    def make_adapter(self, root: Path, *, succeed: bool = True) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        adapter = root / "adapter"
        body = (
            "#!/bin/sh\nset -eu\n"
            "python3 -c 'import json,pathlib,sys; r=json.load(open(sys.argv[1]));"
            "[pathlib.Path(p).write_bytes(k.encode()) for k,p in r[\"artifacts\"].items()]' \"$1\"\n"
            if succeed else "#!/bin/sh\nexit 7\n"
        )
        adapter.write_text(body, encoding="utf-8")
        adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)
        return adapter

    def test_builds_complete_atomic_path_free_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = self.make_plan(root)
            source = root / "source.webm"
            source.write_bytes(b"media")
            output = root / "bundle"
            result = subprocess.run([
                sys.executable, str(CLI), str(plan), str(source), str(output),
                "--render-adapter", str(self.make_adapter(root)),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest_text = (output / "artifacts.json").read_text()
            manifest = json.loads(manifest_text)
            self.assertEqual(manifest["status"], "complete")
            self.assertNotIn(str(source), manifest_text)
            for name in ("fixed-forward.mp4", "auto-directed.mp4", "debug-overlay.mp4"):
                self.assertTrue((output / name).is_file())
            self.assertEqual(json.loads((output / "config.json").read_text())["slice"]["duration_seconds"], 4.0)

            repeated = subprocess.run([
                sys.executable, str(CLI), str(plan), str(source), str(output),
                "--render-adapter", str(self.make_adapter(root)),
            ], capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)

    def test_rejects_failed_gate_and_cleans_failed_staging(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.webm"
            source.write_bytes(b"media")
            rejected = subprocess.run([
                sys.executable, str(CLI), str(self.make_plan(root, passed=False)),
                str(source), str(root / "rejected"),
                "--render-adapter", str(self.make_adapter(root)),
            ], capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("did not pass", rejected.stderr)

            failure_root = root / "failure"
            plan = self.make_plan(failure_root)
            output = failure_root / "bundle"
            failed = subprocess.run([
                sys.executable, str(CLI), str(plan), str(source), str(output),
                "--render-adapter", str(self.make_adapter(failure_root, succeed=False)),
            ], capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(output.exists())
            self.assertEqual(list(failure_root.glob(".bundle.*")), [])


if __name__ == "__main__":
    unittest.main()
