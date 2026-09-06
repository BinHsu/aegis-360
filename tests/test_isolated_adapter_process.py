import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.isolated_adapter_process import (  # noqa: E402
    CapabilityUnavailable, STDERR_LIMIT, STDOUT_LIMIT, TIMEOUT_NS,
    capture_adapter_process, invocation_identity_matches,
)


class RealProcessBackend:
    """Test-local wrapper; deliberately not available from production code."""

    def __init__(self): self.available = True
    def claim_probed_capability(self, invocation):
        value, self.available = self.available, False
        self.claimed = invocation
        return value
    def revalidate_invocation(self, invocation):
        return invocation == self.claimed and invocation_identity_matches(invocation)
    def spawn(self, invocation, argv, **kwargs):
        if not self.revalidate_invocation(invocation):
            raise OSError("identity changed")
        return subprocess.Popen(argv, **kwargs)
    def terminate_group(self, process): os.killpg(process.pid, signal.SIGTERM)
    def kill_group(self, process):
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass


class Token:
    def __init__(self, process=None, available=True, revalidates=True):
        self.process = process; self.available = available; self.spawns = 0
        self.revalidates = revalidates; self.terminated = 0; self.killed = 0
        self.kwargs = None; self.claimed = None; self.revalidations = 0
    def claim_probed_capability(self, invocation):
        value, self.available = self.available, False
        self.claimed = invocation
        return value
    def revalidate_invocation(self, invocation):
        self.revalidations += 1
        return self.revalidates and invocation == self.claimed
    def spawn(self, invocation, argv, **kwargs):
        self.spawns += 1; self.kwargs = (list(argv), kwargs); return self.process
    def terminate_group(self, process): self.terminated += 1
    def kill_group(self, process): self.killed += 1; process.returncode = -9


class FakeProcess:
    def __init__(self, stdout=b"ok", stderr=b"", returncode=0, running=False):
        stdin_read, stdin_write = socket.socketpair()
        self.stdin_read = stdin_read
        self.stdin = os.fdopen(stdin_write.detach(), "wb", buffering=0)
        stdout_read, stdout_write = socket.socketpair()
        stdout_read.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262_144)
        stdout_write.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262_144)
        stdout_write.sendall(stdout); stdout_write.close()
        self.stdout = os.fdopen(stdout_read.detach(), "rb", buffering=0)
        stderr_read, stderr_write = socket.socketpair()
        stderr_read.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 262_144)
        stderr_write.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 262_144)
        stderr_write.sendall(stderr); stderr_write.close()
        self.stderr = os.fdopen(stderr_read.detach(), "rb", buffering=0)
        self.returncode = None
        self.desired_returncode = returncode
        self.running = running
        self.waits = 0; self.stdin_received = b""
    def poll(self):
        if self.returncode is None and not self.running and self.stdin.closed:
            self.returncode = self.desired_returncode
        return self.returncode
    def wait(self):
        self.waits += 1
        if self.returncode is None: self.returncode = -9
        if self.stdin_read.fileno() >= 0:
            self.stdin_received = self.stdin_read.recv(1024)
            self.stdin_read.close()
        return self.returncode


class IsolatedAdapterProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); root = Path(self.temporary.name)
        self.cwd = root / "bundle"; self.home = root / "home"; self.tmp = root / "tmp"
        for path in (self.cwd, self.home, self.tmp): path.mkdir()
        self.executable = root / "adapter"
        self.executable.write_text("#!/bin/sh\ncat\n")
        self.executable.chmod(0o555); self.cwd.chmod(0o555)
        self.home.chmod(0o700); self.tmp.chmod(0o700)
        self.argv = [str(self.executable), "literal;$(no-shell)", "*.json"]
    def tearDown(self):
        self.cwd.chmod(0o755)
        self.temporary.cleanup()
    def invoke(self, token, **extra):
        return capture_adapter_process(backend_token=token, argv=self.argv,
            request_bytes=b"request", bundle_cwd=self.cwd,
            private_home=self.home, private_tmpdir=self.tmp, **extra)

    def test_capability_failure_and_bad_inputs_spawn_zero(self):
        token = Token(available=False)
        with self.assertRaises(CapabilityUnavailable): self.invoke(token)
        self.assertEqual(token.spawns, 0)
        token = Token()
        with self.assertRaises(ValueError):
            capture_adapter_process(backend_token=token, argv=["relative"],
                request_bytes=b"", bundle_cwd=self.cwd,
                private_home=self.home, private_tmpdir=self.tmp)
        self.assertEqual(token.spawns, 0)

    def test_identity_descriptor_modes_and_revalidation_mismatch_spawn_zero(self):
        token = Token(revalidates=False)
        with self.assertRaises(CapabilityUnavailable): self.invoke(token)
        self.assertEqual(token.spawns, 0)
        self.assertEqual(token.revalidations, 1)
        descriptor = token.claimed
        self.assertEqual(descriptor.argv, tuple(self.argv))
        for identity, expected in ((descriptor.executable, 0o555),
                (descriptor.bundle_cwd, 0o555), (descriptor.private_home, 0o700),
                (descriptor.private_tmpdir, 0o700)):
            self.assertEqual(identity.mode, expected)
            self.assertEqual(identity.expected_mode, expected)
            self.assertEqual(identity.uid, os.getuid())
            self.assertGreater(identity.inode, 0)

    def test_path_replacement_after_claim_is_detected_with_retained_fd(self):
        executable = self.executable
        class ReplacingToken(Token):
            def claim_probed_capability(inner, invocation):
                claimed = super(ReplacingToken, inner).claim_probed_capability(invocation)
                executable.rename(executable.with_suffix(".retained"))
                executable.write_text("#!/bin/sh\nexit 9\n")
                executable.chmod(0o555)
                return claimed
            def revalidate_invocation(inner, invocation):
                inner.revalidations += 1
                return invocation == inner.claimed and invocation_identity_matches(invocation)
        token = ReplacingToken()
        with self.assertRaises(CapabilityUnavailable): self.invoke(token)
        self.assertEqual(token.spawns, 0)

    def test_wrong_mode_and_symlink_fail_before_claim_or_spawn(self):
        self.executable.chmod(0o755)
        token = Token()
        with self.assertRaises(ValueError): self.invoke(token)
        self.assertEqual((token.claimed, token.spawns), (None, 0))
        self.executable.chmod(0o555)
        link = Path(self.temporary.name) / "adapter-link"
        link.symlink_to(self.executable)
        self.argv[0] = str(link)
        with self.assertRaises(ValueError): self.invoke(Token())

    def test_home_tmp_must_be_distinct_and_empty_before_claim(self):
        token = Token()
        with self.assertRaises(ValueError):
            capture_adapter_process(backend_token=token, argv=self.argv,
                request_bytes=b"request", bundle_cwd=self.cwd,
                private_home=self.home, private_tmpdir=self.home)
        self.assertIsNone(token.claimed)
        self.assertEqual(token.spawns, 0)
        marker = self.home / "unexpected"
        marker.write_bytes(b"x")
        token = Token()
        with self.assertRaises(ValueError): self.invoke(token)
        self.assertIsNone(token.claimed)
        self.assertEqual(token.spawns, 0)
        marker.unlink()

    def test_claim_time_private_directory_insertion_has_zero_spawn(self):
        home = self.home
        class InsertingToken(Token):
            def claim_probed_capability(inner, invocation):
                claimed = super(InsertingToken, inner).claim_probed_capability(invocation)
                (home / "inserted").write_bytes(b"x")
                return claimed
        token = InsertingToken()
        with self.assertRaises(CapabilityUnavailable): self.invoke(token)
        self.assertEqual(token.spawns, 0)

    def test_retained_descriptors_are_closed_after_capture(self):
        token = Token(FakeProcess())
        self.invoke(token)
        for identity in (token.claimed.executable, token.claimed.bundle_cwd,
                token.claimed.private_home, token.claimed.private_tmpdir):
            with self.assertRaises(OSError): os.fstat(identity.retained_fd)

    def test_direct_argv_exact_environment_and_success(self):
        token = Token(FakeProcess(stdout=b'{"closed":true}'))
        result = self.invoke(token)
        self.assertFalse(result.invocation_failed); self.assertEqual(result.stdout, b'{"closed":true}')
        argv, kwargs = token.kwargs
        self.assertEqual(argv, self.argv); self.assertFalse(kwargs["shell"])
        self.assertTrue(kwargs["close_fds"]); self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(kwargs["cwd"], str(self.cwd))
        self.assertEqual(kwargs["env"], {"LANG": "C", "LC_ALL": "C", "TZ": "UTC",
            "NO_COLOR": "1", "HOME": str(self.home), "TMPDIR": str(self.tmp)})
        self.assertEqual(token.process.stdin_received, b"request")

    def test_failure_matrix_and_bounded_prefixes(self):
        cases = ((b"", b"", 0), (b"ok", b"warning", 0), (b"ok", b"", 3),
                 (b"x" * (STDOUT_LIMIT + 2), b"", 0),
                 (b"ok", b"e" * (STDERR_LIMIT + 2), 0))
        for stdout, stderr, code in cases:
            token = Token(FakeProcess(stdout=stdout, stderr=stderr, returncode=code))
            result = self.invoke(token)
            self.assertTrue(result.invocation_failed)
            self.assertLessEqual(len(result.stdout), STDOUT_LIMIT + 1)

    def test_exact_stdout_limit_succeeds(self):
        result = self.invoke(Token(FakeProcess(stdout=b"x" * STDOUT_LIMIT)))
        self.assertFalse(result.invocation_failed)
        self.assertFalse(result.stdout_overflow)
        self.assertEqual(len(result.stdout), STDOUT_LIMIT)

    def test_stdout_overflow_terminates_then_kills_and_retains_exact_witness(self):
        process = FakeProcess(stdout=b"x" * (STDOUT_LIMIT + 2), running=True)
        token = Token(process)
        result = self.invoke(token)
        self.assertTrue(result.stdout_overflow)
        self.assertEqual(len(result.stdout), STDOUT_LIMIT + 1)
        self.assertEqual((token.terminated, token.killed), (1, 1))

    def test_timeout_terminates_then_kills_and_reaps(self):
        process = FakeProcess(running=True); token = Token(process)
        ticks = iter((0, TIMEOUT_NS, TIMEOUT_NS, TIMEOUT_NS + 2_000_000_000))
        result = self.invoke(token, monotonic_ns=lambda: next(ticks))
        self.assertTrue(result.timed_out); self.assertTrue(result.invocation_failed)
        self.assertEqual((token.terminated, token.killed), (1, 1))
        self.assertEqual(result.returncode, -9)

    def test_bounded_real_process_smoke(self):
        backend = RealProcessBackend()
        command = [str(self.executable)]
        result = capture_adapter_process(backend_token=backend, argv=command,
            request_bytes=b"exact", bundle_cwd=self.cwd,
            private_home=self.home, private_tmpdir=self.tmp)
        self.assertEqual(result.stdout, b"exact"); self.assertFalse(result.invocation_failed)
        with self.assertRaises(CapabilityUnavailable):
            capture_adapter_process(backend_token=backend, argv=command,
                request_bytes=b"again", bundle_cwd=self.cwd,
                private_home=self.home, private_tmpdir=self.tmp)

    def test_real_grandchild_pipe_holder_is_killed_and_reported(self):
        self.executable.chmod(0o755)
        self.executable.write_text("#!/usr/bin/python3\nimport os, time\n"
            "if os.fork() == 0:\n time.sleep(30)\n os._exit(0)\n"
            "print('ok', flush=True)\n")
        self.executable.chmod(0o555)
        result = self.invoke(RealProcessBackend())
        self.assertTrue(result.invocation_failed)
        self.assertTrue(result.cleanup_failed)
        self.assertEqual(result.reason, "cleanup_failure")
        self.assertEqual(result.stdout, b"ok\n")

    def test_missing_pipe_running_process_is_hard_cleaned_and_reaped(self):
        process = FakeProcess(running=True)
        process.stdout.close(); process.stdout = None
        token = Token(process)
        with self.assertRaises(RuntimeError): self.invoke(token)
        self.assertEqual((token.terminated, token.killed), (1, 1))
        self.assertGreaterEqual(process.waits, 1)

    def test_capture_creates_no_threads(self):
        before = {thread.ident for thread in threading.enumerate()}
        self.invoke(Token(FakeProcess()))
        after = {thread.ident for thread in threading.enumerate()}
        self.assertEqual(after, before)


if __name__ == "__main__": unittest.main()
