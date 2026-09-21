"""Private retained policy candidates; no installation or invocation authority.

Media bytes derive from the existing sanitizer gate and are then retained with
the stronger asset-tree pathname checks. No child process can be started here.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .isolated_adapter_process import _identity
from .sparse_story_asset_tree import validate_asset_tree
from .sparse_story_backend_facade import _require_live, _close_children
from .sparse_story_media_tree import _derive_gate_result
from .sparse_story_runner_contract import (
    _absolute_policy_path, canonical_asset_manifest_shape_bytes,
    render_seatbelt_policy_input_shape_bytes, build_asset_manifest_shape,
)

_TOKEN = object()


def _canonical_root(root):
    if not isinstance(root, Path):
        raise ValueError("batch root must be a Path")
    _absolute_policy_path(str(root), "batch root")
    if root.resolve(strict=True) != root:
        raise ValueError("batch root must use its canonical filesystem path")
    return root


class _ScratchRoot:
    """Retain an existing private scratch directory without deleting its content."""

    def __init__(self, root):
        self.identity = _identity(_canonical_root(root), "scratch root", 0o700,
                                  directory=True)
        self.closed = False

    def revalidate(self):
        if self.closed:
            raise ValueError("scratch root is closed")
        value = self.identity
        _canonical_root(Path(value.path))
        retained = os.fstat(value.retained_fd)
        named = os.lstat(value.path)
        expected = (value.device, value.inode, value.uid, 0o40700)
        for current in (retained, named):
            if (current.st_dev, current.st_ino, current.st_uid,
                    current.st_mode) != expected:
                raise ValueError("scratch root identity or mode changed")

    def close(self):
        if not self.closed:
            self.closed = True
            os.close(self.identity.retained_fd)


class _BatchPolicyCandidate:
    """Owned input proofs plus a borrowed live facade, never a capability token."""

    def __init__(self, token, *, facade, proofs, scratch, roots, backend_bytes):
        if token is not _TOKEN:
            raise TypeError("batch policy candidates require the private factory")
        self._facade = facade
        self._proofs = proofs
        self._scratch = scratch
        self._roots = dict(roots)
        self._backend_bytes = backend_bytes
        self._frozen_policy = None
        self._closed = False

    def _policy_bytes(self):
        if self._closed:
            raise ValueError("batch policy candidate is closed")
        live = _require_live(self._facade)
        backend_bytes = live.canonical_bytes()
        if backend_bytes != self._backend_bytes:
            raise ValueError("batch backend changed")
        # Rebuild roots from retained objects, never from a caller's policy map.
        runtime = live._adapter_binding._runtime
        sentinel = live._sentinel_binding._runtime
        launcher = live._backend_binding._runtime
        retained = (runtime, sentinel, launcher, *self._proofs)
        root_paths = [_canonical_root(proof._root) for proof in retained]
        identities = [proof.backend_identity()[:2] for proof in retained]
        self._scratch.revalidate()
        root_paths.append(Path(self._scratch.identity.path))
        identities.append((self._scratch.identity.device, self._scratch.identity.inode))
        if len(set(identities)) != len(identities):
            raise ValueError("batch root identities must be distinct")
        if any(a == b or a in b.parents or b in a.parents
               for i, a in enumerate(root_paths) for b in root_paths[i + 1:]):
            raise ValueError("retained batch roots must not overlap")
        roots = {
            "runtime_root": str(runtime._root),
            "runtime_executable": str(runtime._root / runtime._entrypoint),
            "forbidden_executable": str(sentinel._root / sentinel._entrypoint),
            "bundle_root": str(self._proofs[0]._root),
            "model_root": str(self._proofs[1]._root),
            "prompt_root": str(self._proofs[2]._root),
            "scratch_root": self._scratch.identity.path,
        }
        if roots != self._roots:
            raise ValueError("batch root bindings changed")
        policy = render_seatbelt_policy_input_shape_bytes(
            backend_manifest=json.loads(backend_bytes), dynamic_roots=roots)
        if not 1 <= len(policy) <= 65536:
            raise ValueError("batch policy exceeds launcher transport bound")
        if self._frozen_policy is None:
            self._frozen_policy = policy
        elif policy != self._frozen_policy:
            raise ValueError("batch policy bytes changed")
        return policy

    def candidate_sha256(self):
        """Return a path-free candidate digest, not an installed-policy receipt."""
        return hashlib.sha256(self._policy_bytes()).hexdigest()

    def close(self):
        if self._closed:
            return
        self._closed = True
        error = _close_children(self._scratch, *reversed(self._proofs))
        if error is not None:
            raise error

    def __copy__(self):
        raise TypeError("batch policy candidates cannot be copied")

    def __deepcopy__(self, _memo):
        raise TypeError("batch policy candidates cannot be copied")

    def __reduce__(self):
        raise TypeError("batch policy candidates cannot be pickled")


def _open_batch_policy_candidate(*, facade, bundle_root, index, private_packets,
        ordered_private_packet_sha256s, salt_hex, payloads, media_result_bytes,
        model_root, model_manifest, prompt_root, prompt_manifest, scratch_root):
    """Retain one input-derived packet; consume no facade or caller resources."""
    live = _require_live(facade)
    backend_bytes = live.canonical_bytes()
    if (not isinstance(index, dict) or not isinstance(index.get("packets"), list)
            or len(index["packets"]) != 1):
        raise ValueError("batch requires exactly one packet")
    bundle_root = _canonical_root(bundle_root)
    specifications = ((model_root, model_manifest, "model"),
                      (prompt_root, prompt_manifest, "prompt_schema"))
    # Freeze caller mappings before opening any resources.
    frozen = []
    for root, manifest, kind in specifications:
        manifest = json.loads(canonical_asset_manifest_shape_bytes(manifest))
        if manifest["asset_kind"] != kind:
            raise ValueError("batch asset kind is invalid")
        if kind == "prompt_schema" and not {"prompt.txt", "raw-observation-schema.json"}.issubset(
                row["relative_path"] for row in manifest["entries"]):
            raise ValueError("batch prompt/schema leaves are missing")
        frozen.append((_canonical_root(root), manifest))
    proofs = []
    scratch = candidate = None
    try:
        expected, snapshot, _, hashes = _derive_gate_result(
            index=index, private_packets=private_packets,
            ordered_private_packet_sha256s=ordered_private_packet_sha256s,
            salt_hex=salt_hex, payloads=payloads, bundle=bundle_root)
        try:
            if not isinstance(media_result_bytes, bytes) or media_result_bytes != expected:
                raise ValueError("batch media result does not derive")
            # This internal manifest is a retention mechanism, not a replacement
            # for the sanitizer's lineage/result schema or a caller assertion.
            manifest = build_asset_manifest_shape(asset_kind="synthetic_support",
                entries=[{"relative_path": relative, "mode": 0o444,
                          "size": frozen_leaf[2], "sha256": hashes[relative]}
                         for relative, _, frozen_leaf in sorted(
                             snapshot.leaves, key=lambda row: row[0].encode())])
            proofs.append(validate_asset_tree(root=bundle_root, manifest=manifest))
            if proofs[0].backend_identity()[:2] != snapshot.root_identity:
                raise ValueError("batch media root changed while binding")
        finally:
            snapshot.close()
        for root, manifest in frozen:
            proofs.append(validate_asset_tree(root=root, manifest=manifest))
        scratch = _ScratchRoot(scratch_root)
        runtime = live._adapter_binding._runtime
        sentinel = live._sentinel_binding._runtime
        roots = {"runtime_root": str(runtime._root),
                 "runtime_executable": str(runtime._root / runtime._entrypoint),
                 "forbidden_executable": str(sentinel._root / sentinel._entrypoint),
                 "bundle_root": str(bundle_root), "model_root": str(frozen[0][0]),
                 "prompt_root": str(frozen[1][0]), "scratch_root": str(scratch_root)}
        candidate = _BatchPolicyCandidate(_TOKEN, facade=facade,
            proofs=tuple(proofs), scratch=scratch, roots=roots, backend_bytes=backend_bytes)
        proofs = []
        scratch = None
        candidate.candidate_sha256()
        return candidate
    except BaseException as failure:
        cleanup = _close_children(candidate, scratch, *reversed(proofs))
        if cleanup is not None:
            raise cleanup from failure
        raise
