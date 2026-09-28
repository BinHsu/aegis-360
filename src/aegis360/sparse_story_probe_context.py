"""Private assembly of retained raw-probe inputs; no spawn or capability API."""

from __future__ import annotations

from pathlib import Path
from itertools import combinations

from . import sparse_story_batch_policy as batch_policy
from .sparse_story_batch_policy import _BatchPolicyCandidate
from .sparse_story_probe_listeners import _ProbeListeners
from .sparse_story_probe_sentinels import (
    _OutsideSentinelSnapshot, _ReadDenialSentinel, _ScratchProbeSnapshot,
)

_REPOSITORY_SENTINEL = Path(__file__).resolve().parent / "sparse_story_batch_policy.py"
_PROTOCOL_SENTINEL = (Path(__file__).resolve().parents[2] / "docs/experiments"
    / "sparse-story-semantic-successor-v1-2026-09-07.md")


def _overlaps(first: Path, second: Path) -> bool:
    return first == second or first in second.parents or second in first.parents


class _ProbeContext:
    def __init__(self, *, candidate, repository, protocol, neighbor, result,
                 outside, scratch, listeners):
        if (type(candidate) is not _BatchPolicyCandidate
                or any(type(value) is not _ReadDenialSentinel for value in
                       (repository, protocol, neighbor, result))
                or type(outside) is not _OutsideSentinelSnapshot
                or type(scratch) is not _ScratchProbeSnapshot
                or type(listeners) is not _ProbeListeners):
            raise TypeError("raw probe requires exact retained private inputs")
        if (repository.path != _REPOSITORY_SENTINEL
                or protocol.path != _PROTOCOL_SENTINEL):
            raise ValueError("repository and protocol probes require fixed source leaves")
        self.candidate = candidate
        self.reads = (repository, protocol, neighbor, result)
        self.outside = outside
        self.scratch = scratch
        self.listeners = listeners
        self.allowed = None
        self.prevalidate()

    def prevalidate(self):
        self.candidate._binding_bytes()
        allowed = self.candidate._allowed_probe_leaves()
        if self.allowed is None: self.allowed = allowed
        elif self.allowed != allowed: raise ValueError("allowed probe inputs changed")
        if (self.scratch.root != Path(self.candidate._scratch.identity.path)
                or self.scratch.home != Path(self.candidate._private_home.identity.path)
                or self.scratch.tmpdir != Path(self.candidate._private_tmpdir.identity.path)):
            raise ValueError("scratch probe roots do not match the batch")
        roots = tuple(Path(value) for key, value in self.candidate._roots.items()
            if key != "runtime_executable")
        live = batch_policy._require_live(self.candidate._facade)
        roots += (Path(self.candidate._roots["forbidden_executable"]).parent.parent,
                  live._backend_binding._runtime._root)
        forbidden = (self.outside.root, self.listeners.root,
                     *(proof.path for proof in self.reads))
        if (len(set(forbidden)) != len(forbidden)
                or any(_overlaps(first, second) for first, second in combinations(forbidden, 2))
                or any(_overlaps(path, root) for path in forbidden for root in roots)):
            raise ValueError("probe denial sentinels overlap policy roots")
        for proof in self.reads: proof.revalidate()
        self.outside.revalidate()
        self.scratch.prevalidate()
        self.listeners.revalidate()

    def argv_suffix(self) -> tuple[str, ...]:
        self.prevalidate()
        bundle, model, prompt = self.allowed
        return ("--aegis-isolation-probe", str(bundle.path), str(model.path),
            str(prompt.path), str(self.scratch.scratch_write_path),
            *(str(proof.path) for proof in self.reads),
            str(self.outside.create_path), str(self.outside.existing_path),
            str(self.scratch.source_path), str(self.outside.rename_destination),
            str(self.scratch.fork_marker_path), str(self.listeners.ipv4_port),
            str(self.listeners.ipv6_port), str(self.listeners.unix_path),
            self.candidate._roots["forbidden_executable"],
            str(self.scratch.exec_marker_path))

    def postvalidate(self):
        self.candidate._binding_bytes()
        if self.candidate._allowed_probe_leaves() != self.allowed:
            raise ValueError("allowed probe inputs changed after execution")
        for proof in self.reads: proof.revalidate()
        self.outside.revalidate()
        self.scratch.postvalidate()
        self.listeners.revalidate()
