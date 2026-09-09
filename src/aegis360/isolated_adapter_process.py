"""Bounded subprocess capture for an already-probed isolated adapter backend.

This module does not provide, select, or attest an isolation backend.  Its
single-use token is an injected capability owned by a higher-level coordinator.
That backend is responsible for descriptor-bound execution and must fstat the
retained objects and compare their current path identities at its spawn boundary.
"""

from __future__ import annotations

import os
import selectors
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence


TIMEOUT_NS = 120_000_000_000
TERMINATION_GRACE_NS = 2_000_000_000
STDOUT_LIMIT = 65_536
STDERR_LIMIT = 65_536


class CapabilityUnavailable(ValueError):
    """Raised before spawn when the injected capability cannot be claimed."""


class ProbedBackendToken(Protocol):
    def claim_probed_capability(self, invocation: "InvocationDescriptor") -> bool: ...
    def revalidate_invocation(self, invocation: "InvocationDescriptor") -> bool: ...
    def spawn(self, invocation: "InvocationDescriptor", argv: Sequence[str], **kwargs): ...
    def terminate_group(self, process) -> None: ...
    def kill_group(self, process) -> None: ...


@dataclass(frozen=True)
class FileIdentity:
    path: str
    device: int
    inode: int
    mode: int
    uid: int
    expected_mode: int
    retained_fd: int


@dataclass(frozen=True)
class InvocationDescriptor:
    argv: tuple[str, ...]
    executable: FileIdentity
    bundle_cwd: FileIdentity
    private_home: FileIdentity
    private_tmpdir: FileIdentity


@dataclass(frozen=True)
class ProcessCapture:
    stdout: bytes
    stdout_present: bool
    invocation_failed: bool
    reason: str
    returncode: int | None
    stdout_overflow: bool
    stderr_present: bool
    stderr_overflow: bool
    timed_out: bool
    cleanup_failed: bool


def _identity(path: Path, label: str, expected_mode: int, *, directory: bool) -> FileIdentity:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"{label} must be absolute")
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    retained_fd = None
    try:
        retained_fd = os.open(path, flags)
        value = os.fstat(retained_fd)
        path_value = path.lstat()
    except OSError as error:
        if retained_fd is not None:
            try: os.close(retained_fd)
            except OSError: pass
        raise ValueError(f"{label} cannot be inspected") from error
    kind_ok = stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode)
    mode = stat.S_IMODE(value.st_mode)
    if (not kind_ok or mode != expected_mode or value.st_uid != os.getuid()
            or (value.st_dev, value.st_ino) != (path_value.st_dev, path_value.st_ino)):
        os.close(retained_fd)
        raise ValueError(f"{label} identity, owner, or mode is invalid")
    return FileIdentity(str(path), value.st_dev, value.st_ino, mode, value.st_uid,
                        expected_mode, retained_fd)


def _validate_argv(argv: Sequence[str]) -> tuple[str, ...]:
    if (not isinstance(argv, Sequence) or isinstance(argv, (str, bytes))
            or not argv or any(not isinstance(value, str) or not value
                               or "\x00" in value for value in argv)):
        raise ValueError("adapter argv is invalid")
    return tuple(argv)


def build_invocation_descriptor(*, argv: Sequence[str], bundle_cwd: Path,
        private_home: Path, private_tmpdir: Path) -> InvocationDescriptor:
    checked_argv = _validate_argv(argv)
    retained: list[FileIdentity] = []
    try:
        retained.append(_identity(Path(checked_argv[0]), "adapter executable", 0o555,
                                  directory=False))
        retained.append(_identity(bundle_cwd, "bundle cwd", 0o555, directory=True))
        retained.append(_identity(private_home, "private HOME", 0o700, directory=True))
        retained.append(_identity(private_tmpdir, "private TMPDIR", 0o700, directory=True))
        if ((retained[2].device, retained[2].inode)
                == (retained[3].device, retained[3].inode)):
            raise ValueError("private HOME and TMPDIR must be distinct")
        if os.listdir(retained[2].retained_fd) or os.listdir(retained[3].retained_fd):
            raise ValueError("private HOME and TMPDIR must be exactly empty")
        return InvocationDescriptor(checked_argv, *retained)
    except Exception:
        for identity in retained:
            try: os.close(identity.retained_fd)
            except OSError: pass
        raise


