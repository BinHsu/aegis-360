import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from assemble_vision_tile_evidence import assemble


def evidence(width=640, timestamps=(0.0, 0.04)):
    observations = []
    for index, timestamp in enumerate(timestamps):
        observations.append({
            "frameIndex": index,
            "timestampSeconds": timestamp,
            "state": "reference" if index == 0 else "measured",
            "homographyRowMajor": (
                None if index == 0
                else [1.0, 0.0, 2.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
            ),
            "error": None,
        })
    return {
        "frameWidth": width,
        "frameHeight": 360,
        "observations": observations,
    }


class VisionTileEvidenceArtifactTests(unittest.TestCase):
    def manifest(self):
        return {
            "sourceId": "synthetic-parent",
            "viewportId": "front",
            "parentWidth": 1280,
            "parentHeight": 720,
            "tiles": [
                {
                    "id": "r0c0", "x": 0, "y": 0,
                    "width": 640, "height": 360,
                    "evidenceFile": "private-a.json",
                },
                {
                    "id": "r0c1", "x": 640, "y": 0,
                    "width": 640, "height": 360,
                    "evidenceFile": "private-b.json",
                },
            ],
        }

    def test_output_is_path_free_and_preserves_independent_sequences(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "private-a.json").write_text(json.dumps(evidence()))
            (root / "private-b.json").write_text(json.dumps(evidence()))
            result = assemble(self.manifest(), root)
        encoded = json.dumps(result)
        self.assertEqual(
            result["schema_version"], "aegis360.vision-tile-evidence.v1"
        )
        self.assertEqual(len(result["tile_sequences"]), 2)
        self.assertNotIn("private-a", encoded)
        self.assertNotIn("evidenceFile", encoded)
        self.assertNotIn(str(root), encoded)
        self.assertFalse(result["privacy"]["contains_source_paths"])

    def test_timestamp_disagreement_and_bad_extent_fail_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "private-a.json").write_text(json.dumps(evidence()))
            (root / "private-b.json").write_text(json.dumps(
                evidence(timestamps=(0.0, 0.08))
            ))
            with self.assertRaisesRegex(ValueError, "timestamps"):
                assemble(self.manifest(), root)
            manifest = self.manifest()
            manifest["tiles"][1]["x"] = 1000
            with self.assertRaisesRegex(ValueError, "inside"):
                assemble(manifest, root)

    def test_backend_error_cannot_leak_a_path(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            unsafe = evidence()
            unsafe["observations"][1] = {
                "frameIndex": 1,
                "timestampSeconds": 0.04,
                "state": "error",
                "homographyRowMajor": None,
                "error": "/private/tmp/frame.png",
            }
            (root / "private-a.json").write_text(json.dumps(unsafe))
            (root / "private-b.json").write_text(json.dumps(unsafe))
            result = assemble(self.manifest(), root)
        self.assertEqual(
            result["tile_sequences"][0]["observations"][1]["failure_reason"],
            "backend_error",
        )
        self.assertNotIn("/private/", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
