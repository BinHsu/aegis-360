"""Bounded launcher transport for one raw probe; never a capability receipt."""

from __future__ import annotations

import hashlib
import os
import selectors
import signal
import stat
import struct
import subprocess
import time
from dataclasses import dataclass

from . import sparse_story_batch_policy as batch_policy
from .sparse_story_probe_context import _ProbeContext
from .sparse_story_probe_transcript import (
    _check_probe_row_values, parse_isolation_probe_transcript,
)
from .sparse_story_runner_contract import MATRIX_KEYS

_TIMEOUT_NS = 120_000_000_000
_GRACE_NS = 2_000_000_000
_DRAIN_NS = 2_000_000_000
_LIMIT = 65_536


@dataclass(frozen=True)
class _RawProbeCapture:
    stdout: bytes
    returncode: int | None
    completed: bool
    postcheck_passed: bool
    reason: str


def _entrypoint_facts(proof):
    proof.manifest()
    path = proof._root / proof._entrypoint
    row = next((row for row in proof._leaves if row[0] == proof._entrypoint), None)
    if row is None: raise ValueError("retained runtime entrypoint is absent")
    value = os.fstat(row[1])
    if not stat.S_ISREG(value.st_mode):
        raise ValueError("retained runtime entrypoint changed")
    return path, value


def _close_streams(process):
    for name in ("stdin", "stdout", "stderr"):
        stream = getattr(process, name, None)
        if stream is not None:
            try: stream.close()
            except OSError: pass


