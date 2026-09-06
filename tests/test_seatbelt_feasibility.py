import importlib.util
import json
import platform
import os
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_seatbelt_feasibility.py"
SPEC = importlib.util.spec_from_file_location("seatbelt_feasibility", SCRIPT)
seatbelt = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(seatbelt)


class SeatbeltFeasibilityTests(unittest.TestCase):
    def test_candidate_policy_is_canonical_sorted_and_default_deny(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            runtime = base / "runtime"
            forbidden = base / "forbidden"
            roots = {name: base / name for name in
                     ("bundle", "model", "prompt", "scratch")}
            for root in (runtime, forbidden, *roots.values()):
                root.mkdir()
            executable = runtime / "probe"
            executable.touch()
            forbidden_executable = forbidden / "forbidden-probe"
            forbidden_executable.touch()
            manifest = seatbelt.build_seatbelt_backend_manifest_shape(
                os_build="25F84", architecture="arm64",
                backend_executable_sha256="a" * 64, backend_executable_size=123,
                launcher_runtime_manifest_sha256="b" * 64)
            dynamic = {"runtime_root": str(runtime),
                "runtime_executable": str(executable),
                "forbidden_executable": str(forbidden_executable),
                "bundle_root": str(roots["bundle"]),
                "model_root": str(roots["model"]),
                "prompt_root": str(roots["prompt"]),
                "scratch_root": str(roots["scratch"])}
            first = seatbelt.render_seatbelt_policy_input_shape_bytes(
                backend_manifest=manifest, dynamic_roots=dynamic)
            second = seatbelt.render_seatbelt_policy_input_shape_bytes(
                backend_manifest=manifest,
                dynamic_roots=dict(reversed(list(dynamic.items()))))
            self.assertEqual(first, second)
            self.assertTrue(first.startswith(b"(version 1)\n(deny default)\n"))
            self.assertNotIn(b"(allow default)", first)
            self.assertIn(b'(allow file-read-metadata (literal "/tmp"))', first)
            self.assertIn(b'(allow file-read-data (literal "/"))', first)
            self.assertNotIn(b'(subpath "/tmp")', first)
            self.assertNotIn(b'(subpath "/")', first)
            self.assertLess(first.index(str(roots["bundle"]).encode()),
                            first.index(str(roots["model"]).encode()))
            forbidden_literal = (b"(literal " + json.dumps(
                str(forbidden_executable.resolve())).encode("ascii") + b")")
            self.assertIn(forbidden_literal, first)
            process_exec_lines = [line for line in first.splitlines()
                                  if b"process-exec" in line]
            self.assertEqual(len(process_exec_lines), 1)
            self.assertIn(str(executable.resolve()).encode(), process_exec_lines[0])
            self.assertNotIn(str(forbidden_executable.resolve()).encode(),
                             process_exec_lines[0])

    def test_probe_parser_is_binary_exact_and_closed(self):
        parsed = seatbelt.parse_probe_stdout(b"read\t3\t0\t616263\n")
        self.assertEqual(parsed["read"]["data"], b"abc")
        self.assertEqual(parsed["read"]["value"], 3)
        with self.assertRaisesRegex(ValueError, "duplicated"):
            seatbelt.parse_probe_stdout(b"read\t1\t0\t61\nread\t1\t0\t61\n")
        with self.assertRaises(ValueError):
            seatbelt.parse_probe_stdout(b"read\tbad\t0\t\n")

    def test_operation_set_is_exact_and_socket_stages_are_distinct(self):
        expected = {
            "bundle_read", "model_read", "prompt_read", "scratch_write",
            "repository_read", "protocol_read", "neighbor_read", "result_read",
            "outside_create", "outside_overwrite", "outside_truncate",
            "outside_rename", "outside_unlink", "process_fork", "ipv4_socket",
            "ipv4_connect", "ipv6_socket", "ipv6_connect", "unix_socket",
            "unix_connect", "forbidden_exec"}
        self.assertEqual(seatbelt.EXPECTED_OPERATIONS, expected)
        source = (ROOT / "tools" / "seatbelt_feasibility_probe.c").read_text()
        for name in expected:
            self.assertIn(f'"{name}"', source)

    def test_snapshot_is_nofollow_typed_owned_and_content_exact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            leaf = root / "leaf"
            leaf.write_bytes(b"content")
            (root / "link").symlink_to("leaf")
            snapshot = seatbelt._safe_snapshot(root)
            self.assertEqual(snapshot["leaf"][0], stat.S_IFREG)
            self.assertEqual(snapshot["leaf"][1], os.getuid())
            self.assertEqual(snapshot["leaf"][5], len(b"content"))
            self.assertEqual(snapshot["link"][0], stat.S_IFLNK)
            self.assertEqual(snapshot["link"][6], "")

    def test_compile_timeout_is_normalized_at_compile_stage(self):
        def timeout(_):
            raise subprocess.TimeoutExpired(["clang"], 15)

        with mock.patch.object(seatbelt.platform, "system", return_value="Darwin"), \
             mock.patch.object(seatbelt.platform, "machine", return_value="arm64"), \
             mock.patch.object(seatbelt, "_compile_fixture", side_effect=timeout):
            classification, diagnostic = seatbelt.run()
        self.assertEqual(classification, "not_feasible")
        self.assertEqual(diagnostic, {"reason": "compile_timeout", "stage": "compile"})

    def test_failure_diagnostic_redacts_exception_text_and_path(self):
        secret = "/private/secret/asset"
        with mock.patch.object(seatbelt.platform, "system", return_value="Darwin"), \
             mock.patch.object(seatbelt.platform, "machine", return_value="arm64"), \
             mock.patch.object(seatbelt.tempfile, "TemporaryDirectory",
                               side_effect=OSError(secret)):
            classification, diagnostic = seatbelt.run()
        self.assertEqual(classification, "not_feasible")
        self.assertEqual(diagnostic, {"reason": "operating_system_error", "stage": "setup"})
        self.assertNotIn(secret, repr(diagnostic))

    def test_launch_parse_and_filesystem_failures_keep_closed_stage(self):
        for stage, failure, reason in (
                ("launch", RuntimeError("/secret/launch"), "internal_error"),
                ("parse", ValueError("/secret/parse"), "internal_error"),
                ("filesystem", OSError("/secret/filesystem"), "operating_system_error")):
            def fail(progress, selected=stage, error=failure):
                progress["stage"] = selected
                raise error

            with self.subTest(stage=stage), mock.patch.object(
                    seatbelt, "_run_inner", side_effect=fail):
                classification, diagnostic = seatbelt.run()
            self.assertEqual(classification, "not_feasible")
            self.assertEqual(diagnostic, {"reason": reason, "stage": stage})
            self.assertNotIn("/secret", repr(diagnostic))

    def test_listener_context_is_closed_when_later_listener_fails(self):
        listener = mock.MagicMock()
        listener.__enter__.return_value = listener

        def fixture(path):
            path.write_bytes(b"\xcf\xfa\xed\xfe\x0c\x00\x00\x01")
            path.chmod(0o555)

        with mock.patch.object(seatbelt.platform, "system", return_value="Darwin"), \
             mock.patch.object(seatbelt.platform, "machine", return_value="arm64"), \
             mock.patch.object(seatbelt, "_compile_fixture", side_effect=fixture), \
             mock.patch.object(seatbelt, "_listener",
                               side_effect=[listener, OSError(97, "synthetic")]):
            classification, diagnostic = seatbelt.run()
        self.assertEqual(classification, "not_feasible")
        self.assertEqual(diagnostic["stage"], "listeners")
        listener.__exit__.assert_called_once()

    def test_listener_closes_its_socket_when_bind_fails(self):
        listener = mock.MagicMock()
        listener.bind.side_effect = OSError(1, "synthetic bind failure")
        with mock.patch.object(seatbelt.socket, "socket", return_value=listener):
            with self.assertRaises(OSError):
                seatbelt._listener(seatbelt.socket.AF_INET, ("127.0.0.1", 0))
        listener.close.assert_called_once_with()

    def test_noisy_compiler_failure_is_cli_redacted(self):
        noisy = b"compiler noise /private/secret/path" * 4096
        captured = {"stdout": noisy, "stderr": noisy, "returncode": 1,
                    "timed_out": False, "fresh_group": True,
                    "group_seen_after_leader": False,
                    "group_survived_cleanup": False}
        output = StringIO()
        with mock.patch.object(seatbelt.platform, "system", return_value="Darwin"), \
             mock.patch.object(seatbelt.platform, "machine", return_value="arm64"), \
             mock.patch.object(seatbelt, "_capture", return_value=captured), \
             redirect_stdout(output):
            returncode = seatbelt.main()
        lines = output.getvalue().splitlines()
        self.assertEqual(returncode, 1)
        self.assertEqual(lines[-1], "not_feasible")
        self.assertEqual(len(lines), 2)
        self.assertNotIn("compiler noise", output.getvalue())
        self.assertNotIn("/private/secret", output.getvalue())
        diagnostic = __import__("json").loads(lines[0])
        self.assertEqual(diagnostic,
                         {"reason": "internal_error", "stage": "compile"})

    def test_compiler_rejects_a_cleaned_post_leader_descendant(self):
        captured = {"stdout": b"", "stderr": b"", "returncode": 0,
                    "timed_out": False, "fresh_group": True,
                    "group_seen_after_leader": True,
                    "group_survived_cleanup": False}
        with tempfile.TemporaryDirectory() as temporary, \
             mock.patch.object(seatbelt, "_capture", return_value=captured):
            with self.assertRaisesRegex(RuntimeError, "compiler invocation failed"):
                seatbelt._compile_fixture(Path(temporary) / "probe")

    @unittest.skipUnless(hasattr(os, "fork"), "process-group test requires fork")
    def test_descendant_timeout_is_killed_and_group_disappears(self):
        program = (
            "import os,signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "pid=os.fork(); signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)"
        )
        with mock.patch.object(seatbelt, "PROBE_TIMEOUT_SECONDS", 0.1), \
             mock.patch.object(seatbelt, "TERMINATION_GRACE_SECONDS", 0.1):
            captured = seatbelt._capture(
                [sys.executable, "-c", program], {"PATH": os.environ.get("PATH", "")})
        self.assertTrue(captured["fresh_group"])
        self.assertTrue(captured["timed_out"])
        self.assertFalse(captured["group_survived_cleanup"])

    @unittest.skipUnless(hasattr(os, "fork"), "process-group test requires fork")
    def test_post_leader_descendant_is_cleaned_but_process_gate_is_false(self):
        program = (
            "import os,signal,time; pid=os.fork(); "
            "(os.close(0),os.close(1),os.close(2),"
            "signal.signal(signal.SIGTERM,signal.SIG_IGN),time.sleep(30)) "
            "if pid==0 else None"
        )
        with mock.patch.object(seatbelt, "TERMINATION_GRACE_SECONDS", 0.1):
            captured = seatbelt._capture(
                [sys.executable, "-c", program], {"PATH": os.environ.get("PATH", "")},
                timeout_seconds=2)
        self.assertTrue(captured["group_seen_after_leader"])
        self.assertFalse(captured["group_survived_cleanup"])
        self.assertFalse(seatbelt._process_clean(captured))

    def test_unsupported_host_stops_without_subprocess(self):
        with mock.patch.object(seatbelt.platform, "system", return_value="Linux"), \
             mock.patch.object(seatbelt.subprocess, "run") as invoked:
            classification, diagnostic = seatbelt.run()
        self.assertEqual(classification, "not_feasible")
        self.assertEqual(diagnostic["reason"], "host_is_not_darwin_arm64")
        invoked.assert_not_called()

    @unittest.skipUnless(platform.system() == "Darwin" and platform.machine() == "arm64",
                         "native fixture build requires an arm64 macOS host")
    def test_committed_fixture_builds_as_arm64_macho(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "probe"
            seatbelt._compile_fixture(executable)
            self.assertEqual(executable.read_bytes()[:8],
                             b"\xcf\xfa\xed\xfe\x0c\x00\x00\x01")
            completed = subprocess.run([str(executable)], capture_output=True)
            self.assertEqual(completed.returncode, 64)


if __name__ == "__main__":
    unittest.main()
