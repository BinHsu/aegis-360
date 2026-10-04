"""Retain actual other-packet and full-result read-denial probe leaves."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from contextlib import ExitStack, contextmanager
from pathlib import Path

from .sparse_story_batch_policy import _BatchPolicyCandidate
from .sparse_story_media_tree import _derive_gate_result
from .sparse_story_probe_sentinels import _ReadDenialSentinel

_DECOY_BYTES = b"one-packet-neighbor-sentinel-v1"


class _OwnedOnePacketNeighbor:
    """Own one non-media decoy leaf until the probe leader has been reaped."""

    def __init__(self, *, candidate: _BatchPolicyCandidate, parent: Path):
        if type(candidate) is not _BatchPolicyCandidate:
            raise TypeError("one-packet neighbor requires a private batch candidate")
        if (not isinstance(parent, Path) or not parent.is_absolute()
                or parent.resolve(strict=True) != parent):
            raise ValueError("one-packet neighbor parent is not canonical")
        self.candidate = candidate
        self.binding = candidate._binding_bytes()
        self.root = Path(tempfile.mkdtemp(prefix="aegis-neighbor-", dir=parent)).resolve()
        created_root = os.lstat(self.root)
        self.created_root_identity = (created_root.st_dev, created_root.st_ino)
        self.path = self.root / "neighbor-packet"
        self.root_fd = None
        self.proof = None
        self.created_identity = None
        self.closed = False
        try:
            roots = tuple(Path(value) for value in candidate._roots.values())
            if any(self.root == root or self.root in root.parents
                   or root in self.root.parents for root in roots):
                raise ValueError("one-packet neighbor overlaps policy roots")
            self.root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY
                | os.O_NOFOLLOW | os.O_CLOEXEC)
            self.root_identity = os.fstat(self.root_fd)
            fd = os.open(self.path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=self.root_fd)
            try:
                created = os.fstat(fd)
                self.created_identity = (created.st_dev, created.st_ino)
                if os.write(fd, _DECOY_BYTES) != len(_DECOY_BYTES):
                    raise OSError("one-packet neighbor write was incomplete")
                os.fsync(fd)
            finally:
                os.close(fd)
            self.proof = _ReadDenialSentinel(self.path)
            self.revalidate()
        except BaseException:
            if self.proof is not None: self.proof.close()
            if self.root_fd is not None: os.close(self.root_fd)
            try:
                named = os.lstat(self.path)
                if ((named.st_dev, named.st_ino) == self.created_identity
                        and stat.S_ISREG(named.st_mode)):
                    self.path.unlink()
            except FileNotFoundError:
                pass
            try:
                root_now = os.lstat(self.root)
                if (root_now.st_dev, root_now.st_ino) == self.created_root_identity:
                    self.root.rmdir()
            except OSError:
                pass
            raise

    def revalidate(self):
        if self.closed: raise ValueError("one-packet neighbor is closed")
        current = os.lstat(self.root)
        frozen = self.root_identity
        if ((current.st_dev, current.st_ino, current.st_uid, current.st_mode)
                != (frozen.st_dev, frozen.st_ino, frozen.st_uid, frozen.st_mode)
                or not stat.S_ISDIR(current.st_mode)
                or stat.S_IMODE(current.st_mode) != 0o700
                or set(os.listdir(self.root_fd)) != {self.path.name}
                or self.candidate._binding_bytes() != self.binding):
            raise ValueError("one-packet neighbor root or binding changed")
        self.proof.revalidate()
        if os.pread(self.proof.file_fd, len(_DECOY_BYTES) + 1, 0) != _DECOY_BYTES:
            raise ValueError("one-packet neighbor bytes changed")
        if set(os.listdir(self.root_fd)) != {self.path.name}:
            raise ValueError("one-packet neighbor children changed")

    def finish_after_reap(self, returncode: int | None):
        if type(returncode) is not int:
            self.abandon()
            raise ValueError("one-packet neighbor cannot be cleaned before reap")
        try:
            self.revalidate()
            named = os.stat(self.path.name, dir_fd=self.root_fd,
                follow_symlinks=False)
            if ((named.st_dev, named.st_ino) != self.created_identity
                    or (named.st_dev, named.st_ino) != self.proof.frozen[:2]):
                raise ValueError("one-packet neighbor name was replaced")
            self.proof.close()
            os.unlink(self.path.name, dir_fd=self.root_fd)
            root_now = os.lstat(self.root)
            if (root_now.st_dev, root_now.st_ino) != self.created_root_identity:
                raise ValueError("one-packet neighbor root was replaced during cleanup")
            os.close(self.root_fd)
            self.root_fd = None
            self.root.rmdir()
            self.closed = True
        except BaseException:
            self.abandon()
            raise

    def abandon(self):
        if self.closed: return
        self.closed = True
        if self.proof is not None: self.proof.close()
        if self.root_fd is not None:
            os.close(self.root_fd)
            self.root_fd = None


@contextmanager
def _retain_full_set_denials(*, candidate: _BatchPolicyCandidate,
        result_bytes: bytes, index, private_packets,
        ordered_private_packet_sha256s, salt_hex, payloads,
        bundle: Path, result_path: Path):
    """Bind forbidden leaves to a validated multi-packet tree, without authority."""
    if type(candidate) is not _BatchPolicyCandidate:
        raise TypeError("full-set denial probes require a private batch candidate")
    before = candidate._binding_bytes()
    expected, snapshot, tree_sha, leaf_hashes = _derive_gate_result(
        index=index, private_packets=private_packets,
        ordered_private_packet_sha256s=ordered_private_packet_sha256s,
        salt_hex=salt_hex, payloads=payloads, bundle=bundle)
    try:
        if expected != result_bytes or len(index["packets"]) < 2:
            raise ValueError("full-set denial source is invalid")
        selected_id = json.loads(candidate._request_bytes)["packet_id"]
        ids = [item["projection"]["packet_id"] for item in index["packets"]]
        if ids.count(selected_id) != 1:
            raise ValueError("selected packet is not in the full set")
        other = next(item for item in index["packets"]
            if item["projection"]["packet_id"] != selected_id)
        neighbor_ref = other["projection"]["rows"][0]["media_ref"]
        with ExitStack() as stack:
            neighbor = stack.enter_context(_ReadDenialSentinel(bundle / neighbor_ref))
            result = stack.enter_context(_ReadDenialSentinel(result_path))
            if os.pread(result.file_fd, len(expected) + 1, 0) != expected:
                raise ValueError("full-set result leaf does not match the validated result")
            if candidate._binding_bytes() != before:
                raise ValueError("selected packet binding changed during denial setup")
            yield neighbor, result
            neighbor.revalidate()
            result.revalidate()
            if (snapshot.leaf_hashes() != leaf_hashes
                    or snapshot.digest() != tree_sha
                    or candidate._binding_bytes() != before):
                raise ValueError("full-set denial source changed during probe")
    finally:
        snapshot.close()


def _run_owned_full_set_batch_probe(*, candidate, batch_scratch, outside,
        scratch, listeners, repository, protocol, denial_source):
    """Own full-set proof exit, candidate closure, then exact batch cleanup."""
    from dataclasses import replace
    from .sparse_story_probe_context import _ProbeContext
    from .sparse_story_probe_listeners import _OwnedProbeListeners
    from .sparse_story_probe_sentinels import (
        _OwnedBatchScratch, _OwnedOutsideSentinel, _OwnedScratchProbeFiles,
    )
    from .sparse_story_raw_probe_transport import _run_owned_raw_probe

    if (type(candidate) is not _BatchPolicyCandidate
            or type(batch_scratch) is not _OwnedBatchScratch
            or batch_scratch.bound_candidate is not candidate
            or type(outside) is not _OwnedOutsideSentinel
            or type(scratch) is not _OwnedScratchProbeFiles
            or type(listeners) is not _OwnedProbeListeners
            or type(repository) is not _ReadDenialSentinel
            or type(protocol) is not _ReadDenialSentinel
            or type(denial_source) is not dict
            or set(denial_source) != {"result_bytes", "index", "private_packets",
                "ordered_private_packet_sha256s", "salt_hex", "payloads",
                "bundle", "result_path"}):
        raise TypeError("full-set batch probe requires exact private owners")
    capture = None
    try:
        with _retain_full_set_denials(candidate=candidate, **denial_source) as (
                neighbor, result):
            context = _ProbeContext(candidate=candidate, repository=repository,
                protocol=protocol, neighbor=neighbor, result=result,
                outside=outside.snapshot, scratch=scratch.snapshot,
                listeners=listeners.listeners)
            capture = _run_owned_raw_probe(context, outside=outside, scratch=scratch,
                listeners=listeners)
    except BaseException:
        try:
            candidate.close()
        finally:
            for owner in (outside, scratch, listeners, batch_scratch):
                owner.abandon()
        raise
    try:
        candidate.close()
    except BaseException:
        batch_scratch.abandon()
        raise
    try:
        batch_scratch.finish_after_candidate_close(candidate, capture)
    except (OSError, ValueError):
        return replace(capture, completed=False, reason="batch_scratch_cleanup_invalid")
    return capture


class _RetainedProbedBatch:
    """Private probe result retaining its exact batch until terminal closure.

    This is deliberately not an invocation token or capability receipt.
    """

    def __init__(self, candidate, batch_scratch, capture, binding, receipt_bytes,
                 probe_prefixes):
        self._candidate = candidate
        self._batch_scratch = batch_scratch
        self._capture = capture
        self._binding = binding
        self._receipt_bytes = receipt_bytes
        self._probe_prefixes = probe_prefixes
        self._closed = False
        self._claimed = False
        self._invocation_started = False
        self._invocation_capture = None

    def revalidate(self):
        if self._closed or not self._capture.completed:
            raise ValueError("retained probe session is inactive")
        if (self._candidate._closed or self._batch_scratch.closed
                or self._batch_scratch.bound_candidate is not self._candidate
                or self._candidate._binding_bytes() != self._binding):
            raise ValueError("retained probe batch changed")
        if _rebuild_private_probe_receipt(self._candidate, self._capture,
                self._probe_prefixes) != self._receipt_bytes:
            raise ValueError("retained probe receipt changed")
        self._batch_scratch.revalidate()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if (self._invocation_started
                and (self._invocation_capture is None
                     or self._invocation_capture.group_gone is not True
                     or type(self._invocation_capture.returncode) is not int)):
            try: self._candidate.close()
            finally: self._batch_scratch.abandon()
            raise ValueError("inference group absence is unverified")
        try:
            self._candidate.close()
        except BaseException:
            self._batch_scratch.abandon()
            raise
        self._batch_scratch.finish_after_candidate_close(
            self._candidate, self._capture)

    def claim_once(self):
        """Consume the private batch claim before any future invocation work."""
        if self._claimed:
            raise ValueError("retained probe batch was already claimed")
        self.revalidate()
        self._claimed = True
        return _ClaimedProbedBatch(_CLAIM_FACTORY_TOKEN, self)

    def __enter__(self):
        self.revalidate()
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()


class _ClaimedProbedBatch:
    """Non-transferable private claim; it has no spawn or receipt method."""

    def __init__(self, token, session):
        if (token is not _CLAIM_FACTORY_TOKEN
                or type(session) is not _RetainedProbedBatch
                or not session._claimed):
            raise TypeError("claim requires a consumed retained session")
        self._session = session
        self._invoked = False

    def revalidate(self):
        if not self._session._claimed:
            raise ValueError("retained claim is inactive")
        self._session.revalidate()

    def receipt_bytes(self):
        self.revalidate()
        return self._session._receipt_bytes

    def _run_fixed_synthetic_fd_case_once(self):
        """Exercise one closed fixture case; no general adapter invocation API."""
        return self._run_fixed_synthetic_case_once("fd_hygiene", b"")

    def _run_fixed_synthetic_pipe_case_once(self):
        """Exercise bounded simultaneous stdout and request transfer."""
        return self._run_fixed_synthetic_case_once(
            "concurrent_pipe_pressure", b"x" * 60_000)

    def _run_fixed_synthetic_scratch_case_once(self):
        """Exercise and remove one exact fixture-created scratch leaf."""
        return self._run_fixed_synthetic_case_once("scratch_write_allowed", b"")

    def _run_fixed_synthetic_case_once(self, case_id, request_bytes):
        capture = self._execute_fixed_synthetic_case_once(case_id, request_bytes)
        if capture.completed:
            from .sparse_story_semantics import _strict_raw
            _strict_raw(capture.stdout)
        return capture

    def _observe_fixed_synthetic_output_case_once(self, case_id):
        """Classify a closed fixture stdout case from observed bytes and status."""
        allowed = {"stdout_empty", "stdout_invalid_utf8",
            "stdout_duplicate_key", "stdout_nan", "stdout_trailing_bytes",
            "stdout_forbidden_field", "stdout_extra_field",
            "stdout_limit_minus_one", "stdout_limit_exact",
            "stdout_limit_plus_one", "stderr_nonempty", "nonzero_exit",
            "signal_exit", "wall_timeout", "term_ignore_kill"}
        if case_id not in allowed:
            raise ValueError("fixed synthetic output case is invalid")
        capture = self._execute_fixed_synthetic_case_once(case_id, b"")
        return _classify_fixed_synthetic_output(capture)

    def _observe_fixed_synthetic_identity_case_once(self, case_id):
        if case_id not in {"argv_literal", "environment_exact", "cwd_identity",
                "fd_hygiene"}:
            raise ValueError("fixed synthetic identity case is invalid")
        capture = self._execute_fixed_synthetic_case_once(case_id, b"")
        return _classify_fixed_synthetic_output(capture)

    def _observe_fixed_synthetic_network_case_once(self, case_id):
        if case_id not in {"network_ipv4_denied", "network_ipv6_denied",
                "unix_socket_denied"}:
            raise ValueError("fixed synthetic network case is invalid")
        capture = self._execute_fixed_synthetic_case_once(case_id, b"")
        return ("isolation_denied" if _classify_fixed_synthetic_output(capture)
            == "success" else "invocation_failure")

    def _observe_fixed_synthetic_denial_case_once(self, case_id):
        if case_id not in {"grandchild_containment", "outside_write_denied",
                "repository_read_denied", "protocol_read_denied"}:
            raise ValueError("fixed synthetic denial case is invalid")
        capture = self._execute_fixed_synthetic_case_once(case_id, b"")
        return ("isolation_denied" if _classify_fixed_synthetic_output(capture)
            == "success" else "invocation_failure")

    def _observe_fixed_fullset_read_denial_once(self, case_id, denial_source):
        """Probe an actual other-packet or full-result leaf from the same set."""
        from .sparse_story_raw_probe_transport import _run_native_process
        if case_id not in {"neighbor_packet_read_denied", "result_read_denied"}:
            raise ValueError("fixed full-set read case is invalid")
        if self._invoked:
            raise ValueError("private batch claim was already invoked")
        self.revalidate()
        candidate = self._session._candidate
        with _retain_full_set_denials(candidate=candidate, **denial_source) as (
                neighbor, result):
            target = neighbor if case_id == "neighbor_packet_read_denied" else result
            self._invoked = True
            self._session._invocation_started = True
            def postvalidate():
                self.revalidate()
                neighbor.revalidate()
                result.revalidate()
            capture = _run_native_process(candidate,
                ("--aegis-synthetic-case", case_id, "--", str(target.path)),
                postvalidate=postvalidate, request_bytes=b"")
            self._session._invocation_capture = capture
        self.revalidate()
        return ("isolation_denied" if _classify_fixed_synthetic_output(capture)
            == "success" else "invocation_failure")

    def _observe_fixed_allowed_read_once(self, case_id):
        """Read a request-selected retained leaf using its exact byte prefix."""
        from .sparse_story_raw_probe_transport import _run_native_process
        selected = {"bundle_read_allowed": 0, "model_read_allowed": 1,
            "prompt_read_allowed": 2}
        if case_id not in selected:
            raise ValueError("fixed allowed-read case is invalid")
        if self._invoked:
            raise ValueError("private batch claim was already invoked")
        self.revalidate()
        candidate = self._session._candidate
        allowed = candidate._allowed_probe_leaves()
        leaf = allowed[selected[case_id]]
        self._invoked = True
        self._session._invocation_started = True
        def postvalidate():
            self.revalidate()
            if candidate._allowed_probe_leaves() != allowed:
                raise ValueError("allowed read leaf changed")
        capture = _run_native_process(candidate,
            ("--aegis-synthetic-case", case_id, "--", str(leaf.path),
                "hex:" + leaf.prefix.hex()),
            postvalidate=postvalidate, request_bytes=b"")
        self._session._invocation_capture = capture
        self.revalidate()
        return ("isolation_allowed" if _classify_fixed_synthetic_output(capture)
            == "success" else "invocation_failure")

    def _execute_fixed_synthetic_case_once(self, case_id, request_bytes):
        from . import sparse_story_batch_policy as batch_policy
        from .sparse_story_raw_probe_transport import _run_native_process

        if ((case_id, request_bytes) not in
                (("fd_hygiene", b""),
                 ("concurrent_pipe_pressure", b"x" * 60_000),
                 ("scratch_write_allowed", b""))
                and (case_id not in {"grandchild_containment",
                    "outside_write_denied", "repository_read_denied",
                    "protocol_read_denied", "network_ipv4_denied",
                    "network_ipv6_denied", "unix_socket_denied",
                    "argv_literal", "environment_exact",
                    "cwd_identity", "stdout_empty", "stdout_invalid_utf8",
                    "stdout_duplicate_key", "stdout_nan", "stdout_trailing_bytes",
                    "stdout_forbidden_field", "stdout_extra_field",
                    "stdout_limit_minus_one", "stdout_limit_exact",
                    "stdout_limit_plus_one", "stderr_nonempty", "nonzero_exit",
                    "signal_exit", "wall_timeout", "term_ignore_kill"}
                    or request_bytes != b"")):
            raise ValueError("fixed synthetic case is invalid")
        if self._invoked:
            raise ValueError("private batch claim was already invoked")
        self.revalidate()
        candidate = self._session._candidate
        live = batch_policy._require_live(candidate._facade)
        if live._adapter_binding._runtime._entrypoint != "bin/aegis-synthetic-adapter":
            raise ValueError("fixed synthetic case requires the fixture runtime")
        scratch_owner = self._session._batch_scratch
        scratch_path = scratch_owner.root / "synthetic-write"
        network_case = case_id in {"network_ipv4_denied",
            "network_ipv6_denied", "unix_socket_denied"}
        listener_owner = None
        outside_owner = None
        read_owner = None
        if network_case:
            from .sparse_story_probe_listeners import _OwnedProbeListeners
            listener_owner = _OwnedProbeListeners(scratch_owner.root.parent)
        if case_id == "outside_write_denied":
            from .sparse_story_probe_sentinels import _OwnedOutsideSentinel
            outside_owner = _OwnedOutsideSentinel(scratch_owner.root.parent)
        if case_id in {"repository_read_denied", "protocol_read_denied"}:
            from .sparse_story_probe_context import (
                _PROTOCOL_SENTINEL, _REPOSITORY_SENTINEL,
            )
            from .sparse_story_probe_sentinels import _ReadDenialSentinel
            read_owner = _ReadDenialSentinel(_REPOSITORY_SENTINEL
                if case_id == "repository_read_denied" else _PROTOCOL_SENTINEL)
        if case_id == "scratch_write_allowed":
            try: os.lstat(scratch_path)
            except FileNotFoundError: pass
            else: raise ValueError("fixed synthetic scratch target already exists")
        self._invoked = True
        suffix = ("--aegis-synthetic-case", case_id, "--")
        if case_id == "scratch_write_allowed":
            suffix += (str(scratch_path),)
        elif case_id == "argv_literal":
            suffix += (";$(touch should-not-run)", "* ' \" \\")
        elif case_id == "environment_exact":
            suffix += (candidate._private_home.identity.path,
                candidate._private_tmpdir.identity.path)
        elif case_id == "cwd_identity":
            suffix += (str(candidate._proofs[0]._root),)
        elif network_case:
            listeners = listener_owner.listeners
            suffix += (str(listeners.ipv4_port) if case_id == "network_ipv4_denied"
                else str(listeners.ipv6_port) if case_id == "network_ipv6_denied"
                else str(listeners.unix_path),)
        elif case_id == "outside_write_denied":
            suffix += (str(outside_owner.snapshot.create_path),)
        elif read_owner is not None:
            suffix += (str(read_owner.path),)
        elif case_id == "grandchild_containment":
            suffix += (str(scratch_owner.root / "grandchild-marker"),)
        self._session._invocation_started = True
        def postvalidate():
            if case_id == "scratch_write_allowed":
                candidate._binding_bytes()
            else:
                self.revalidate()
            if listener_owner is not None: listener_owner.revalidate()
            if outside_owner is not None: outside_owner.revalidate()
            if read_owner is not None: read_owner.revalidate()
        try:
            capture = _run_native_process(candidate, suffix,
                postvalidate=postvalidate, request_bytes=request_bytes)
        except BaseException:
            if listener_owner is not None: listener_owner.abandon()
            if outside_owner is not None: outside_owner.abandon()
            if read_owner is not None: read_owner.close()
            raise
        self._session._invocation_capture = capture
        if listener_owner is not None:
            if capture.group_gone and type(capture.returncode) is int:
                listener_owner.finish_after_reap(capture.returncode)
            else:
                listener_owner.abandon()
        if outside_owner is not None:
            if capture.group_gone and type(capture.returncode) is int:
                outside_owner.finish_after_reap(capture.returncode)
            else:
                outside_owner.abandon()
        if read_owner is not None:
            try: read_owner.revalidate()
            finally: read_owner.close()
        if case_id == "scratch_write_allowed":
            if not capture.completed or not capture.group_gone:
                return capture
            _clean_fixed_synthetic_scratch(scratch_owner)
        self.revalidate()
        return capture

    def __copy__(self):
        raise TypeError("private batch claims cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("private batch claims cannot be copied")

    def __reduce__(self):
        raise TypeError("private batch claims cannot be pickled")


_CLAIM_FACTORY_TOKEN = object()


def _classify_fixed_synthetic_output(capture):
    from collections.abc import Mapping
    from .sparse_story_raw_probe_transport import _RawProbeCapture
    from .sparse_story_semantics import _decode_raw, validate_raw_observation

    if type(capture) is not _RawProbeCapture:
        raise TypeError("synthetic output classification requires native capture")
    if not capture.completed:
        return "invocation_failure"
    try: parsed = _decode_raw(capture.stdout)
    except ValueError:
        return "malformed_json"
    if not isinstance(parsed, Mapping):
        return "schema_violation"
    from .sparse_story_semantics import FIELDS
    if set(parsed) != set(FIELDS):
        return "forbidden_field" if set(parsed) - set(FIELDS) else "schema_violation"
    try: validate_raw_observation(parsed)
    except ValueError:
        return "schema_violation"
    return "success"


def _rebuild_private_probe_receipt(candidate, capture, prefixes):
    from .sparse_story_probe_transcript import (
        _check_probe_row_values, parse_isolation_probe_transcript,
    )
    from .sparse_story_raw_probe_transport import _RawProbeCapture
    from .sparse_story_runner_contract import (
        CAPABILITY_SCHEMA, MATRIX_KEYS, canonical_capability_receipt_shape_bytes,
    )
    import hashlib

    if (type(candidate) is not _BatchPolicyCandidate
            or type(capture) is not _RawProbeCapture or not capture.completed
            or capture.group_gone is not True or capture.postcheck_passed is not True
            or capture.returncode != 0 or type(prefixes) is not tuple
            or len(prefixes) != 3 or any(type(value) is not bytes for value in prefixes)):
        raise ValueError("private probe receipt inputs are invalid")
    rows = parse_isolation_probe_transcript(capture.stdout)
    matrix = _check_probe_row_values(rows, bundle_prefix=prefixes[0],
        model_prefix=prefixes[1], prompt_prefix=prefixes[2])
    if (set(matrix) != set(MATRIX_KEYS)
            or any(matrix[key] is not True for key in MATRIX_KEYS)):
        raise ValueError("retained probe matrix is incomplete")
    return canonical_capability_receipt_shape_bytes({
        "schema_version": CAPABILITY_SCHEMA,
        "backend_manifest_sha256": hashlib.sha256(candidate._backend_bytes).hexdigest(),
        "compiled_policy_sha256": hashlib.sha256(candidate._policy_bytes()).hexdigest(),
        "runner_policy_sha256": hashlib.sha256(
            candidate._runner_policy_bytes).hexdigest(),
        "matrix": matrix,
    })


def _clean_fixed_synthetic_scratch(owner):
    """Remove only the exact verified fixture leaf after group absence."""
    from .sparse_story_probe_sentinels import _OwnedBatchScratch, _file_facts
    if type(owner) is not _OwnedBatchScratch or owner.closed:
        raise ValueError("fixed synthetic scratch owner is invalid")
    root = os.lstat(owner.root)
    if ((root.st_dev, root.st_ino) != owner.root_identity
            or set(os.listdir(owner.root_fd)) != {"home", "tmp", "synthetic-write"}):
        raise ValueError("fixed synthetic scratch tree changed")
    fd = os.open("synthetic-write", os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
        dir_fd=owner.root_fd)
    try:
        value = os.fstat(fd)
        named = os.stat("synthetic-write", dir_fd=owner.root_fd,
            follow_symlinks=False)
        facts = _file_facts(value)
        marker = b"synthetic-scratch-write-v1"
        if (facts != _file_facts(named) or not stat.S_ISREG(value.st_mode)
                or stat.S_IMODE(value.st_mode) != 0o600
                or value.st_uid != os.getuid() or value.st_nlink != 1
                or value.st_size != len(marker)
                or os.pread(fd, len(marker) + 1, 0) != marker):
            raise ValueError("fixed synthetic scratch leaf changed")
    finally:
        os.close(fd)
    if (_file_facts(os.stat("synthetic-write", dir_fd=owner.root_fd,
            follow_symlinks=False)) != facts
            or (os.lstat(owner.root).st_dev, os.lstat(owner.root).st_ino)
               != owner.root_identity):
        raise ValueError("fixed synthetic scratch cleanup target changed")
    os.unlink("synthetic-write", dir_fd=owner.root_fd)


def _open_retained_probed_batch(*, candidate, batch_scratch, outside,
        scratch, listeners, repository, protocol, denial_source):
    """Run one raw probe and retain only a fully validated batch candidate."""
    from .sparse_story_probe_context import _ProbeContext
    from .sparse_story_probe_listeners import _OwnedProbeListeners
    from .sparse_story_probe_sentinels import (
        _OwnedBatchScratch, _OwnedOutsideSentinel, _OwnedScratchProbeFiles,
    )
    from .sparse_story_raw_probe_transport import _run_owned_raw_probe

    if (type(candidate) is not _BatchPolicyCandidate
            or type(batch_scratch) is not _OwnedBatchScratch
            or batch_scratch.bound_candidate is not candidate
            or type(outside) is not _OwnedOutsideSentinel
            or type(scratch) is not _OwnedScratchProbeFiles
            or type(listeners) is not _OwnedProbeListeners
            or type(repository) is not _ReadDenialSentinel
            or type(protocol) is not _ReadDenialSentinel
            or type(denial_source) is not dict
            or set(denial_source) != {"result_bytes", "index", "private_packets",
                "ordered_private_packet_sha256s", "salt_hex", "payloads",
                "bundle", "result_path"}):
        raise TypeError("retained batch probe requires exact private owners")
    capture = None
    try:
        with _retain_full_set_denials(candidate=candidate, **denial_source) as (
                neighbor, result):
            context = _ProbeContext(candidate=candidate, repository=repository,
                protocol=protocol, neighbor=neighbor, result=result,
                outside=outside.snapshot, scratch=scratch.snapshot,
                listeners=listeners.listeners)
            capture = _run_owned_raw_probe(context, outside=outside,
                scratch=scratch, listeners=listeners)
        if not capture.completed:
            raise ValueError("retained batch raw probe is incomplete")
        binding = candidate._binding_bytes()
        batch_scratch.revalidate()
        bundle, model, prompt = context.allowed
        prefixes = (bundle.prefix, model.prefix, prompt.prefix)
        receipt_bytes = _rebuild_private_probe_receipt(candidate, capture, prefixes)
        session = _RetainedProbedBatch(candidate, batch_scratch, capture, binding,
            receipt_bytes, prefixes)
        session.revalidate()
        return session
    except BaseException:
        try:
            candidate.close()
        finally:
            for owner in (outside, scratch, listeners):
                owner.abandon()
            if (capture is not None and type(capture.returncode) is int
                    and capture.group_gone is True):
                try:
                    batch_scratch.finish_after_candidate_close(candidate, capture)
                except (OSError, ValueError):
                    batch_scratch.abandon()
            else:
                batch_scratch.abandon()
        raise