def invocation_identity_matches(invocation: InvocationDescriptor) -> bool:
    """Compare every retained object to both its fstat and current path identity."""
    for identity in (invocation.executable, invocation.bundle_cwd,
                     invocation.private_home, invocation.private_tmpdir):
        try:
            retained = os.fstat(identity.retained_fd)
            current = os.lstat(identity.path)
        except OSError:
            return False
        if ((retained.st_dev, retained.st_ino, stat.S_IMODE(retained.st_mode), retained.st_uid)
                != (identity.device, identity.inode, identity.mode, identity.uid)
                or identity.mode != identity.expected_mode
                or (current.st_dev, current.st_ino) != (identity.device, identity.inode)):
            return False
    try:
        return (not os.listdir(invocation.private_home.retained_fd)
                and not os.listdir(invocation.private_tmpdir.retained_fd))
    except OSError:
        return False


def _close_invocation(invocation: InvocationDescriptor) -> None:
    for identity in (invocation.executable, invocation.bundle_cwd,
                     invocation.private_home, invocation.private_tmpdir):
        try: os.close(identity.retained_fd)
        except OSError: pass


def _close_process_streams(process) -> None:
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(process, stream_name, None)
        if stream is not None:
            try: stream.close()
            except (OSError, ValueError): pass


def _hard_cleanup(backend_token: ProbedBackendToken, process,
        monotonic_ns: Callable[[], int]) -> None:
    try: backend_token.terminate_group(process)
    except (OSError, ProcessLookupError): pass
    deadline = monotonic_ns() + TERMINATION_GRACE_NS
    while process.poll() is None and monotonic_ns() < deadline:
        time.sleep(0.01)
    try: backend_token.kill_group(process)
    except (OSError, ProcessLookupError): pass
    _close_process_streams(process)
    try: process.wait()
    except (OSError, subprocess.SubprocessError): pass


