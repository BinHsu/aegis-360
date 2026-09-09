import hashlib
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_sparse_story_forbidden_exec_sentinel.sh"
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, _validate_runtime_entrypoint, validate_asset_tree,
)

MARKER_BYTES = b"aegis-forbidden-exec-marker-v1\n"
ENTRYPOINT = "bin/aegis-forbidden-exec-sentinel"


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64",
                     "native sentinel is Darwin arm64 only")
class ForbiddenExecSentinelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name).resolve()
        cls.runtime_root = cls.base / "sentinel-runtime"
        result = subprocess.run([str(BUILD), str(cls.runtime_root)], check=True,
                                capture_output=True, text=True)
        cls.executable = Path(result.stdout.strip())

    @classmethod
    def tearDownClass(cls):
        for path in (cls.executable, cls.runtime_root / "bin", cls.runtime_root):
            if path.exists(): path.chmod(0o700)
        cls.temp.cleanup()

    def manifest(self):
        return _observe_asset_manifest_shape(root=self.runtime_root, asset_kind="runtime",
                                             entrypoint=ENTRYPOINT)

    def run_control(self, marker: Path):
        manifest = self.manifest()
        with validate_asset_tree(manifest=manifest, root=self.runtime_root) as proof:
            self.assertEqual(proof.manifest(), manifest)
            result = subprocess.run([str(self.executable),
                "--aegis-forbidden-exec-sentinel-v1", str(marker)], capture_output=True)
            self.assertEqual(proof.manifest(), manifest)
            return result

    def test_signed_thin_arm64_sealed_runtime_passes_retained_asset_validation(self):
        subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(self.executable)],
                       check=True)
        self.assertEqual(subprocess.check_output(["/usr/bin/lipo", "-archs",
            str(self.executable)], text=True).strip(), "arm64")
        self.assertEqual(stat.S_IMODE(self.executable.stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE((self.runtime_root / "bin").stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE(self.runtime_root.stat().st_mode), 0o555)
        fd = os.open(self.executable, os.O_RDONLY | os.O_CLOEXEC)
        try:
            _validate_runtime_entrypoint(fd)
        finally:
            os.close(fd)
        manifest = self.manifest()
        with validate_asset_tree(manifest=manifest, root=self.runtime_root) as proof:
            self.assertEqual(proof.manifest(), manifest)

    def test_unsandboxed_o_excl_marker_control_and_duplicate_failure(self):
        marker = self.base / "unique-marker"
        first = self.run_control(marker)
        self.assertEqual((first.returncode, first.stdout, first.stderr), (0, b"", b""))
        self.assertEqual(marker.read_bytes(), MARKER_BYTES)
        self.assertEqual(stat.S_IMODE(marker.stat().st_mode), 0o600)
        second = self.run_control(marker)
        self.assertEqual((second.returncode, second.stdout, second.stderr), (73, b"", b""))
        self.assertEqual(marker.read_bytes(), MARKER_BYTES)

    def test_malformed_argv_cannot_create_marker(self):
        for argv in ([], ["--wrong", str(self.base / "wrong")],
                     ["--aegis-forbidden-exec-sentinel-v1", "relative"]):
            marker = self.base / ("bad-" + str(len(argv)))
            result = subprocess.run([str(self.executable), *argv], capture_output=True)
            self.assertEqual((result.stdout, result.stderr), (b"", b""))
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_rebuild_refuses_existing_root_without_mutation(self):
        before = hashlib.sha256(self.executable.read_bytes()).hexdigest()
        result = subprocess.run([str(BUILD), str(self.runtime_root)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(hashlib.sha256(self.executable.read_bytes()).hexdigest(), before)

    def test_pre_mutation_parent_and_basename_validation_leave_no_output(self):
        noncanonical = self.base / "parent" / ".." / "bad-root"
        self.base.joinpath("parent").mkdir(mode=0o700)
        result = subprocess.run([str(BUILD), str(noncanonical)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.base / "bad-root").exists())
        unsafe = self.base / ".unsafe"
        result = subprocess.run([str(BUILD), str(unsafe)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(unsafe.exists())

    def test_post_exit_retained_proof_revalidation_detects_runtime_mutation(self):
        original_run = subprocess.run
        original_bytes = self.executable.read_bytes()

        def mutate_after_control(argv, *args, **kwargs):
            result = original_run(argv, *args, **kwargs)
            if argv and argv[0] == str(self.executable):
                self.runtime_root.chmod(0o700); (self.runtime_root / "bin").chmod(0o700)
                self.executable.chmod(0o700); self.executable.write_bytes(b"mutation")
                self.executable.chmod(0o555)
            return result

        try:
            with mock.patch.object(subprocess, "run", side_effect=mutate_after_control):
                with self.assertRaises(ValueError):
                    self.run_control(self.base / "post-exit-mutation-marker")
        finally:
            self.executable.chmod(0o700); self.executable.write_bytes(original_bytes)
            self.executable.chmod(0o555); (self.runtime_root / "bin").chmod(0o555)
            self.runtime_root.chmod(0o555)

    def test_identity_owned_failure_rollback_and_replacement_preservation(self):
        anchors = {
            "after-root": '[ -n "$root_identity" ] || { echo "could not retain output root identity" >&2; exit 70; }\n',
            "after-output-signing": '[ -n "$output_identity" ] || { echo "sentinel identity changed during signing" >&2; exit 70; }\n',
            "after-bin-seal": '/bin/chmod 0555 "${candidate_root}/bin"\n',
            "after-root-seal": '/bin/chmod 0555 "$candidate_root"\n',
        }

        def wrapper(stage, injection="exit 70\n"):
            wrapper_root = self.base / ("wrapper-" + stage)
            (wrapper_root / "scripts").mkdir(parents=True, exist_ok=True)
            (wrapper_root / "tools").mkdir(exist_ok=True)
            script = (wrapper_root / "scripts" / BUILD.name)
            anchor = anchors[stage]
            text = BUILD.read_text()
            self.assertEqual(text.count(anchor), 1)
            text = text.replace(anchor, anchor + injection, 1)
            script.write_text(text); script.chmod(0o755)
            (wrapper_root / "tools" / "sparse_story_forbidden_exec_sentinel.c").write_bytes(
                (ROOT / "tools" / "sparse_story_forbidden_exec_sentinel.c").read_bytes())
            return script

        for stage in ("after-root", "after-output-signing", "after-bin-seal", "after-root-seal"):
            failed = self.base / ("failed-" + stage)
            result = subprocess.run([str(wrapper(stage)), str(failed)], capture_output=True)
            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertFalse(failed.exists(), stage)
        replaced = self.base / "replaced-runtime"
        script = wrapper("after-root", "/bin/sleep 1\nexit 70\n")
        process = subprocess.Popen([str(script), str(replaced)], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        deadline = time.monotonic() + 2
        while not replaced.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(replaced.exists())
        replaced.rmdir(); replaced.mkdir(mode=0o700)
        marker = replaced / "replacement-preserved"
        marker.write_bytes(b"replacement")
        _, stderr = process.communicate(timeout=3)
        self.assertNotEqual(process.returncode, 0, stderr)
        self.assertEqual(marker.read_bytes(), b"replacement")

    def test_c_fault_cleanup_removes_marker_after_write_fsync_and_close_failure(self):
        source = ROOT / "tools" / "sparse_story_forbidden_exec_sentinel.c"
        for fault in ("AEGIS_SENTINEL_TEST_WRITE_FAILURE", "AEGIS_SENTINEL_TEST_FSYNC_FAILURE",
                      "AEGIS_SENTINEL_TEST_CLOSE_FAILURE"):
            executable = self.base / fault.lower()
            subprocess.run(["/usr/bin/xcrun", "clang", "-arch", "arm64",
                "-mmacosx-version-min=15.0", f"-D{fault}", str(source), "-o",
                str(executable)], check=True)
            marker = self.base / (fault + "-marker")
            result = subprocess.run([str(executable), "--aegis-forbidden-exec-sentinel-v1",
                str(marker)], capture_output=True)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (75, b"", b""))
            self.assertFalse(marker.exists())

    def test_c_race_fault_preserves_replacement_marker(self):
        source = ROOT / "tools" / "sparse_story_forbidden_exec_sentinel.c"
        executable = self.base / "race-fault"
        subprocess.run(["/usr/bin/xcrun", "clang", "-arch", "arm64",
            "-mmacosx-version-min=15.0", "-DAEGIS_SENTINEL_TEST_RACE_REPLACEMENT",
            str(source), "-o", str(executable)], check=True)
        marker = self.base / "race-marker"
        result = subprocess.run([str(executable), "--aegis-forbidden-exec-sentinel-v1",
            str(marker)], capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (75, b"", b""))
        self.assertEqual(marker.read_bytes(), b"replacement")
        self.assertTrue(marker.with_name(marker.name + ".retained").exists())

    def test_empty_sentinel_mutation_cannot_pass_retained_control(self):
        altered_root = self.base / "altered-runtime"
        result = subprocess.run([str(BUILD), str(altered_root)], check=True,
                                capture_output=True, text=True)
        executable = Path(result.stdout.strip())
        manifest = _observe_asset_manifest_shape(root=altered_root, asset_kind="runtime",
                                                 entrypoint=ENTRYPOINT)
        altered_root.chmod(0o700); (altered_root / "bin").chmod(0o700)
        executable.chmod(0o700); executable.write_bytes(b""); executable.chmod(0o555)
        with self.assertRaises(ValueError):
            validate_asset_tree(manifest=manifest, root=altered_root)
        marker = self.base / "mutation-marker"
        with self.assertRaises(OSError):
            subprocess.run([str(executable), "--aegis-forbidden-exec-sentinel-v1",
                            str(marker)], check=False)
        self.assertFalse(marker.exists())
        executable.chmod(0o700); (altered_root / "bin").chmod(0o700); altered_root.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
