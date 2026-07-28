import subprocess
import sys
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ModelManifestTests(unittest.TestCase):
    def test_repository_manifest_is_safe_and_missing_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([
                sys.executable,
                str(ROOT / "scripts" / "verify_model_manifest.py"),
                str(ROOT / "model-manifests" / "manifest.toml"),
                temporary,
            ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING apple_yolov3_tiny_fp16_v2", result.stderr)
        self.assertNotIn("http", result.stderr)
