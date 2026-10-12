"""Private shape freeze for the closed synthetic case schedule; no authority."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .sparse_story_runner_contract import (
    CASE_SPECS, build_case_manifest, canonical_asset_manifest_shape_bytes,
    canonical_case_manifest_bytes,
)

_TWO_ARGS = {"argv_literal", "environment_exact", "bundle_read_allowed",
    "model_read_allowed", "prompt_read_allowed"}
_ONE_ARG = {"cwd_identity", "grandchild_containment",
    "network_ipv4_denied", "network_ipv6_denied", "unix_socket_denied",
    "repository_read_denied", "protocol_read_denied",
    "neighbor_packet_read_denied", "result_read_denied",
    "outside_write_denied", "scratch_write_allowed"}
_COORDINATOR = {"bundle_mutation", "replacement_race",
    "single_invocation", "receipt_rebuild"}
_NO_SUPPORT = ({case_id for case_id, _ in CASE_SPECS}
    - _ONE_ARG - _TWO_ARGS - _COORDINATOR)
_PREPARED_OWNER_CASES = ("network_ipv4_denied", "network_ipv6_denied",
    "unix_socket_denied", "outside_write_denied")


def _freeze_private_synthetic_manifest_with_prepared_owners(*,
        adapter_manifest_sha256, repeat_packet_id, stimuli,
        prepared_owners):
    """Freeze shape while the four literal-target owners remain live."""
    from .sparse_story_probe_denials import _PreparedFixedSyntheticOwner
    if (type(prepared_owners) is not dict
            or set(prepared_owners) != set(_PREPARED_OWNER_CASES)
            or not isinstance(stimuli, Mapping)
            or set(stimuli) != {case_id for case_id, _ in CASE_SPECS}):
        raise ValueError("prepared synthetic schedule is incomplete")
    sources = dict(stimuli)
    claims = set()
    request_shape = None
    for case_id in _PREPARED_OWNER_CASES:
        prepared = prepared_owners[case_id]
        if (type(prepared) is not _PreparedFixedSyntheticOwner
                or prepared.case_id != case_id
                or id(prepared.claim) in claims):
            raise ValueError("prepared synthetic owner is duplicated or mismatched")
        prepared.revalidate()
        claims.add(id(prepared.claim))
        retained_request = prepared.claim._session._candidate._request_bytes
        request = json.loads(retained_request)
        packet_id = request["packet_id"]
        if packet_id != repeat_packet_id:
            raise ValueError("prepared synthetic packet ID differs")
        # Each retained session has private asset roots. The candidate separately
        # proves those exact roots and bytes; the portable request must agree.
        for role in ("model", "prompt_schema"):
            request[role].pop("root_path")
        if request_shape is None: request_shape = request
        elif request != request_shape:
            raise ValueError("prepared synthetic requests differ")
        source = stimuli[case_id]
        if not isinstance(source, Mapping):
            raise ValueError("prepared synthetic stimulus is invalid")
        sources[case_id] = {**source, "argv": prepared.argv}
    result = _freeze_private_synthetic_case_manifest(
        adapter_manifest_sha256=adapter_manifest_sha256,
        repeat_packet_id=repeat_packet_id, stimuli=sources)
    for prepared in prepared_owners.values():
        prepared.revalidate()
    return result


def _freeze_private_synthetic_case_manifest(*, adapter_manifest_sha256,
        repeat_packet_id, stimuli: Mapping[str, object]):
    """Hash exact planned argv/stdin/support bytes before any case execution."""
    expected_ids = tuple(case_id for case_id, _ in CASE_SPECS)
    if (not isinstance(stimuli, Mapping)
            or set(stimuli) != set(expected_ids)
            or len(_NO_SUPPORT | _ONE_ARG | _TWO_ARGS | _COORDINATOR)
               != len(expected_ids)):
        raise ValueError("synthetic stimuli must cover the closed case set")
    rows = []
    for case_id, expected in CASE_SPECS:
        source = stimuli[case_id]
        if not isinstance(source, Mapping) or set(source) != {
                "argv", "stdin", "support_manifest"}:
            raise ValueError("synthetic stimulus is incomplete")
        argv = source["argv"]
        if (type(argv) is not tuple
                or any(type(value) is not str or not value or "\x00" in value
                       for value in argv)
                or (len(argv) > 8 if case_id in _COORDINATOR else
                    len(argv) != (2 if case_id in _TWO_ARGS else
                        1 if case_id in _ONE_ARG else 0))):
            raise ValueError("synthetic literal argv is invalid")
        if case_id == "argv_literal" and argv != (
                ";$(touch should-not-run)", "* ' \" \\"):
            raise ValueError("synthetic literal argv changed")
        stdin = source["stdin"]
        if (type(stdin) is not bytes or len(stdin) > 1_048_576
                or (case_id == "concurrent_pipe_pressure"
                    and stdin != b"x" * 60_000)
                or (case_id not in {"concurrent_pipe_pressure",
                    "bundle_mutation", "replacement_race", "single_invocation",
                    "receipt_rebuild"} and stdin)):
            raise ValueError("synthetic stdin bytes are invalid")
        support = source["support_manifest"]
        support_bytes = canonical_asset_manifest_shape_bytes(support)
        if support["asset_kind"] != "synthetic_support":
            raise ValueError("synthetic support manifest has wrong kind")
        if case_id in _NO_SUPPORT and support["entries"]:
            raise ValueError("synthetic case has unexpected support files")
        rows.append({"case_id": case_id, "expected_result": expected,
            "stimulus": {"argv": list(argv),
                "stdin_sha256": hashlib.sha256(stdin).hexdigest(),
                "support_manifest_sha256": hashlib.sha256(
                    support_bytes).hexdigest()}})
    manifest = build_case_manifest(
        synthetic_adapter_manifest_sha256=adapter_manifest_sha256,
        cases=rows, repeat_packet_id=repeat_packet_id)
    return canonical_case_manifest_bytes(manifest,
        synthetic_adapter_manifest_sha256=adapter_manifest_sha256,
        cases=rows, repeat_packet_id=repeat_packet_id), manifest
