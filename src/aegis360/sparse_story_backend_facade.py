"""Conservative coordinator provenance facade for the retained Seatbelt binding."""

from __future__ import annotations

import hashlib
import weakref
from pathlib import Path
from typing import Mapping

from .sparse_story_asset_tree import _AssetTreeProof, validate_asset_tree
from .sparse_story_backend_binding import _bind_backend
from .sparse_story_os_backend import _observe_os_backend
from .sparse_story_runner_contract import canonical_asset_manifest_shape_bytes

_TOKEN = object()
_LIVE = weakref.WeakKeyDictionary()
_CLOSED = weakref.WeakSet()
_MISSING = object()
_FORBIDDEN_EXEC_SENTINEL_ENTRYPOINT = "bin/aegis-forbidden-exec-sentinel"


def _close_children(*children):
    first = None
    for child in children:
        if child is None:
            continue
        try:
            child.close()
        except BaseException as error:
            if first is None:
                first = error
    return first


def _asset_identity(proof):
    """Return a private retained-tree identity only for a real production proof."""
    if type(proof) is _AssetTreeProof:
        return proof.backend_identity()
    return None


def _same_retained_asset(first, second) -> bool:
    """Compare private proof facts without publishing a path, descriptor or digest."""
    if first is None or second is None:
        return False
    return first[:2] == second[:2] or first[2] == second[2]


