import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "run_auto_directed_slice.py"


def fixture():
    candidate = {
        "id": "front:human:0", "kind": "human", "confidence": 0.8,
        "yawRadians": 0.0, "pitchRadians": 0.0,
        "horizontalFovRadians": 1.0, "viewportId": "front",
        "boundingBox": {"x": .1, "y": .2, "width": .3, "height": .4},
    }
    return {
        "schemaVersion": 1,
        "provenance": {
            "adapterId": "synthetic", "adapterVersion": "1",
            "backendId": "fake-perception", "projectionStrategy": "viewports",
            "weightsSha256": None,
        },
        "frames": [
            {"sourceId": "job:e2e", "frameIndex": 0, "timestampSeconds": 10.0,
             "candidates": [candidate, {**candidate, "id": "right:human:0",
                                       "viewportId": "right", "yawRadians": .01}]},
            {"sourceId": "job:e2e", "frameIndex": 1, "timestampSeconds": 11.0,
             "candidates": [{**candidate, "id": "front:human:1", "yawRadians": .02}]},
        ],
    }


class AutoDirectedSliceE2ETests(unittest.TestCase):
    def test_fake_perception_to_complete_artifact_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "vision.json"
            evidence.write_text(json.dumps(fixture()), encoding="utf-8")
            source = root / "source.fake"
            source.write_bytes(b"not real media")
            adapter = root / "fake-renderer"
            adapter.write_text(
                "#!/bin/sh\nset -eu\n"
                "python3 -c 'import json,pathlib,sys; r=json.load(open(sys.argv[1]));"
                "[pathlib.Path(p).write_bytes((k+\" artifact\").encode()) "
                "for k,p in r[\"artifacts\"].items()]' \"$1\"\n",
                encoding="utf-8",
            )
            adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)
            bundle = root / "bundle"
            result = subprocess.run(
                [sys.executable, str(CLI), str(evidence), str(bundle),
                 "--source-id", "job:e2e", "--width", "1024", "--height", "512",
                 "--start", "10", "--duration", "1",
                 "--render-adapter", str(adapter), "--source-media", str(source)],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((bundle / "artifacts.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            for name in ("fixed", "auto", "debug"):
                self.assertTrue((bundle / manifest["artifacts"][name]["path"]).is_file())
            trace_text = (bundle / "trace.json").read_text()
            config_text = (bundle / "config.json").read_text()
            self.assertNotIn(str(source), trace_text + config_text)
            trace = json.loads(trace_text)
            self.assertEqual(trace["dedup"][0]["input_candidates"], 2)
            self.assertEqual(trace["dedup"][0]["output_candidates"], 1)
            camera = json.loads((bundle / "camera-path.json").read_text())
            self.assertEqual(len(camera["keyframes"]), 2)
            self.assertEqual(
                [item["timestamp"] for item in camera["keyframes"]], [0.0, 1.0]
            )

            repeated = subprocess.run(
                [sys.executable, str(CLI), str(evidence), str(bundle),
                 "--source-id", "job:e2e", "--width", "1024", "--height", "512",
                 "--start", "10", "--duration", "1"],
                text=True, capture_output=True,
            )
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)

    def test_planning_only_manifest_is_explicit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "vision.json"
            evidence.write_text(json.dumps(fixture()), encoding="utf-8")
            bundle = root / "bundle"
            subprocess.run(
                [sys.executable, str(CLI), str(evidence), str(bundle),
                 "--source-id", "job:e2e", "--width", "10", "--height", "5",
                 "--start", "10", "--duration", "1"],
                check=True,
            )
            manifest = json.loads((bundle / "artifacts.json").read_text())
            self.assertEqual(manifest["status"], "planned")
            self.assertFalse(manifest["artifacts"]["auto"]["exists"])


if __name__ == "__main__":
    unittest.main()
