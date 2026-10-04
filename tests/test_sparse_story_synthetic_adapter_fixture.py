import os
import select
import signal
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_probe_transcript import (  # noqa: E402
    OPERATIONS, _check_probe_row_values, parse_isolation_probe_transcript,
)
from aegis360.sparse_story_semantics import (  # noqa: E402
    select_failure_reason,
)
from aegis360.sparse_story_probe_sentinels import (  # noqa: E402
    _OutsideSentinelSnapshot, _ScratchProbeSnapshot,
)


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64",
                     "native adapter fixture is Darwin arm64 only")
class SyntheticAdapterFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name).resolve()
        cls.runtime = cls.base / "runtime"
        (cls.runtime / "bin").mkdir(parents=True)
        cls.executable = cls.runtime / "bin" / "aegis-synthetic-adapter"
        subprocess.run(["/usr/bin/xcrun", "--sdk", "macosx", "clang", "-std=c11",
            "-Os", "-Wall", "-Wextra", "-Werror", "-Wpedantic",
            "-fstack-protector-strong", "-arch", "arm64",
            "-mmacosx-version-min=15.0", str(ROOT / "tools" /
                "sparse_story_synthetic_adapter_fixture.c"), "-o", str(cls.executable)],
            check=True, capture_output=True)
        subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-",
                        "--timestamp=none", str(cls.executable)],
                       check=True, capture_output=True)
        cls.executable.chmod(0o555)
        (cls.runtime / "bin").chmod(0o555)
        cls.runtime.chmod(0o555)

    @classmethod
    def tearDownClass(cls):
        for path in (cls.executable, cls.runtime / "bin", cls.runtime):
            if path.exists(): path.chmod(0o700)
        cls.temp.cleanup()

    def test_same_retained_entrypoint_has_closed_probe_and_case_modes(self):
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
            case = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                                   "argv_literal", "--", ";$(touch should-not-run)",
                                   "* ' \" \\"], capture_output=True, timeout=5)
            self.assertEqual((case.returncode, case.stderr), (0, b""))
            self.assertIsNone(select_failure_reason(missing_anchor=False,
                invocation_failed=False, raw_output=case.stdout))
            for suffix in ([], ["--aegis-synthetic-case", "bad", "--"],
                           ["--aegis-isolation-probe"],
                           ["--aegis-synthetic-case", "argv_literal", "--", "extra"],
                           ["--aegis-synthetic-case", "argv_literal", "--"]):
                wrong = subprocess.run([str(self.executable), *suffix],
                                       capture_output=True, timeout=5)
                self.assertEqual((wrong.returncode, wrong.stdout, wrong.stderr),
                                 (64, b"", b""))
            self.assertEqual(proof.manifest(), manifest)

    def test_binary_bundle_prefix_is_checked_without_text_conversion(self):
        with tempfile.TemporaryDirectory() as directory:
            leaf = Path(directory) / "binary.png"
            prefix = b"\x89PNG\r\n\x1a\n\x00\xff"
            leaf.write_bytes(prefix + b"more payload")
            def run(expected):
                return subprocess.run([str(self.executable),
                    "--aegis-synthetic-case", "bundle_read_allowed", "--",
                    str(leaf), expected], capture_output=True, timeout=5)
            self.assertEqual(run("hex:" + prefix.hex()).returncode, 0)
            self.assertEqual(run("hex:" + (prefix[:-1] + b"\x00").hex()).returncode, 65)
            self.assertEqual(run("hex:zz").returncode, 64)

    def test_stdout_failure_cases_have_distinct_raw_bytes(self):
        expected = {
            "stdout_empty": (b"", "malformed_json"),
            "stdout_invalid_utf8": (b"\xff", "malformed_json"),
            "stdout_duplicate_key": (b'{"status":"abstain","status":"abstain"}', "malformed_json"),
            "stdout_nan": (b'{"status":NaN}', "malformed_json"),
            "stdout_trailing_bytes": (b"{}{}", "malformed_json"),
            "stdout_forbidden_field": (b'{"source_time":0}', "forbidden_field"),
            "stdout_extra_field": (b'{"unexpected":true}', "forbidden_field"),
        }
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
            for case_id, (raw, reason) in expected.items():
                with self.subTest(case_id=case_id):
                    case = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                                           case_id, "--"], capture_output=True, timeout=5)
                    self.assertEqual((case.returncode, case.stdout, case.stderr),
                                     (0, raw, b""))
                    self.assertEqual(select_failure_reason(missing_anchor=False,
                        invocation_failed=False, raw_output=case.stdout), reason)
            self.assertEqual(proof.manifest(), manifest)

    def test_environment_descriptors_and_cwd_detect_violations(self):
        home = self.base / "private-home"
        tmpdir = self.base / "private-tmp"
        home.mkdir()
        tmpdir.mkdir()
        environment = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1",
                       "HOME": str(home), "TMPDIR": str(tmpdir)}
        def run(case_id, *args, env=None, cwd=None, pass_fds=()):
            return subprocess.run([str(self.executable), "--aegis-synthetic-case",
                case_id, "--", *args], env=env, cwd=cwd, pass_fds=pass_fds,
                capture_output=True, timeout=5)
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
            for case_id, args in (("environment_exact", (str(home), str(tmpdir))),
                                  ("fd_hygiene", ()), ("cwd_identity", (str(self.base),))):
                with self.subTest(case_id=case_id):
                    result = run(case_id, *args, env=environment, cwd=self.base)
                    self.assertEqual((result.returncode, result.stderr), (0, b""))
                    self.assertIsNone(select_failure_reason(missing_anchor=False,
                        invocation_failed=False, raw_output=result.stdout))
            contaminated = dict(environment, PATH="/usr/bin")
            self.assertEqual(run("environment_exact", str(home), str(tmpdir),
                                 env=contaminated, cwd=self.base).returncode, 65)
            missing = {key: value for key, value in environment.items() if key != "NO_COLOR"}
            self.assertEqual(run("environment_exact", str(home), str(tmpdir),
                                 env=missing, cwd=self.base).returncode, 65)
            wrong_home = dict(environment, HOME=str(tmpdir))
            self.assertEqual(run("environment_exact", str(home), str(tmpdir),
                                 env=wrong_home, cwd=self.base).returncode, 65)
            self.assertEqual(run("cwd_identity", str(tmpdir), env=environment,
                                 cwd=self.base).returncode, 65)
            reader, writer = os.pipe()
            try:
                self.assertEqual(run("fd_hygiene", env=environment, cwd=self.base,
                                     pass_fds=(reader,)).returncode, 65)
            finally:
                os.close(reader)
                os.close(writer)
            self.assertEqual(proof.manifest(), manifest)

    def test_stdout_ceiling_stderr_and_termination_cases(self):
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        def run(case_id):
            return subprocess.run([str(self.executable), "--aegis-synthetic-case",
                                   case_id, "--"], capture_output=True, timeout=5)
        with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
            for case_id, size in (("stdout_limit_minus_one", 65535),
                                  ("stdout_limit_exact", 65536),
                                  ("stdout_limit_plus_one", 65537)):
                with self.subTest(case_id=case_id):
                    result = run(case_id)
                    self.assertEqual((result.returncode, len(result.stdout), result.stderr),
                                     (0, size, b""))
                    self.assertIsNone(select_failure_reason(missing_anchor=False,
                        invocation_failed=False, raw_output=result.stdout))
            stderr_case = run("stderr_nonempty")
            self.assertEqual((stderr_case.returncode, stderr_case.stderr),
                             (0, b"synthetic-stderr-v1\n"))
            self.assertIsNone(select_failure_reason(missing_anchor=False,
                invocation_failed=False, raw_output=stderr_case.stdout))
            nonzero = run("nonzero_exit")
            self.assertEqual((nonzero.returncode, nonzero.stderr), (23, b""))
            self.assertIsNone(select_failure_reason(missing_anchor=False,
                invocation_failed=False, raw_output=nonzero.stdout))
            signaled = run("signal_exit")
            self.assertEqual((signaled.returncode, signaled.stdout, signaled.stderr),
                             (-15, b"", b""))
            with self.assertRaises(subprocess.TimeoutExpired):
                subprocess.run([str(self.executable), "--aegis-synthetic-case",
                                "wall_timeout", "--"], capture_output=True, timeout=0.2)
            pressure = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                "concurrent_pipe_pressure", "--"], input=b"x" * 60000,
                capture_output=True, timeout=5)
            self.assertEqual((pressure.returncode, len(pressure.stdout),
                              len(pressure.stderr)), (0, 60000, 0))
            self.assertIsNone(select_failure_reason(missing_anchor=False,
                invocation_failed=False, raw_output=pressure.stdout))
            wrong_input = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                "concurrent_pipe_pressure", "--"], input=b"x" * 59999 + b"y",
                capture_output=True, timeout=5)
            self.assertEqual((wrong_input.returncode, wrong_input.stderr), (65, b""))
            stubborn = subprocess.Popen([str(self.executable), "--aegis-synthetic-case",
                "term_ignore_kill", "--"], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, start_new_session=True)
            try:
                readable, _, _ = select.select([stubborn.stdout], [], [], 5)
                self.assertTrue(readable)
                self.assertEqual(os.read(stubborn.stdout.fileno(), 6), b"ready\n")
                os.kill(stubborn.pid, signal.SIGTERM)
                with self.assertRaises(subprocess.TimeoutExpired):
                    stubborn.wait(timeout=0.2)
                os.kill(stubborn.pid, signal.SIGKILL)
                self.assertEqual(stubborn.wait(timeout=5), -signal.SIGKILL)
            finally:
                if stubborn.poll() is None:
                    stubborn.kill()
                    stubborn.wait(timeout=5)
                stubborn.stdout.close()
                stubborn.stderr.close()
            self.assertEqual(proof.manifest(), manifest)

    def test_file_cases_distinguish_existing_reads_and_real_writes(self):
        with tempfile.TemporaryDirectory(dir=self.base) as temporary:
            root = Path(temporary)
            manifest = _observe_asset_manifest_shape(root=self.runtime,
                asset_kind="runtime", entrypoint="bin/aegis-synthetic-adapter")
            def run(case_id, *args):
                return subprocess.run([str(self.executable), "--aegis-synthetic-case",
                    case_id, "--", *map(str, args)], capture_output=True, timeout=5)
            with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
                for case_id in ("bundle_read_allowed", "model_read_allowed",
                                "prompt_read_allowed"):
                    path = root / case_id
                    path.write_text(case_id)
                    result = run(case_id, path, case_id)
                    self.assertEqual((result.returncode, result.stderr), (0, b""))
                    self.assertIsNone(select_failure_reason(missing_anchor=False,
                        invocation_failed=False, raw_output=result.stdout))
                    self.assertEqual(run(case_id, path, "wrong").returncode, 65)
                for case_id in ("repository_read_denied", "protocol_read_denied",
                                "neighbor_packet_read_denied", "result_read_denied"):
                    path = root / case_id
                    path.write_text(case_id)
                    result = run(case_id, path)
                    self.assertEqual((result.returncode, result.stdout, result.stderr),
                                     (65, b"", b""))
                    self.assertEqual(path.read_text(), case_id)
                    self.assertEqual(run(case_id, root / "missing").returncode, 65)
                scratch = root / "scratch-write"
                allowed = run("scratch_write_allowed", scratch)
                self.assertEqual((allowed.returncode, allowed.stderr), (0, b""))
                self.assertEqual(scratch.read_bytes(), b"synthetic-scratch-write-v1")
                self.assertEqual(run("scratch_write_allowed", scratch).returncode, 65)
                outside = root / "outside-write"
                denied = run("outside_write_denied", outside)
                self.assertEqual((denied.returncode, denied.stdout, denied.stderr),
                                 (65, b"", b""))
                self.assertTrue(outside.is_file())
                self.assertEqual(proof.manifest(), manifest)

    def test_network_denial_cases_require_real_listeners(self):
        with tempfile.TemporaryDirectory(dir=self.base) as temporary:
            root = Path(temporary)
            manifest = _observe_asset_manifest_shape(root=self.runtime,
                asset_kind="runtime", entrypoint="bin/aegis-synthetic-adapter")
            with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
                for case_id, family, address in (
                    ("network_ipv4_denied", socket.AF_INET, "127.0.0.1"),
                    ("network_ipv6_denied", socket.AF_INET6, "::1"),
                    ("unix_socket_denied", socket.AF_UNIX, str(root / "live.sock"))):
                    with self.subTest(case_id=case_id), socket.socket(family,
                            socket.SOCK_STREAM) as listener:
                        try:
                            listener.bind((address, 0) if family != socket.AF_UNIX else address)
                        except PermissionError as error:
                            self.skipTest(f"host policy denies local listener bind: {error.errno}")
                        listener.listen(1)
                        target = address if family == socket.AF_UNIX else str(listener.getsockname()[1])
                        case = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                            case_id, "--", target], capture_output=True, timeout=5)
                        self.assertEqual((case.returncode, case.stdout, case.stderr),
                                         (65, b"", b""))
                self.assertEqual(proof.manifest(), manifest)

    def test_grandchild_denial_case_creates_marker_when_unconfined(self):
        with tempfile.TemporaryDirectory(dir=self.base) as temporary:
            marker = Path(temporary) / "grandchild-marker"
            manifest = _observe_asset_manifest_shape(root=self.runtime,
                asset_kind="runtime", entrypoint="bin/aegis-synthetic-adapter")
            with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
                result = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                    "grandchild_containment", "--", str(marker)],
                    capture_output=True, timeout=5)
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (65, b"", b""))
                self.assertEqual(marker.read_bytes(), b"grandchild-created-v1")
                self.assertEqual(proof.manifest(), manifest)

    def test_raw_probe_rows_are_exact_order_without_claiming_confinement(self):
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        with tempfile.TemporaryDirectory(dir=self.base) as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir(mode=0o700)
            scratch_root = root / "scratch-root"
            scratch_root.mkdir(mode=0o700)
            home, tmpdir = scratch_root / "home", scratch_root / "tmp"
            home.mkdir(mode=0o700)
            tmpdir.mkdir(mode=0o700)
            paths = [root / name for name in ("bundle", "model", "prompt", "scratch",
                "repo", "protocol", "neighbor", "result", "outside-create",
                "outside-existing", "rename-source", "rename-dest", "fork-marker")]
            paths[3] = scratch_root / "scratch-write"
            paths[8] = outside / "outside-create"
            paths[9] = outside / "outside-existing"
            paths[10] = scratch_root / "rename-source"
            paths[11] = outside / "rename-dest"
            paths[12] = scratch_root / "fork-marker"
            for path in paths[:3]: path.write_bytes(path.name.encode())
            paths[9].write_bytes(b"outside-existing-sentinel-v1")
            paths[9].chmod(0o600)
            paths[10].write_bytes(b"rename-source-v1")
            paths[10].chmod(0o600)
            argv = [str(self.executable), "--aegis-isolation-probe",
                *map(str, paths[:13]), "0", "0", str(root / "absent.sock"),
                str(root / "absent-executable"), str(scratch_root / "exec-marker")]
            self.assertEqual(len(argv), 20)
            with (validate_asset_tree(manifest=manifest, root=self.runtime) as proof,
                  _OutsideSentinelSnapshot(outside) as sentinels,
                  _ScratchProbeSnapshot(scratch_root, home, tmpdir) as scratch):
                result = subprocess.run(argv, capture_output=True, timeout=5)
                self.assertEqual((result.returncode, result.stderr), (0, b""))
                rows = parse_isolation_probe_transcript(result.stdout)
                self.assertEqual(tuple(row.operation for row in rows), OPERATIONS)
                self.assertEqual(rows[0].data, b"bundle")
                self.assertEqual(rows[1].data, b"model")
                self.assertEqual(rows[2].data, b"prompt")
                primitive = _check_probe_row_values(rows, bundle_prefix=b"bundle",
                    model_prefix=b"model", prompt_prefix=b"prompt")
                self.assertTrue(all(primitive[key] for key in (
                    "allowed_bundle_read", "allowed_model_read", "allowed_prompt_read",
                    "allowed_scratch_write")))
                self.assertFalse(primitive["denied_repository_read"])
                self.assertFalse(primitive["denied_outside_write"])
                with self.assertRaises(ValueError): sentinels.revalidate()
                with self.assertRaises(ValueError): scratch.postvalidate()
                self.assertEqual(proof.manifest(), manifest)


if __name__ == "__main__": unittest.main()
