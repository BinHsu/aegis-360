import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tests.test_continuous_onset_semantic import ContinuousOnsetSemanticTests


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_continuous_onset_semantic_review.py"


class ContinuousOnsetSemanticReviewRunnerTests(unittest.TestCase):
    def setUp(self):
        fixture = ContinuousOnsetSemanticTests()
        fixture.setUp()
        self.onset, self.samples = fixture.onset, fixture.samples
        self.grid, self.packet = fixture.grid, fixture.packet

    def _write_inputs(self, root, packet=None):
        values = {"onset": self.onset, "samples": self.samples,
                  "grid": self.grid, "packet": self.packet if packet is None else packet}
        paths = {}
        for name, value in values.items():
            path = root / f"{name}.json"
            path.write_text(json.dumps(value, sort_keys=True))
            paths[name] = path
        source = root / "source.webm"
        source.write_bytes(b"fixture")
        return source, paths

    def _executables(self, root):
        ffmpeg = root / "ffmpeg"
        ffmpeg.write_text(
            "#!/usr/bin/env python3\nimport pathlib,sys\npathlib.Path(sys.argv[-1]).write_bytes(b'png')\n")
        ffmpeg.chmod(0o755)
        adapter = root / "adapter.py"
        adapter.write_text(
            "import json,os,pathlib,sys\n"
            "work=pathlib.Path(os.environ['AEGIS_REVIEW_MEDIA_DIR'])\n"
            "index=json.loads(pathlib.Path(os.environ['AEGIS_REVIEW_MEDIA_INDEX']).read_text())\n"
            "assert index['schema_version']=='aegis360.transient-continuous-onset-review-media-index.v1'\n"
            "assert len(index['frames'])==int(sys.argv[2])\n"
            "assert all('/' not in row['filename'] for row in index['frames'])\n"
            "assert all((work/row['filename']).is_file() for row in index['frames'])\n"
            "pathlib.Path(sys.argv[1]).write_text(str(work))\n"
            "raise SystemExit(int(sys.argv[3]))\n")
        return ffmpeg, adapter

    def _run(self, root, *, packet=None, returncode=0):
        source, paths = self._write_inputs(root, packet)
        ffmpeg, adapter = self._executables(root)
        marker = root / "work-path.txt"
        environment = os.environ.copy()
        environment["PATH"] = f"{root}:{environment['PATH']}"
        command = [sys.executable, str(RUNNER), "--width", "80", "--height", "64",
                   str(source), str(paths["onset"]),
                   str(paths["samples"]), str(paths["grid"]), str(paths["packet"]),
                   "--", sys.executable, str(adapter), str(marker), "5", str(returncode)]
        return subprocess.run(command, capture_output=True, text=True, env=environment), marker

    def test_renders_exact_available_silent_composites_and_cleans(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, marker = self._run(Path(temporary))
            self.assertEqual(result.returncode, 0, result.stderr)
            work = Path(marker.read_text())
            self.assertFalse(work.exists())

    def test_explicit_unavailable_sample_is_skipped(self):
        packet = copy.deepcopy(self.packet)
        packet["samples"][-1].update(
            available=False, row_index=None, timestamp_seconds=None,
            acquisition_interval_pts_seconds=None, normalized_difference=None)
        # Exact validation requires an input-derived unavailable row, so trim the
        # acquisition/onset fixture consistently instead of accepting tampering.
        self.samples["samples"] = self.samples["samples"][:5]
        self.samples["window"]["duration_seconds"] = 1.0
        self.grid["window"]["duration_seconds"] = 1.0
        policy = self.onset["policy"]
        from aegis360.continuous_onset_candidates import build_continuous_onset_candidates
        from aegis360.continuous_onset_semantic_packet import build_continuous_onset_semantic_packet
        from tests.test_continuous_onset_semantic import digest
        self.onset = build_continuous_onset_candidates(
            self.samples, policy, samples_sha256=digest(self.samples),
            policy_sha256=digest(policy))
        packet = build_continuous_onset_semantic_packet(
            self.onset, self.samples, self.grid, candidate_id="continuous-onset:0000",
            onset_sha256=digest(self.onset), samples_sha256=digest(self.samples),
            grid_sha256=digest(self.grid))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, paths = self._write_inputs(root, packet)
            _, adapter = self._executables(root)
            marker = root / "work-path.txt"
            environment = os.environ.copy(); environment["PATH"] = f"{root}:{environment['PATH']}"
            result = subprocess.run([
                sys.executable, str(RUNNER), "--width", "80", "--height", "64",
                str(source), str(paths["onset"]),
                str(paths["samples"]), str(paths["grid"]), str(paths["packet"]),
                "--", sys.executable, str(adapter), str(marker), "4", "0"],
                capture_output=True, text=True,
                env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(Path(marker.read_text()).exists())

    def test_adapter_failure_code_propagates_after_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, marker = self._run(Path(temporary), returncode=7)
            self.assertEqual(result.returncode, 7, result.stderr)
            self.assertFalse(Path(marker.read_text()).exists())

    def test_malformed_lineage_fails_before_adapter(self):
        packet = copy.deepcopy(self.packet)
        packet["inputs"]["context_view_grid_sha256"] = "f" * 64
        with tempfile.TemporaryDirectory() as temporary:
            result, marker = self._run(Path(temporary), packet=packet)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_contract_has_no_shell_and_bounded_silent_render(self):
        source = RUNNER.read_text()
        self.assertNotIn("shell=True", source)
        self.assertIn('"-frames:v", "1"', source)
        self.assertIn('"-an"', source)
        self.assertIn("TemporaryDirectory", source)


if __name__ == "__main__":
    unittest.main()
