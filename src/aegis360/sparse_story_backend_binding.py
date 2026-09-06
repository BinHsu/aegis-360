"""Private live binding of retained launcher and macOS backend proofs."""

from __future__ import annotations

import hashlib
import re

from .sparse_story_asset_tree import _AssetTreeProof
from .sparse_story_os_backend import _OSBackendProof
from .sparse_story_runner_contract import (
    build_seatbelt_backend_manifest_shape,
    canonical_asset_manifest_shape_bytes,
    canonical_seatbelt_backend_manifest_shape_bytes,
)

_TOKEN = object()
_SHA = re.compile(r"^[0-9a-f]{64}$")
_ENTRYPOINT = "bin/aegis-sparse-story-launcher"


def _close_pair(runtime, backend):
    error = None
    for proof, expected_type in ((runtime, _AssetTreeProof), (backend, _OSBackendProof)):
        if type(proof) is expected_type:
            try:
                proof.close()
            except BaseException as caught:
                if error is None:
                    error = caught
    return error


class _BackendBinding:
    def __init__(self, token, *, backend, runtime, expected_runtime_sha, frozen_bytes):
        if token is not _TOKEN:
            raise TypeError("backend bindings cannot be constructed by callers")
        self._backend = backend
        self._runtime = runtime
        self._expected_runtime_sha = expected_runtime_sha
        self._frozen_bytes = frozen_bytes
        self._closed = False

    def canonical_bytes(self) -> bytes:
        if self._closed:
            raise ValueError("backend binding is closed")
        current = _derive_bytes(self._backend, self._runtime,
                                self._expected_runtime_sha)
        if current != self._frozen_bytes:
            raise ValueError("backend binding changed")
        return bytes(current)

    def close(self):
        if self._closed:
            return
        self._closed = True
        error = _close_pair(self._runtime, self._backend)
        if error is not None:
            raise error

    def __enter__(self):
        self.canonical_bytes()
        return self

    def __exit__(self, *_):
        self.close()

    def __copy__(self): raise TypeError("backend bindings cannot be copied")
    def __deepcopy__(self, _memo): raise TypeError("backend bindings cannot be copied")
    def __reduce__(self): raise TypeError("backend bindings cannot be pickled")


def _derive_bytes(backend, runtime, expected_runtime_sha):
    if type(backend) is not _OSBackendProof or type(runtime) is not _AssetTreeProof:
        raise TypeError("exact production retained proofs are required")
    if (runtime._closed or runtime._asset_kind != "runtime"
            or runtime._entrypoint != _ENTRYPOINT):
        raise ValueError("launcher runtime proof is invalid")
    runtime_manifest = runtime.manifest()
    runtime_bytes = canonical_asset_manifest_shape_bytes(runtime_manifest)
    runtime_sha = hashlib.sha256(runtime_bytes).hexdigest()
    if runtime_sha != expected_runtime_sha:
        raise ValueError("launcher runtime manifest does not match precommit")
    os_build, backend_hash, backend_size, system_hash = backend._manifest_facts()
    shape = build_seatbelt_backend_manifest_shape(os_build=os_build,
        architecture="arm64", backend_executable_sha256=backend_hash,
        backend_executable_size=backend_size,
        launcher_runtime_manifest_sha256=runtime_sha,
        system_version_sha256=system_hash)
    return canonical_seatbelt_backend_manifest_shape_bytes(shape)


def _bind_backend(*, os_backend_proof, launcher_runtime_proof,
                  expected_launcher_manifest_sha256):
    """Consume two live production proofs into one private binding."""
    if (not isinstance(expected_launcher_manifest_sha256, str)
            or _SHA.fullmatch(expected_launcher_manifest_sha256) is None):
        failure = ValueError("expected launcher manifest SHA-256 is invalid")
        cleanup_error = _close_pair(launcher_runtime_proof, os_backend_proof)
        if cleanup_error is not None:
            raise cleanup_error from failure
        raise failure
    try:
        frozen = _derive_bytes(os_backend_proof, launcher_runtime_proof,
                               expected_launcher_manifest_sha256)
        return _BackendBinding(_TOKEN, backend=os_backend_proof,
            runtime=launcher_runtime_proof,
            expected_runtime_sha=expected_launcher_manifest_sha256,
            frozen_bytes=frozen)
    except BaseException as failure:
        cleanup_error = _close_pair(launcher_runtime_proof, os_backend_proof)
        if cleanup_error is not None:
            raise cleanup_error from failure
        raise