def _run_raw_probe(context: _ProbeContext) -> _RawProbeCapture:
    """Execute only the closed raw-probe mode; never invoke the model adapter mode."""
    if type(context) is not _ProbeContext:
        raise TypeError("raw probe requires an exact private context")
    suffix = context.argv_suffix()
    candidate = context.candidate
    binding_before = candidate._binding_bytes()
    live = batch_policy._require_live(candidate._facade)
    launcher_proof = live._backend_binding._runtime
    runtime_proof = live._adapter_binding._runtime
    launcher, _ = _entrypoint_facts(launcher_proof)
    runtime, runtime_stat = _entrypoint_facts(runtime_proof)
    policy = candidate._policy_bytes()
    if not 1 <= len(policy) <= _LIMIT:
        raise ValueError("raw probe policy size is invalid")
    bundle_fd = candidate._proofs[0]._root_fd
    bundle_stat = os.fstat(bundle_fd)
    env = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1",
           "HOME": candidate._private_home.identity.path,
           "TMPDIR": candidate._private_tmpdir.identity.path}
    read_fd, write_fd = os.pipe()
    os.set_blocking(write_fd, False)
    transfer = memoryview(struct.pack(">Q", len(policy)) + policy)
    argv = (str(launcher), f"--policy-fd={read_fd}",
        f"--policy-size={len(policy)}",
        f"--policy-sha256={hashlib.sha256(policy).hexdigest()}",
        f"--cwd-fd={bundle_fd}", f"--cwd-dev={bundle_stat.st_dev}",
        f"--cwd-ino={bundle_stat.st_ino}", f"--uid={candidate._uid}",
        f"--gid={candidate._gid}", f"--home={env['HOME']}",
        f"--tmpdir={env['TMPDIR']}", f"--runtime-dev={runtime_stat.st_dev}",
        f"--runtime-ino={runtime_stat.st_ino}",
        f"--runtime-size={runtime_stat.st_size}", "--", str(runtime), *suffix)
    process = None
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr_present = stdout_overflow = stderr_overflow = timed_out = False
    stderr_count = 0
    writer_failed = cleanup_failed = group_verified = False
    writer_open = stdout_open = stderr_open = False
    transferred = 0
    term_at = kill_at = None
    started = time.monotonic_ns()

    def close_writer():
        nonlocal writer_open
        if writer_open:
            try: selector.unregister(write_fd)
            except KeyError: pass
            writer_open = False
        try: os.close(write_fd)
        except OSError: pass

    def signal_owned(sig):
        nonlocal cleanup_failed
        if process is None: return
        try:
            if group_verified: os.killpg(process.pid, sig)
            else: os.kill(process.pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            cleanup_failed = True

    try:
        process = subprocess.Popen(argv, pass_fds=(read_fd, bundle_fd),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, close_fds=True,
            start_new_session=False, shell=False)
        os.close(read_fd)
        read_fd = -1
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            if stream is None: raise RuntimeError("probe pipe is missing")
            os.set_blocking(stream.fileno(), False)
            selector.register(stream.fileno(), selectors.EVENT_READ, name)
        stdout_open = stderr_open = True
        while writer_open or stdout_open or stderr_open or not group_verified:
            now = time.monotonic_ns()
            if not group_verified:
                try:
                    group_verified = (os.getpgid(process.pid) == process.pid
                                      and os.getsid(process.pid) == process.pid)
                except ProcessLookupError:
                    pass
                if group_verified:
                    selector.register(write_fd, selectors.EVENT_WRITE, "policy")
                    writer_open = True
            if now - started >= _TIMEOUT_NS and term_at is None:
                timed_out = True
                term_at = now
                close_writer()
                signal_owned(signal.SIGTERM)
            if term_at is not None and now - term_at >= _GRACE_NS and kill_at is None:
                kill_at = now
                signal_owned(signal.SIGKILL)
            if kill_at is not None and now - kill_at >= _DRAIN_NS:
                cleanup_failed = True
                break
            for key, _ in selector.select(0.01):
                if key.data == "policy":
                    try: count = os.write(write_fd, transfer[transferred:])
                    except BlockingIOError: continue
                    except (BrokenPipeError, OSError):
                        writer_failed = True
                        count = 0
                    transferred += count
                    if writer_failed or transferred == len(transfer): close_writer()
                    continue
                try: chunk = os.read(key.fd, 8192)
                except BlockingIOError: continue
                except OSError:
                    cleanup_failed = True
                    chunk = b""
                if not chunk:
                    selector.unregister(key.fd)
                    if key.data == "stdout": stdout_open = False
                    else: stderr_open = False
                    continue
                if key.data == "stderr":
                    stderr_present = True
                    stderr_count = min(_LIMIT + 1, stderr_count + len(chunk))
                    stderr_overflow |= stderr_count > _LIMIT
                else:
                    remaining = _LIMIT + 1 - len(stdout)
                    if remaining > 0: stdout.extend(chunk[:remaining])
                    stdout_overflow |= len(chunk) > remaining or len(stdout) > _LIMIT
                if (stdout_overflow or stderr_overflow) and term_at is None:
                    term_at = time.monotonic_ns()
                    close_writer()
                    signal_owned(signal.SIGTERM)
            if not group_verified and not stdout_open and not stderr_open:
                close_writer()
                break
        if writer_open: close_writer()
        # Keep the exited leader unreaped while signalling its process group:
        # its PID cannot be reused as a different group identifier yet.
        exited = False
        while not exited:
            try:
                exited = os.waitid(os.P_PID, process.pid,
                    os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None
            except ChildProcessError:
                cleanup_failed = True
                break
            if exited: break
            now = time.monotonic_ns()
            if now - started >= _TIMEOUT_NS and term_at is None:
                timed_out = True
                term_at = now
                signal_owned(signal.SIGTERM)
            if term_at is not None and now - term_at >= _GRACE_NS and kill_at is None:
                kill_at = now
                signal_owned(signal.SIGKILL)
            if kill_at is not None and now - kill_at >= _DRAIN_NS:
                cleanup_failed = True
                break
            time.sleep(0.01)
        if exited and group_verified:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            except PermissionError:
                # macOS can reject a group containing only a zombie leader.
                # The post-reap group-absence check remains mandatory.
                pass
        try: returncode = process.wait(timeout=_DRAIN_NS / 1e9)
        except subprocess.TimeoutExpired:
            cleanup_failed = True
            returncode = None
        postcheck_passed = False
        group_gone = False
        if returncode is not None:
            try:
                context.postvalidate()
                if candidate._binding_bytes() != binding_before:
                    raise ValueError("probe invocation binding changed")
                launcher_proof.manifest()
                runtime_proof.manifest()
                postcheck_passed = True
            except (ValueError, OSError):
                pass
            try: os.killpg(process.pid, 0)
            except ProcessLookupError: group_gone = True
        transport_complete = bool(returncode == 0 and transferred == len(transfer)
            and group_verified and group_gone and not timed_out and not writer_failed
            and not stdout_overflow and not stderr_overflow and not stderr_present
            and not cleanup_failed and postcheck_passed and stdout)
        primitive_passed = False
        if transport_complete:
            try:
                rows = parse_isolation_probe_transcript(bytes(stdout))
                bundle, model, prompt = context.allowed
                matrix = _check_probe_row_values(rows,
                    bundle_prefix=bundle.prefix, model_prefix=model.prefix,
                    prompt_prefix=prompt.prefix)
                primitive_passed = (type(matrix) is dict
                    and set(matrix) == set(MATRIX_KEYS)
                    and all(type(matrix[key]) is bool and matrix[key]
                            for key in MATRIX_KEYS))
            except ValueError:
                pass
        completed = transport_complete and primitive_passed
        return _RawProbeCapture(bytes(stdout), returncode, completed,
            postcheck_passed, "raw_probe_complete" if completed else "raw_probe_invalid")
    finally:
        if read_fd >= 0: os.close(read_fd)
        close_writer()
        selector.close()
        if process is not None:
            if process.returncode is None:
                signal_owned(signal.SIGKILL)
                try: process.wait(timeout=_DRAIN_NS / 1e9)
                except subprocess.TimeoutExpired: pass
            _close_streams(process)
