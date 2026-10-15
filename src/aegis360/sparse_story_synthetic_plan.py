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


def _fixed_stimulus_from_retained_claim(claim, case_id, *, denial_source=None):
    """Derive a fixed case's literal stimulus from its still-live candidate."""
    from .sparse_story_probe_denials import (
        _ClaimedProbedBatch, _retain_full_set_denials,
    )
    from .sparse_story_probe_context import (
        _PROTOCOL_SENTINEL, _REPOSITORY_SENTINEL,
    )
    from .sparse_story_runner_contract import build_asset_manifest_shape

    if (type(claim) is not _ClaimedProbedBatch or claim._invoked
            or case_id in _COORDINATOR or case_id in _PREPARED_OWNER_CASES
            or case_id not in {name for name, _ in CASE_SPECS}):
        raise ValueError("fixed synthetic claim or case is invalid")
    claim.revalidate()
    candidate = claim._session._candidate
    if denial_source is not None and case_id not in {
            "neighbor_packet_read_denied", "result_read_denied"}:
        raise ValueError("full-set source is unrelated to fixed case")
    argv = ()
    if case_id == "argv_literal":
        argv = (";$(touch should-not-run)", "* ' \" \\")
    elif case_id == "environment_exact":
        argv = (candidate._private_home.identity.path,
            candidate._private_tmpdir.identity.path)
    elif case_id == "cwd_identity":
        argv = (str(candidate._proofs[0]._root),)
    elif case_id == "grandchild_containment":
        argv = (str(claim._session._batch_scratch.root / "grandchild-marker"),)
    elif case_id == "scratch_write_allowed":
        target = claim._session._batch_scratch.root / "synthetic-write"
        import os
        try: os.lstat(target)
        except FileNotFoundError: pass
        else: raise ValueError("fixed synthetic scratch target already exists")
        argv = (str(target),)
    elif case_id in {"repository_read_denied", "protocol_read_denied"}:
        argv = (str(_REPOSITORY_SENTINEL if case_id ==
            "repository_read_denied" else _PROTOCOL_SENTINEL),)
    elif case_id in {"bundle_read_allowed", "model_read_allowed",
            "prompt_read_allowed"}:
        index = {"bundle_read_allowed": 0, "model_read_allowed": 1,
            "prompt_read_allowed": 2}[case_id]
        leaf = candidate._allowed_probe_leaves()[index]
        argv = (str(leaf.path), "hex:" + leaf.prefix.hex())
    elif case_id in {"neighbor_packet_read_denied", "result_read_denied"}:
        if type(denial_source) is not dict:
            raise ValueError("fixed full-set source is missing")
        with _retain_full_set_denials(candidate=candidate, **denial_source) as (
                neighbor, result):
            target = (neighbor if case_id == "neighbor_packet_read_denied"
                else result)
            argv = (str(target.path),)
    stdin = b"x" * 60_000 if case_id == "concurrent_pipe_pressure" else b""
    claim.revalidate()
    return {"argv": argv, "stdin": stdin,
        "support_manifest": build_asset_manifest_shape(
            asset_kind="synthetic_support", entries=[])}


def _freeze_private_synthetic_adapter_schedule(*, adapter_manifest_sha256,
        repeat_packet_id, fixed_claims, prepared_owners, denial_sources,
        coordinator_stimuli):
    """Freeze all 33 adapter rows from distinct retained claims and owners."""
    from .sparse_story_probe_denials import _ClaimedProbedBatch
    from .sparse_story_runner_contract import build_asset_manifest_shape

    fixed_ids = ({case_id for case_id, _ in CASE_SPECS}
        - set(_PREPARED_OWNER_CASES) - _COORDINATOR)
    if (type(fixed_claims) is not dict or set(fixed_claims) != fixed_ids
            or type(denial_sources) is not dict
            or set(denial_sources) != {"neighbor_packet_read_denied",
                "result_read_denied"}
            or type(coordinator_stimuli) is not dict
            or set(coordinator_stimuli) != _COORDINATOR
            or type(prepared_owners) is not dict
            or set(prepared_owners) != set(_PREPARED_OWNER_CASES)):
        raise ValueError("retained synthetic schedule is incomplete")
    claims = {case_id: fixed_claims[case_id] for case_id in fixed_ids}
    for case_id, owner in prepared_owners.items():
        from .sparse_story_probe_denials import _PreparedFixedSyntheticOwner
        if type(owner) is not _PreparedFixedSyntheticOwner or owner.case_id != case_id:
            raise ValueError("prepared synthetic owner differs")
        claims[case_id] = owner.claim
    if (any(type(claim) is not _ClaimedProbedBatch or claim._invoked
            for claim in claims.values())
            or len({id(claim) for claim in claims.values()}) != 33
            or len({id(claim._session._candidate) for claim in claims.values()}) != 33):
        raise ValueError("retained synthetic claims are duplicated or consumed")
    request_shape = None
    for claim in claims.values():
        claim.revalidate()
        request = json.loads(claim._session._candidate._request_bytes)
        if request["packet_id"] != repeat_packet_id:
            raise ValueError("retained synthetic packet ID differs")
        for role in ("model", "prompt_schema"):
            request[role].pop("root_path")
        if request_shape is None: request_shape = request
        elif request != request_shape:
            raise ValueError("retained synthetic requests differ")
    empty = build_asset_manifest_shape(asset_kind="synthetic_support", entries=[])
    stimuli = dict(coordinator_stimuli)
    for case_id in fixed_ids:
        stimuli[case_id] = _fixed_stimulus_from_retained_claim(
            claims[case_id], case_id,
            denial_source=denial_sources.get(case_id))
    for case_id, owner in prepared_owners.items():
        stimuli[case_id] = {"argv": owner.argv, "stdin": b"",
            "support_manifest": empty}
    result = _freeze_private_synthetic_manifest_with_prepared_owners(
        adapter_manifest_sha256=adapter_manifest_sha256,
        repeat_packet_id=repeat_packet_id, stimuli=stimuli,
        prepared_owners=prepared_owners)
    for claim in claims.values(): claim.revalidate()
    return result


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
