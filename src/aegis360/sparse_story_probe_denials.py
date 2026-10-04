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

    def __init__(self, candidate, batch_scratch, capture, binding, receipt_bytes):
        self._candidate = candidate
        self._batch_scratch = batch_scratch
        self._capture = capture
        self._binding = binding
        self._receipt_bytes = receipt_bytes
        self._closed = False
        self._claimed = False

    def revalidate(self):
        if self._closed or not self._capture.completed:
            raise ValueError("retained probe session is inactive")
        if (self._candidate._closed or self._batch_scratch.closed
                or self._batch_scratch.bound_candidate is not self._candidate
                or self._candidate._binding_bytes() != self._binding):
            raise ValueError("retained probe batch changed")
        self._batch_scratch.revalidate()

    def close(self):
        if self._closed:
            return
        self._closed = True
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

    def revalidate(self):
        if not self._session._claimed:
            raise ValueError("retained claim is inactive")
        self._session.revalidate()

    def receipt_bytes(self):
        self.revalidate()
        return self._session._receipt_bytes

    def __copy__(self):
        raise TypeError("private batch claims cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("private batch claims cannot be copied")

    def __reduce__(self):
        raise TypeError("private batch claims cannot be pickled")


_CLAIM_FACTORY_TOKEN = object()


def _open_retained_probed_batch(*, candidate, batch_scratch, outside,
        scratch, listeners, repository, protocol, denial_source):
    """Run one raw probe and retain only a fully validated batch candidate."""
    from .sparse_story_probe_context import _ProbeContext
    from .sparse_story_probe_listeners import _OwnedProbeListeners
    from .sparse_story_probe_sentinels import (
        _OwnedBatchScratch, _OwnedOutsideSentinel, _OwnedScratchProbeFiles,
    )
    from .sparse_story_raw_probe_transport import _run_owned_raw_probe
    from .sparse_story_probe_transcript import (
        _check_probe_row_values, parse_isolation_probe_transcript,
    )
    from .sparse_story_runner_contract import (
        CAPABILITY_SCHEMA, MATRIX_KEYS, canonical_capability_receipt_shape_bytes,
    )
    import hashlib

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
        rows = parse_isolation_probe_transcript(capture.stdout)
        bundle, model, prompt = context.allowed
        matrix = _check_probe_row_values(rows,
            bundle_prefix=bundle.prefix, model_prefix=model.prefix,
            prompt_prefix=prompt.prefix)
        if (set(matrix) != set(MATRIX_KEYS)
                or any(matrix[key] is not True for key in MATRIX_KEYS)):
            raise ValueError("retained probe matrix is incomplete")
        receipt_bytes = canonical_capability_receipt_shape_bytes({
            "schema_version": CAPABILITY_SCHEMA,
            "backend_manifest_sha256": hashlib.sha256(
                candidate._backend_bytes).hexdigest(),
            "compiled_policy_sha256": hashlib.sha256(
                candidate._policy_bytes()).hexdigest(),
            "runner_policy_sha256": hashlib.sha256(
                candidate._runner_policy_bytes).hexdigest(),
            "matrix": matrix,
        })
        session = _RetainedProbedBatch(candidate, batch_scratch, capture, binding,
            receipt_bytes)
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
