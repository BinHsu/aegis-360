#!/usr/bin/env python3
"""Run a synthetic, non-authoritative Seatbelt feasibility observation."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import platform
import plistlib
import signal
import shutil
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "seatbelt_feasibility_probe.c"
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    build_seatbelt_backend_manifest_shape,
    render_seatbelt_policy_input_shape_bytes,
)
DENIAL_ERRNOS = {errno.EACCES, errno.EPERM}
ALLOWED_BYTES = {
    "bundle_read": b"bundle-stand-in-v1",
    "model_read": b"model-stand-in-v1",
    "prompt_read": b"prompt-stand-in-v1",
}
FORBIDDEN_BYTES = b"forbidden-stand-in-v1"
SCRATCH_BYTES = b"scratch-write-sentinel-v1"
COMPILE_TIMEOUT_SECONDS = 15
PROBE_TIMEOUT_SECONDS = 15
TERMINATION_GRACE_SECONDS = 2
CAPTURE_LIMIT_BYTES = 65_536
SYNTHETIC_LAUNCHER_MANIFEST_SHA256 = hashlib.sha256(
    b"aegis360.synthetic-seatbelt-feasibility-launcher.v1").hexdigest()
EXPECTED_OPERATIONS = frozenset(ALLOWED_BYTES) | {
    "scratch_write", "repository_read", "protocol_read", "neighbor_read",
    "result_read", "outside_create", "outside_overwrite", "outside_truncate",
    "outside_rename", "outside_unlink", "process_fork", "ipv4_socket",
    "ipv4_connect", "ipv6_socket", "ipv6_connect", "unix_socket",
    "unix_connect", "forbidden_exec"}


def _candidate_backend_shape(sandbox_exec: Path):
    """Build non-authoritative renderer input from current host content facts."""
    system_version = Path("/System/Library/CoreServices/SystemVersion.plist").read_bytes()
    os_build = plistlib.loads(system_version)["ProductBuildVersion"]
    value = sandbox_exec.stat()
    return build_seatbelt_backend_manifest_shape(
        os_build=os_build, architecture="arm64",
        backend_executable_sha256=hashlib.sha256(sandbox_exec.read_bytes()).hexdigest(),
        backend_executable_size=value.st_size,
        launcher_runtime_manifest_sha256=SYNTHETIC_LAUNCHER_MANIFEST_SHA256,
        system_version_sha256=hashlib.sha256(system_version).hexdigest())


def parse_probe_stdout(value: bytes) -> dict[str, dict[str, object]]:
    observations = {}
    for raw_line in value.splitlines():
        fields = raw_line.split(b"\t")
        if len(fields) != 4:
            raise ValueError("probe output line has the wrong field count")
        try:
            name = fields[0].decode("ascii")
            number = int(fields[1])
            error = int(fields[2])
            data = bytes.fromhex(fields[3].decode("ascii"))
        except (UnicodeError, ValueError) as failure:
            raise ValueError("probe output is malformed") from failure
        if name in observations:
            raise ValueError("probe output name is duplicated")
        observations[name] = {"value": number, "errno": error,
                              "data_sha256": hashlib.sha256(data).hexdigest(),
                              "data": data}
    return observations


def _write(path: Path, value: bytes, mode: int = 0o444) -> None:
    path.write_bytes(value)
    path.chmod(mode)


def _compile_fixture(destination: Path) -> None:
    clang = shutil.which("clang")
    if clang is None:
        raise RuntimeError("clang is unavailable")
    captured = _capture(
        [clang, "-arch", "arm64", "-std=c11", "-Wall", "-Wextra", "-Werror",
         "-O2", str(SOURCE), "-o", str(destination)], None,
        timeout_seconds=COMPILE_TIMEOUT_SECONDS)
    if captured["timed_out"]:
        raise subprocess.TimeoutExpired(["clang"], COMPILE_TIMEOUT_SECONDS)
    if not _process_clean(captured):
        raise RuntimeError("compiler invocation failed")
    destination.chmod(0o555)
    header = destination.read_bytes()[:8]
    if (len(header) != 8 or header[:4] != b"\xcf\xfa\xed\xfe"
            or struct.unpack("<I", header[4:])[0] != 0x0100000C):
        raise RuntimeError("fixture is not a thin native arm64 Mach-O")


def _listener(family: int, address):
    listener = socket.socket(family, socket.SOCK_STREAM)
    try:
        if family in (socket.AF_INET, socket.AF_INET6):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(address)
        listener.listen(4)
        listener.setblocking(False)
        return listener
    except BaseException:
        listener.close()
        raise


def _accepted_count(listener: socket.socket) -> int:
    count = 0
    while True:
        try:
            connection, _ = listener.accept()
        except BlockingIOError:
            return count
        connection.close()
        count += 1


def _safe_snapshot(directory: Path) -> dict[str, tuple[int, int, int, int, int, int, str]]:
    snapshot = {}
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name in sorted(os.listdir(directory_fd)):
            value = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            kind = stat.S_IFMT(value.st_mode)
            digest = ""
            if stat.S_ISREG(value.st_mode):
                fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
                try:
                    opened = os.fstat(fd)
                    if ((opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode))
                            != (value.st_dev, value.st_ino, kind)):
                        raise OSError(errno.ESTALE, "snapshot identity changed")
                    hasher = hashlib.sha256()
                    while chunk := os.read(fd, 1024 * 1024):
                        hasher.update(chunk)
                    digest = hasher.hexdigest()
                finally:
                    os.close(fd)
            snapshot[name] = (kind, value.st_uid, value.st_dev, value.st_ino,
                              stat.S_IMODE(value.st_mode), value.st_size, digest)
    finally:
        os.close(directory_fd)
    return snapshot


def _group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _terminate_group(process: subprocess.Popen, pgid: int) -> tuple[bytes, bytes, bool]:
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        group_was_already_absent = True
    deadline = time.monotonic() + TERMINATION_GRACE_SECONDS
    while _group_exists(pgid) and time.monotonic() < deadline:
        time.sleep(0.01)
    if _group_exists(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            group_was_already_absent = True
    try:
        stdout, stderr = process.communicate(timeout=TERMINATION_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            leader_was_already_absent = True
        try:
            stdout, stderr = process.communicate(timeout=TERMINATION_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            stdout, stderr = b"", b""
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            try:
                process.wait(timeout=TERMINATION_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                leader_reap_timed_out = True
    disappearance_deadline = time.monotonic() + TERMINATION_GRACE_SECONDS
    while _group_exists(pgid) and time.monotonic() < disappearance_deadline:
        time.sleep(0.01)
    return ((stdout or b"")[:CAPTURE_LIMIT_BYTES + 1],
            (stderr or b"")[:CAPTURE_LIMIT_BYTES + 1], _group_exists(pgid))


def _capture(argv, environment, *, timeout_seconds=None,
             output_limit_bytes=CAPTURE_LIMIT_BYTES) -> dict[str, object]:
    """Capture a fresh group and cap retained evidence, not acquisition memory."""
    if timeout_seconds is None:
        timeout_seconds = PROBE_TIMEOUT_SECONDS
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True, close_fds=True, env=environment)
    try:
        pgid = os.getpgid(process.pid)
    except BaseException:
        _terminate_group(process, process.pid)
        raise
    if pgid != process.pid:
        stdout, stderr, surviving = _terminate_group(process, pgid)
        return {"stdout": stdout, "stderr": stderr, "returncode": process.poll(),
                "timed_out": False, "group_seen_after_leader": True,
                "group_survived_cleanup": surviving, "fresh_group": False}
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=b"", timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        stdout, stderr, surviving = _terminate_group(process, pgid)
        return {"stdout": stdout, "stderr": stderr, "returncode": process.poll(),
                "timed_out": True, "group_seen_after_leader": True,
                "group_survived_cleanup": surviving, "fresh_group": True}
    except BaseException:
        _terminate_group(process, pgid)
        raise
    group_seen = _group_exists(pgid)
    surviving = False
    if group_seen:
        extra_stdout, extra_stderr, surviving = _terminate_group(process, pgid)
        stdout += extra_stdout
        stderr += extra_stderr
    stdout = stdout[:output_limit_bytes + 1]
    stderr = stderr[:output_limit_bytes + 1]
    return {"stdout": stdout, "stderr": stderr, "returncode": process.returncode,
            "timed_out": timed_out, "group_seen_after_leader": group_seen,
            "group_survived_cleanup": surviving, "fresh_group": True}


def _process_clean(captured: dict[str, object]) -> bool:
    """Require no post-leader PGID survivor, even when cleanup removed it."""
    return (captured["returncode"] == 0 and captured["stderr"] == b""
            and captured["fresh_group"] is True
            and captured["timed_out"] is False
            and captured["group_seen_after_leader"] is False
            and captured["group_survived_cleanup"] is False)


def _denied(observation: dict[str, object]) -> bool:
    return observation["value"] == -1 and observation["errno"] in DENIAL_ERRNOS


def _public_observations(observations):
    return {name: {key: value for key, value in row.items() if key != "data"}
            for name, row in sorted(observations.items())}


def _run_inner(progress: dict[str, str]) -> tuple[str, dict[str, object]]:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return "not_feasible", {"reason": "host_is_not_darwin_arm64"}
    sandbox_exec = Path("/usr/bin/sandbox-exec")
    if not sandbox_exec.is_file():
        return "not_feasible", {"reason": "sandbox_exec_is_unavailable"}
    progress["stage"] = "setup"
    with ExitStack() as stack:
        raw_temp = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="aegis-seatbelt-", dir="/tmp"))
        base = Path(raw_temp).resolve()
        allowed = {name: base / name for name in ("bundle", "model", "prompt")}
        runtime = base / "runtime"
        scratch = base / "scratch"
        private_home = base / "home"
        private_tmpdir = base / "tmpdir"
        forbidden = base / "forbidden"
        for directory in (*allowed.values(), runtime, scratch, private_home, private_tmpdir,
                          forbidden):
            directory.mkdir(mode=0o700)
        executable = runtime / "probe"
        forbidden_executable = forbidden / "exec-sentinel"
        progress["stage"] = "compile"
        try:
            _compile_fixture(executable)
        except subprocess.TimeoutExpired:
            return "not_feasible", {"reason": "compile_timeout", "stage": "compile"}
        shutil.copy2(executable, forbidden_executable)
        forbidden_executable.chmod(0o555)
        allowed_files = {}
        for name, value in ALLOWED_BYTES.items():
            short_name = name.removesuffix("_read")
            allowed_files[name] = allowed[short_name] / "sentinel"
            _write(allowed_files[name], value)
        forbidden_files = {}
        for name in ("repository_read", "protocol_read", "neighbor_read", "result_read"):
            forbidden_files[name] = forbidden / name
            _write(forbidden_files[name], FORBIDDEN_BYTES)
        outside_existing = forbidden / "outside-existing"
        _write(outside_existing, FORBIDDEN_BYTES)
        outside_create = forbidden / "outside-created"
        rename_source = scratch / "rename-source"
        _write(rename_source, b"rename-source-v1", 0o600)
        rename_destination = forbidden / "renamed"
        fork_marker = scratch / "fork-marker"
        exec_marker = scratch / "exec-marker"
        scratch_write = scratch / "write-sentinel"
        unix_path = base / "listener.sock"
        progress["stage"] = "listeners"
        ipv4 = stack.enter_context(_listener(socket.AF_INET, ("127.0.0.1", 0)))
        try:
            ipv6 = stack.enter_context(_listener(socket.AF_INET6, ("::1", 0)))
        except OSError as failure:
            return "not_feasible", {"reason": "ipv6_loopback_listener_unavailable",
                                    "errno": failure.errno, "stage": "listeners"}
        unix = stack.enter_context(_listener(socket.AF_UNIX, str(unix_path)))
        before_forbidden = _safe_snapshot(forbidden)
        before_rename = _safe_snapshot(scratch)[rename_source.name]
        before_home = _safe_snapshot(private_home)
        before_tmpdir = _safe_snapshot(private_tmpdir)
        policy = render_seatbelt_policy_input_shape_bytes(
            backend_manifest=_candidate_backend_shape(sandbox_exec),
            dynamic_roots={"runtime_root": str(runtime),
                "runtime_executable": str(executable),
                "forbidden_executable": str(forbidden_executable),
                "bundle_root": str(allowed["bundle"]),
                "model_root": str(allowed["model"]),
                "prompt_root": str(allowed["prompt"]),
                "scratch_root": str(scratch)})
        policy_path = base / "candidate.sb"
        policy_path.write_bytes(policy)
        argv = [str(sandbox_exec), "-f", str(policy_path), str(executable),
                "--aegis-seatbelt-feasibility-probe",
                str(allowed_files["bundle_read"]), str(allowed_files["model_read"]),
                str(allowed_files["prompt_read"]), str(scratch_write),
                str(forbidden_files["repository_read"]),
                str(forbidden_files["protocol_read"]),
                str(forbidden_files["neighbor_read"]),
                str(forbidden_files["result_read"]), str(outside_create),
                str(outside_existing), str(rename_source), str(rename_destination),
                str(fork_marker), str(ipv4.getsockname()[1]),
                str(ipv6.getsockname()[1]), str(unix_path), str(forbidden_executable),
                str(exec_marker)]
        progress["stage"] = "launch"
        captured = _capture(argv,
            {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1",
             "HOME": str(private_home), "TMPDIR": str(private_tmpdir)})
        accepts = {"ipv4": _accepted_count(ipv4), "ipv6": _accepted_count(ipv6),
                   "unix": _accepted_count(unix)}
        progress["stage"] = "parse"
        try:
            observations = parse_probe_stdout(captured["stdout"])
        except ValueError:
            observations = {}
        expected_names = EXPECTED_OPERATIONS
        allowed_ok = all(name in observations
            and observations[name]["value"] == len(value)
            and observations[name]["errno"] == 0
            and observations[name]["data"] == value
            for name, value in ALLOWED_BYTES.items())
        scratch_ok = (observations.get("scratch_write", {}).get("value")
                      == len(SCRATCH_BYTES) and scratch_write.is_file()
                      and scratch_write.read_bytes() == SCRATCH_BYTES)
        socket_names = {"ipv4_socket", "ipv6_socket", "unix_socket"}
        socket_ok = all(name in observations
            and observations[name]["value"] >= 0 and observations[name]["errno"] == 0
            for name in socket_names)
        denied_names = (expected_names - set(ALLOWED_BYTES)
                        - {"scratch_write", *socket_names})
        denials_ok = all(name in observations and _denied(observations[name])
                         for name in denied_names)
        fork_evidence_ok = (observations.get("process_fork", {}).get("data")
                            == b"-1,-1,0")
        overwrite_stage_ok = (observations.get("outside_overwrite", {}).get("data")
                              in {b"open", b"pwrite"})
        progress["stage"] = "filesystem"
        after_forbidden = _safe_snapshot(forbidden)
        side_effects_absent = (before_forbidden == after_forbidden
            and rename_source.is_file()
            and _safe_snapshot(scratch).get(rename_source.name) == before_rename
            and not outside_create.exists() and not rename_destination.exists()
            and not fork_marker.exists() and not exec_marker.exists()
            and accepts == {"ipv4": 0, "ipv6": 0, "unix": 0}
            and _safe_snapshot(private_home) == before_home == {}
            and _safe_snapshot(private_tmpdir) == before_tmpdir == {})
        process_ok = _process_clean(captured)
        feasible = (process_ok
                    and set(observations) == expected_names and allowed_ok and scratch_ok
                    and socket_ok and denials_ok and fork_evidence_ok
                    and overwrite_stage_ok and side_effects_absent)
        diagnostic = {
            "host": {"machine": platform.machine(), "system": platform.system()},
            "policy_sha256": hashlib.sha256(policy).hexdigest(),
            "process": {"returncode": captured["returncode"],
                        "stderr_bytes": len(captured["stderr"]),
                        "timed_out": captured["timed_out"],
                        "fresh_group": captured["fresh_group"],
                        "group_seen_after_leader": captured["group_seen_after_leader"],
                        "group_survived_cleanup": captured["group_survived_cleanup"]},
            "listener_accepts": accepts,
            "checks": {"allowed_bytes": allowed_ok, "scratch_write": scratch_ok,
                       "socket_creation": socket_ok, "denials": denials_ok,
                       "fork_evidence": fork_evidence_ok,
                       "overwrite_stage": overwrite_stage_ok,
                       "side_effects_absent": side_effects_absent,
                       "process_group": process_ok,
                       "observation_set_exact": set(observations) == expected_names},
            "observations": _public_observations(observations),
        }
        return ("feasible" if feasible else "not_feasible"), diagnostic


def run() -> tuple[str, dict[str, object]]:
    """Normalize every harness failure without exposing paths or exception text."""
    progress = {"stage": "preflight"}
    try:
        return _run_inner(progress)
    except BaseException as failure:
        if isinstance(failure, KeyboardInterrupt):
            reason = "interrupted"
        elif isinstance(failure, subprocess.TimeoutExpired):
            reason = "subprocess_timeout"
        elif isinstance(failure, OSError):
            reason = "operating_system_error"
        else:
            reason = "internal_error"
        return "not_feasible", {"reason": reason, "stage": progress["stage"]}


def main() -> int:
    classification, diagnostic = run()
    print(json.dumps(diagnostic, allow_nan=False, sort_keys=True, separators=(",", ":")))
    print(classification)
    return 0 if classification == "feasible" else 1


if __name__ == "__main__":
    sys.exit(main())
