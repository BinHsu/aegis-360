"""Conservative coordinator provenance facade for the retained Seatbelt binding."""

from __future__ import annotations

import hashlib
import weakref
from pathlib import Path
from typing import Mapping

from .sparse_story_asset_tree import validate_asset_tree
from .sparse_story_backend_binding import _bind_backend
from .sparse_story_os_backend import _observe_os_backend
from .sparse_story_runner_contract import canonical_asset_manifest_shape_bytes

_TOKEN = object()
_LIVE = weakref.WeakKeyDictionary()
_CLOSED = weakref.WeakSet()
_MISSING = object()


def _close_children(runtime, backend):
    first = None
    for child in (runtime, backend):
        if child is None:
            continue
        try:
            child.close()
        except BaseException as error:
            if first is None:
                first = error
    return first


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
                                  precommitted_launcher_manifest: Mapping):
    """Open a live path-free binding from only a root and precommitted manifest."""
    if not isinstance(launcher_root, Path) or not isinstance(
            precommitted_launcher_manifest, Mapping):
        raise ValueError("launcher root or manifest is invalid")
    manifest_bytes = canonical_asset_manifest_shape_bytes(
        precommitted_launcher_manifest)
    expected_sha = hashlib.sha256(manifest_bytes).hexdigest()
    backend = runtime = binding = None
    try:
        backend = _observe_os_backend()
        runtime = validate_asset_tree(manifest=precommitted_launcher_manifest,
                                      root=launcher_root)
        binding = _bind_backend(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=expected_sha)
        backend = runtime = None
        facade = SeatbeltBackendBinding(_TOKEN, binding)
        _LIVE[facade] = binding
        return facade
    except BaseException as failure:
        cleanup = _close_children(runtime, backend)
        if binding is not None:
            try:
                binding.close()
            except BaseException as error:
                if cleanup is None:
                    cleanup = error
        if cleanup is not None:
            raise cleanup from failure
        raise