def capture_adapter_process(*, backend_token: ProbedBackendToken,
        argv: Sequence[str], request_bytes: bytes, bundle_cwd: Path,
        private_home: Path, private_tmpdir: Path,
        monotonic_ns: Callable[[], int] = time.monotonic_ns) -> ProcessCapture:
    """Run one process through an injected capability and capture bounded pipes."""
    required_methods = ("claim_probed_capability", "revalidate_invocation", "spawn",
                        "terminate_group", "kill_group")
    if backend_token is None or any(not callable(getattr(backend_token, name, None))
                                    for name in required_methods):
        raise CapabilityUnavailable("an already-probed backend token is required")
    if not isinstance(request_bytes, bytes):
        raise ValueError("adapter request must be exact bytes")
    invocation = build_invocation_descriptor(argv=argv, bundle_cwd=bundle_cwd,
        private_home=private_home, private_tmpdir=private_tmpdir)
    try:
        claimed = backend_token.claim_probed_capability(invocation)
    except Exception as error:
        _close_invocation(invocation)
        raise CapabilityUnavailable("backend capability could not be claimed") from error
    if claimed is not True:
        _close_invocation(invocation)
        raise CapabilityUnavailable("backend capability is unavailable or already consumed")
    try:
        still_bound = backend_token.revalidate_invocation(invocation)
    except Exception as error:
        _close_invocation(invocation)
        raise CapabilityUnavailable("invocation identity could not be revalidated") from error
    if still_bound is not True:
        _close_invocation(invocation)
        raise CapabilityUnavailable("invocation identity changed before spawn")
    try:
        private_dirs_empty = (not os.listdir(invocation.private_home.retained_fd)
                              and not os.listdir(invocation.private_tmpdir.retained_fd))
    except OSError as error:
        _close_invocation(invocation)
        raise CapabilityUnavailable("private directories could not be revalidated") from error
    if not private_dirs_empty:
        _close_invocation(invocation)
        raise CapabilityUnavailable("private directories changed before spawn")
    environment = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1",
                   "HOME": invocation.private_home.path,
                   "TMPDIR": invocation.private_tmpdir.path}
    process = None
    selector = selectors.DefaultSelector()
    stdout = bytearray()
    stderr = bytearray()
    stdout_overflow = stderr_overflow = timed_out = cleanup_failed = False
    writer_error = False
    request_view = memoryview(request_bytes)
    request_offset = 0
    stdin_open = stdout_open = stderr_open = False
    forced = False
    term_sent = kill_sent = False
    termination_deadline = None
    leader_exit_seen = None
    start = monotonic_ns()
    try:
        try:
            process = backend_token.spawn(invocation, invocation.argv,
                cwd=invocation.bundle_cwd.path, env=environment,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                # The retained native launcher owns setsid() before it reads the
                # policy transport.  Asking a backend for another session would
                # either fail or move that ordering outside the launcher.
                close_fds=True, start_new_session=False, shell=False)
        except (OSError, subprocess.SubprocessError):
            return ProcessCapture(b"", False, True, "invocation_failure", None,
                                  False, False, False, False, False)
        streams = (("stdin", process.stdin), ("stdout", process.stdout),
                   ("stderr", process.stderr))
        if any(stream is None for _, stream in streams):
            raise RuntimeError("backend did not provide the required stdio pipes")
        fds = {}
        for name, stream in streams:
            fd = stream.fileno()
            if type(fd) is not int or fd < 0:
                raise RuntimeError("backend stdio must expose real file descriptors")
            os.set_blocking(fd, False)
            fds[name] = fd
        if len(set(fds.values())) != 3:
            raise RuntimeError("backend stdio file descriptors must be distinct")
        selector.register(fds["stdout"], selectors.EVENT_READ, "stdout")
        selector.register(fds["stderr"], selectors.EVENT_READ, "stderr")
        stdout_open = stderr_open = True
        if request_view:
            selector.register(fds["stdin"], selectors.EVENT_WRITE, "stdin")
            stdin_open = True
        else:
            process.stdin.close()

        while stdout_open or stderr_open or stdin_open or process.poll() is None:
            now = monotonic_ns()
            returncode_now = process.poll()
            if returncode_now is not None and leader_exit_seen is None:
                leader_exit_seen = now
            if not forced and now - start >= TIMEOUT_NS:
                timed_out = forced = True
            if (not forced and leader_exit_seen is not None
                    and (stdout_open or stderr_open or stdin_open)
                    and now - leader_exit_seen >= 100_000_000):
                cleanup_failed = forced = True
            if forced and not term_sent:
                try: backend_token.terminate_group(process)
                except (OSError, ProcessLookupError): pass
                term_sent = True
                termination_deadline = now + TERMINATION_GRACE_NS
            if (term_sent and not kill_sent and termination_deadline is not None
                    and now >= termination_deadline):
                try: backend_token.kill_group(process)
                except (OSError, ProcessLookupError): pass
                kill_sent = True
                _close_process_streams(process)
                stdin_open = stdout_open = stderr_open = False
                break
            events = selector.select(0.01)
            for key, mask in events:
                name, fd = key.data, key.fd
                if name == "stdin":
                    try:
                        count = os.write(fd, request_view[request_offset:])
                        request_offset += count
                    except BlockingIOError:
                        continue
                    except (BrokenPipeError, OSError):
                        writer_error = True
                        count = 0
                    if writer_error or request_offset == len(request_view):
                        selector.unregister(fd)
                        process.stdin.close()
                        stdin_open = False
                    continue
                try: chunk = os.read(fd, 8192)
                except BlockingIOError: continue
                except OSError:
                    chunk = b""
                    writer_error = True
                if not chunk:
                    try: selector.unregister(fd)
                    except KeyError: pass
                    if name == "stdout": stdout_open = False
                    else: stderr_open = False
                    continue
                target = stdout if name == "stdout" else stderr
                limit = STDOUT_LIMIT if name == "stdout" else STDERR_LIMIT
                remaining = limit + 1 - len(target)
                if remaining > 0: target.extend(chunk[:remaining])
                overflow = len(target) > limit or len(chunk) > remaining
                if name == "stdout": stdout_overflow |= overflow
                else: stderr_overflow |= overflow
                forced |= overflow
        returncode = process.wait()
        stdout_bytes, stderr_bytes = bytes(stdout), bytes(stderr)
        invocation_failed = bool(timed_out or stdout_overflow or stderr_overflow
            or stderr_bytes or returncode != 0
            or not stdout_bytes or writer_error or cleanup_failed)
        return ProcessCapture(stdout_bytes, bool(stdout_bytes), invocation_failed,
            "cleanup_failure" if cleanup_failed else
            ("invocation_failure" if invocation_failed else "success"), returncode,
            stdout_overflow, bool(stderr_bytes), stderr_overflow, timed_out,
            cleanup_failed)
    except Exception:
        if process is not None:
            _hard_cleanup(backend_token, process, monotonic_ns)
        raise
    finally:
        selector.close()
        if process is not None: _close_process_streams(process)
        _close_invocation(invocation)
