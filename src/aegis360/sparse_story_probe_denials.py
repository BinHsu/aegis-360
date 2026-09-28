"""Retain actual other-packet and full-result read-denial probe leaves."""

from __future__ import annotations

import json
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path

from .sparse_story_batch_policy import _BatchPolicyCandidate
from .sparse_story_media_tree import _derive_gate_result
from .sparse_story_probe_sentinels import _ReadDenialSentinel


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