class _AdapterRuntimeBinding:
    """Private retained adapter runtime; it deliberately exports no execution handle."""

    def __init__(self, token, *, runtime, expected_manifest_bytes, entrypoint):
        if token is not _TOKEN:
            raise TypeError("adapter runtime bindings cannot be constructed by callers")
        self._runtime = runtime
        self._expected_manifest_bytes = expected_manifest_bytes
        self._entrypoint = entrypoint
        self._closed = False

    def revalidate(self) -> None:
        if self._closed:
            raise ValueError("adapter runtime binding is closed")
        manifest = self._runtime.manifest()
        current = canonical_asset_manifest_shape_bytes(manifest)
        if (manifest.get("entrypoint") != self._entrypoint
                or current != self._expected_manifest_bytes):
            raise ValueError("adapter runtime manifest changed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._runtime.close()

    def __copy__(self):
        raise TypeError("adapter runtime bindings cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("adapter runtime bindings cannot be copied")

    def __reduce__(self):
        raise TypeError("adapter runtime bindings cannot be pickled")


def _bind_adapter_runtime(*, adapter_runtime_proof,
                          expected_adapter_manifest_bytes: bytes):
    """Consume the exact retained runtime proof without exposing its entrypoint."""
    failure = None
    try:
        if type(adapter_runtime_proof) is not _AssetTreeProof:
            raise TypeError("exact production adapter runtime proof is required")
        if (not isinstance(expected_adapter_manifest_bytes, bytes)
                or not expected_adapter_manifest_bytes):
            raise ValueError("adapter runtime precommit is invalid")
        manifest = adapter_runtime_proof.manifest()
        if (manifest.get("asset_kind") != "runtime"
                or not isinstance(manifest.get("entrypoint"), str)
                or canonical_asset_manifest_shape_bytes(manifest)
                != expected_adapter_manifest_bytes):
            raise ValueError("adapter runtime manifest does not match precommit")
        # Asset-tree revalidation reaches the single declared entrypoint through
        # its retained descriptor and validates its Darwin arm64 Mach-O shape.
        return _AdapterRuntimeBinding(_TOKEN, runtime=adapter_runtime_proof,
            expected_manifest_bytes=expected_adapter_manifest_bytes,
            entrypoint=manifest["entrypoint"])
    except BaseException as caught:
        failure = caught
    try:
        if type(adapter_runtime_proof) is _AssetTreeProof:
            adapter_runtime_proof.close()
    except BaseException as cleanup:
        raise cleanup from failure
    raise failure


class _ForbiddenExecSentinelBinding:
    """Private retained sentinel runtime; it deliberately exports no handle."""

    def __init__(self, token, *, runtime, expected_manifest_bytes):
        if token is not _TOKEN:
            raise TypeError("forbidden-exec sentinel bindings cannot be constructed by callers")
        self._runtime = runtime
        self._expected_manifest_bytes = expected_manifest_bytes
        self._closed = False

    def revalidate(self) -> None:
        if self._closed:
            raise ValueError("forbidden-exec sentinel binding is closed")
        manifest = self._runtime.manifest()
        current = canonical_asset_manifest_shape_bytes(manifest)
        if (manifest.get("asset_kind") != "runtime"
                or manifest.get("entrypoint") != _FORBIDDEN_EXEC_SENTINEL_ENTRYPOINT
                or current != self._expected_manifest_bytes):
            raise ValueError("forbidden-exec sentinel manifest changed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._runtime.close()

    def __copy__(self):
        raise TypeError("forbidden-exec sentinel bindings cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("forbidden-exec sentinel bindings cannot be copied")

    def __reduce__(self):
        raise TypeError("forbidden-exec sentinel bindings cannot be pickled")


def _bind_forbidden_exec_sentinel(*, sentinel_runtime_proof,
                                  expected_sentinel_manifest_bytes: bytes):
    """Consume the exact retained sentinel proof without exposing its entrypoint."""
    failure = None
    try:
        if type(sentinel_runtime_proof) is not _AssetTreeProof:
            raise TypeError("exact production forbidden-exec sentinel proof is required")
        if (not isinstance(expected_sentinel_manifest_bytes, bytes)
                or not expected_sentinel_manifest_bytes):
            raise ValueError("forbidden-exec sentinel precommit is invalid")
        manifest = sentinel_runtime_proof.manifest()
        if (manifest.get("asset_kind") != "runtime"
                or manifest.get("entrypoint") != _FORBIDDEN_EXEC_SENTINEL_ENTRYPOINT
                or canonical_asset_manifest_shape_bytes(manifest)
                != expected_sentinel_manifest_bytes):
            raise ValueError("forbidden-exec sentinel manifest does not match precommit")
        # Asset-tree revalidation reaches the only permitted sentinel entrypoint
        # through its retained descriptor and validates its Darwin arm64 Mach-O shape.
        return _ForbiddenExecSentinelBinding(
            _TOKEN, runtime=sentinel_runtime_proof,
            expected_manifest_bytes=expected_sentinel_manifest_bytes)
    except BaseException as caught:
        failure = caught
    try:
        if type(sentinel_runtime_proof) is _AssetTreeProof:
            sentinel_runtime_proof.close()
    except BaseException as cleanup:
        raise cleanup from failure
    raise failure


class _LiveFacadeBinding:
    """Private retained bindings whose public bytes expose no runtime handles."""

    def __init__(self, token, *, backend_binding, adapter_binding, sentinel_binding):
        if token is not _TOKEN:
            raise TypeError("live facade bindings cannot be constructed by callers")
        self._backend_binding = backend_binding
        self._adapter_binding = adapter_binding
        self._sentinel_binding = sentinel_binding
        self._closed = False

    def canonical_bytes(self) -> bytes:
        if self._closed:
            raise ValueError("live facade binding is closed")
        self._sentinel_binding.revalidate()
        self._adapter_binding.revalidate()
        return self._backend_binding.canonical_bytes()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        error = _close_children(self._sentinel_binding, self._adapter_binding,
                                self._backend_binding)
        if error is not None:
            raise error


def _require_live(value):
    if type(value) is not SeatbeltBackendBinding:
        raise ValueError("Seatbelt backend binding facade is not live")
    binding = _LIVE.get(value, _MISSING)
    if binding is _MISSING:
        raise ValueError("Seatbelt backend binding facade is not live")
    return binding


class SeatbeltBackendBinding:
    """Opaque live facade; only the module factory may register an instance."""

    __slots__ = ("__weakref__",)

    def __init_subclass__(cls, **kwargs):
        raise TypeError("Seatbelt backend binding facades cannot be subclassed")

    def __init__(self, token, binding):
        if token is not _TOKEN:
            raise TypeError("Seatbelt backend binding facades require the factory")
        if binding is None:
            raise TypeError("Seatbelt backend binding is required")

    def canonical_manifest_bytes(self) -> bytes:
        return _require_live(self).canonical_bytes()

    def close(self) -> None:
        if type(self) is not SeatbeltBackendBinding:
            raise ValueError("Seatbelt backend binding facade is not live")
        if self in _CLOSED:
            return
        binding = _LIVE.pop(self, _MISSING)
        if binding is _MISSING:
            raise ValueError("Seatbelt backend binding facade is not live")
        _CLOSED.add(self)
        binding.close()

    def __enter__(self):
        _require_live(self)
        return self

    def __exit__(self, *_):
        self.close()

    def __copy__(self):
        raise TypeError("Seatbelt backend binding facades cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("Seatbelt backend binding facades cannot be copied")

    def __reduce__(self):
        raise TypeError("Seatbelt backend binding facades cannot be pickled")


def open_seatbelt_backend_binding(*, launcher_root: Path,
                                  precommitted_launcher_manifest: Mapping,
                                  adapter_runtime_root: Path,
                                  precommitted_adapter_runtime_manifest: Mapping,
                                  forbidden_exec_sentinel_runtime_root: Path,
                                  precommitted_forbidden_exec_sentinel_manifest: Mapping):
    """Open private bindings from precommitted launcher, adapter and sentinel runtimes."""
    if not isinstance(launcher_root, Path) or not isinstance(
            precommitted_launcher_manifest, Mapping) or not isinstance(
            adapter_runtime_root, Path) or not isinstance(
            precommitted_adapter_runtime_manifest, Mapping) or not isinstance(
            forbidden_exec_sentinel_runtime_root, Path) or not isinstance(
            precommitted_forbidden_exec_sentinel_manifest, Mapping):
        raise ValueError("runtime root or manifest is invalid")
    roots = (launcher_root, adapter_runtime_root,
             forbidden_exec_sentinel_runtime_root)
    manifests = (precommitted_launcher_manifest,
                 precommitted_adapter_runtime_manifest,
                 precommitted_forbidden_exec_sentinel_manifest)
    if len(set(roots)) != len(roots) or len({id(value) for value in manifests}) != len(manifests):
        raise ValueError("runtime roles must be distinct")
    manifest_bytes = canonical_asset_manifest_shape_bytes(
        precommitted_launcher_manifest)
    expected_sha = hashlib.sha256(manifest_bytes).hexdigest()
    adapter_manifest_bytes = canonical_asset_manifest_shape_bytes(
        precommitted_adapter_runtime_manifest)
    sentinel_manifest_bytes = canonical_asset_manifest_shape_bytes(
        precommitted_forbidden_exec_sentinel_manifest)
    if len({manifest_bytes, adapter_manifest_bytes, sentinel_manifest_bytes}) != 3:
        raise ValueError("runtime role manifests must be distinct")
    backend = runtime = binding = adapter_runtime = adapter_binding = None
    sentinel_runtime = sentinel_binding = live = facade = None
    launcher_identity = adapter_identity = None
    try:
        backend = _observe_os_backend()
        runtime = validate_asset_tree(manifest=precommitted_launcher_manifest,
                                      root=launcher_root)
        launcher_identity = _asset_identity(runtime)
        binding = _bind_backend(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=expected_sha)
        backend = runtime = None
        adapter_runtime = validate_asset_tree(
            manifest=precommitted_adapter_runtime_manifest,
            root=adapter_runtime_root)
        adapter_identity = _asset_identity(adapter_runtime)
        if _same_retained_asset(launcher_identity, adapter_identity):
            raise ValueError("runtime roles must be distinct")
        candidate_adapter_runtime, adapter_runtime = adapter_runtime, None
        adapter_binding = _bind_adapter_runtime(
            adapter_runtime_proof=candidate_adapter_runtime,
            expected_adapter_manifest_bytes=adapter_manifest_bytes)
        adapter_runtime = None
        sentinel_runtime = validate_asset_tree(
            manifest=precommitted_forbidden_exec_sentinel_manifest,
            root=forbidden_exec_sentinel_runtime_root)
        sentinel_identity = _asset_identity(sentinel_runtime)
        if (_same_retained_asset(launcher_identity, sentinel_identity)
                or _same_retained_asset(adapter_identity, sentinel_identity)):
            raise ValueError("runtime roles must be distinct")
        candidate_sentinel_runtime, sentinel_runtime = sentinel_runtime, None
        sentinel_binding = _bind_forbidden_exec_sentinel(
            sentinel_runtime_proof=candidate_sentinel_runtime,
            expected_sentinel_manifest_bytes=sentinel_manifest_bytes)
        sentinel_runtime = None
        live = _LiveFacadeBinding(_TOKEN, backend_binding=binding,
                                  adapter_binding=adapter_binding,
                                  sentinel_binding=sentinel_binding)
        binding = adapter_binding = sentinel_binding = None
        facade = SeatbeltBackendBinding(_TOKEN, live)
        _LIVE[facade] = live
        live = None
        return facade
    except BaseException as failure:
        unregister_error = None
        if facade is not None:
            try:
                _LIVE.pop(facade, None)
            except BaseException as error:
                unregister_error = error
        cleanup = _close_children(live, sentinel_runtime, adapter_runtime, runtime,
                                  backend)
        for child in (sentinel_binding, adapter_binding, binding):
            if child is None:
                continue
            try:
                child.close()
            except BaseException as error:
                if cleanup is None:
                    cleanup = error
        if cleanup is not None:
            raise cleanup from failure
        if unregister_error is not None:
            raise unregister_error from failure
        raise
