"""One private observation of the complete synthetic case schedule.

The four coordinator rows execute through retained owners.  This module does
not issue the protocol case result, an aggregate, or public runner authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .sparse_story_coordinator_mutation import (
    _OwnedSelectedBundleMutation, _observe_claimed_selected_bundle_mutation_once,
)
from .sparse_story_coordinator_replacement import _file_facts
from .sparse_story_private_attested_replacement import (
    _observe_attested_private_replacement,
)
from .sparse_story_private_exact_rebuild_cases import (
    _observe_private_exact_rebuild_case,
)
from .sparse_story_private_run_publication import _OwnedPrivateRunRoot
from .sparse_story_private_run_receipt import _build_private_synthetic_run_receipt
from .sparse_story_probe_denials import _ClaimedProbedBatch
from .sparse_story_runner_contract import CASE_SPECS, sha256, validate_case_manifest


@dataclass(frozen=True, slots=True)
class _PrivateObservedCase:
    case_id: str
    observed_result: str
    proof: object
    ordinal: int = 0


@dataclass(frozen=True, slots=True)
class _PrivateCompleteSyntheticObservations:
    """Private, live-owner-bound facts; deliberately not a case result."""

    manifest_sha256: str
    rows: tuple[_PrivateObservedCase, ...]
    authority: bool = False


@dataclass(frozen=True, slots=True)
class _PrivateMutationProof:
    claim: _ClaimedProbedBatch
    owner: _OwnedSelectedBundleMutation
    before: tuple[tuple[int, int], str]
    after: tuple[tuple[int, int], str]


@dataclass(frozen=True, slots=True)
class _PrivateReplacementProof:
    claim: _ClaimedProbedBatch
    receipt: object
    owner: _OwnedPrivateRunRoot
    facts: object
    peers: tuple[tuple[tuple[int, int], str], ...]


@dataclass(frozen=True, slots=True)
class _PrivateExactProof:
    claim: _ClaimedProbedBatch
    receipt: object
    facts: object


def _require_uninvoked_claim(claim, *, packet_id, case_id):
    if (type(claim) is not _ClaimedProbedBatch or claim._invoked
            or claim._launch_ledger.count != 0
            or claim._session._invocation_capture is not None):
        raise ValueError(f"{case_id} requires an uninvoked retained claim")
    claim.revalidate()
    request = json.loads(claim._session._candidate._request_bytes)
    if request.get("packet_id") != packet_id:
        raise ValueError(f"{case_id} packet identity differs")


def _run_frozen_case_rows_once(*, frozen_manifest, adapter_step,
        coordinator_step):
    """Dispatch the frozen schedule in order; stop at the first failed row."""
    if (type(frozen_manifest) is not dict
            or type(frozen_manifest.get("cases")) is not list
            or len(frozen_manifest["cases"]) != len(CASE_SPECS)
            or not callable(adapter_step) or not callable(coordinator_step)):
        raise ValueError("frozen case schedule is incomplete")
    results = []
    coordinator = {"bundle_mutation", "replacement_race",
        "single_invocation", "receipt_rebuild"}
    for ordinal, (row, (expected_id, expected_result)) in enumerate(
            zip(frozen_manifest["cases"], CASE_SPECS), 1):
        if (type(row) is not dict or row.get("case_id") != expected_id
                or row.get("expected_result") != expected_result):
            raise ValueError("frozen case execution order differs")
        step = coordinator_step if expected_id in coordinator else adapter_step
        observed = step(row, ordinal)
        if (type(observed) is not _PrivateObservedCase
                or observed.case_id != expected_id
                or observed.ordinal != ordinal):
            raise ValueError("frozen case dispatch proof differs")
        results.append(observed)
    return tuple(results)


def _observe_private_complete_synthetic_cases_once(*, frozen_manifest,
        fixed_claims, prepared_owners, denial_sources, coordinator_stimuli,
        mutation_claim, mutation_owner, replacement_claim, replacement_owner,
        exact_claims):
    """Preflight 37 live owners, then execute the exact frozen row order."""
    from .sparse_story_private_adapter_rebuild import (
        _PrivateAdapterRowProof, _rebuild_private_adapter_observations,
    )
    from .sparse_story_synthetic_plan import (
        _freeze_private_synthetic_adapter_schedule,
        _observe_private_synthetic_adapter_row_once,
    )

    if type(frozen_manifest) is not dict:
        raise ValueError("frozen case manifest is invalid")
    validate_case_manifest(frozen_manifest,
        synthetic_adapter_manifest_sha256=frozen_manifest.get(
            "synthetic_adapter_manifest_sha256"),
        cases=frozen_manifest.get("cases"),
        repeat_packet_id=frozen_manifest.get("repeat_packet_id"))
    if (type(fixed_claims) is not dict or type(prepared_owners) is not dict
            or type(denial_sources) is not dict
            or type(coordinator_stimuli) is not dict
            or type(mutation_owner) is not _OwnedSelectedBundleMutation
            or type(replacement_owner) is not _OwnedPrivateRunRoot
            or type(exact_claims) is not dict
            or set(exact_claims) != {"single_invocation", "receipt_rebuild"}):
        raise ValueError("complete synthetic case owners differ")
    _, rebuilt_manifest = _freeze_private_synthetic_adapter_schedule(
        adapter_manifest_sha256=frozen_manifest["synthetic_adapter_manifest_sha256"],
        repeat_packet_id=frozen_manifest["repeat_packet_id"],
        fixed_claims=fixed_claims, prepared_owners=prepared_owners,
        denial_sources=denial_sources,
        coordinator_stimuli=coordinator_stimuli)
    if frozen_manifest != rebuilt_manifest:
        raise ValueError("frozen synthetic case schedule changed")
    coordinator_claims = {"bundle_mutation": mutation_claim,
        "replacement_race": replacement_claim, **exact_claims}
    adapter_claims = {**fixed_claims,
        **{case_id: owner.claim for case_id, owner in prepared_owners.items()}}
    all_claims = {**adapter_claims, **coordinator_claims}
    if (len(all_claims) != 37
            or any(type(claim) is not _ClaimedProbedBatch
                for claim in coordinator_claims.values())
            or len({id(claim) for claim in all_claims.values()}) != 37
            or len({id(claim._session._candidate) for claim in all_claims.values()})
                != 37
            or len({claim._session._candidate._proofs[0]._root
                for claim in all_claims.values()}) != 37):
        raise ValueError("synthetic claims or selected bundles overlap")
    request_shape = None
    for claim in all_claims.values():
        request = json.loads(claim._session._candidate._request_bytes)
        for role in ("model", "prompt_schema"):
            request[role].pop("root_path")
        if request_shape is None:
            request_shape = request
        elif request != request_shape:
            raise ValueError("synthetic retained requests differ")
    for case_id, claim in coordinator_claims.items():
        _require_uninvoked_claim(claim,
            packet_id=frozen_manifest["repeat_packet_id"], case_id=case_id)
    if (mutation_owner._root != mutation_claim._session._candidate._proofs[0]._root
            or replacement_owner._used):
        raise ValueError("coordinator owner does not match retained claim")
    replacement_owner.revalidate_empty()

    def adapter_step(row, ordinal):
        case_id = row["case_id"]
        owner = prepared_owners.get(case_id)
        claim = owner.claim if owner is not None else fixed_claims[case_id]
        observed = _observe_private_synthetic_adapter_row_once(
            row=row, claim=claim, prepared_owner=owner,
            denial_source=denial_sources.get(case_id))
        proof = _PrivateAdapterRowProof(case_id, observed, claim,
            claim._session._invocation_capture)
        return _PrivateObservedCase(case_id, observed, proof, ordinal)

    def coordinator_step(row, ordinal):
        case_id = row["case_id"]
        claim = coordinator_claims[case_id]
        if case_id == "bundle_mutation":
            mutation_path = mutation_owner._root / mutation_owner._relative
            before = _file_facts(mutation_path)
            observed = _observe_claimed_selected_bundle_mutation_once(
                claim=claim, owner=mutation_owner, frozen_row=row)
            after = _file_facts(mutation_path)
            if (observed != "trust_invalid" or before[0] != after[0]
                    or before[1] == after[1]):
                raise ValueError("bundle mutation did not retain changed leaf")
            return _PrivateObservedCase(case_id, observed,
                _PrivateMutationProof(claim, mutation_owner, before, after),
                ordinal)
        capture = claim._run_coordinator_fixture_case_once(case_id, row)
        if not capture.completed:
            raise ValueError(f"{case_id} native observation is incomplete")
        receipt = _build_private_synthetic_run_receipt(
            claim=claim, frozen_row=row)
        if case_id == "replacement_race":
            facts = _observe_attested_private_replacement(
                owner=replacement_owner, receipt=receipt, frozen_row=row)
            names = ("held-evidence.json", "held-receipt.json",
                "evidence.json", "receipt.json")
            peers = tuple(_file_facts(replacement_owner.root / name)
                for name in names)
            return _PrivateObservedCase(case_id, "replacement_preserved",
                _PrivateReplacementProof(claim, receipt, replacement_owner,
                    facts, peers), ordinal)
        facts = _observe_private_exact_rebuild_case(
            claim=claim, frozen_row=row, receipt=receipt)
        return _PrivateObservedCase(case_id, "exact_rebuild",
            _PrivateExactProof(claim, receipt, facts), ordinal)

    ordered = _run_frozen_case_rows_once(frozen_manifest=frozen_manifest,
        adapter_step=adapter_step, coordinator_step=coordinator_step)
    rebuilt = _rebuild_private_adapter_observations(
        frozen_manifest=frozen_manifest, claims=fixed_claims,
        prepared_owners=prepared_owners)
    adapter_rows = (row for row in ordered if type(row.proof)
        is _PrivateAdapterRowProof)
    for row, actual in zip(adapter_rows, rebuilt.rows):
        if (row.case_id != actual.case_id
                or row.observed_result != actual.observed_result
                or row.proof.claim is not actual.claim
                or row.proof.capture is not actual.capture):
            raise ValueError("adapter observation did not exactly rebuild")
    result = _PrivateCompleteSyntheticObservations(
        manifest_sha256=sha256(frozen_manifest), rows=ordered)
    _revalidate_private_complete_synthetic_observations(
        proof=result, frozen_manifest=frozen_manifest,
        prepared_owners=prepared_owners)
    return result


def _revalidate_private_complete_synthetic_observations(*, proof,
        frozen_manifest, prepared_owners):
    """Rebuild every still-live row without re-executing a fixture."""
    from .sparse_story_private_adapter_rebuild import (
        _PrivateAdapterRowProof, _rebuild_private_adapter_observations,
    )

    if (type(proof) is not _PrivateCompleteSyntheticObservations
            or proof.authority is not False
            or type(proof.rows) is not tuple or len(proof.rows) != 37
            or proof.manifest_sha256 != sha256(frozen_manifest)):
        raise ValueError("private complete observation shape differs")
    validate_case_manifest(frozen_manifest,
        synthetic_adapter_manifest_sha256=frozen_manifest.get(
            "synthetic_adapter_manifest_sha256"),
        cases=frozen_manifest.get("cases"),
        repeat_packet_id=frozen_manifest.get("repeat_packet_id"))
    indexed = {row["case_id"]: row for row in frozen_manifest["cases"]}
    if (len(indexed) != 37 or len({row.case_id for row in proof.rows}) != 37
            or tuple(row.case_id for row in proof.rows)
                != tuple(case_id for case_id, _ in CASE_SPECS)
            or tuple(row.ordinal for row in proof.rows)
                != tuple(range(1, len(CASE_SPECS) + 1))):
        raise ValueError("private complete observation order differs")
    adapter_claims = {}
    for row in proof.rows:
        if type(row) is not _PrivateObservedCase:
            raise ValueError("private case observation type differs")
        case_id = row.case_id
        if case_id not in {"bundle_mutation", "replacement_race",
                "single_invocation", "receipt_rebuild"}:
            if type(row.proof) is not _PrivateAdapterRowProof:
                raise ValueError("private adapter row proof differs")
            if case_id not in prepared_owners:
                adapter_claims[case_id] = row.proof.claim
        elif case_id == "bundle_mutation":
            source = row.proof
            if (type(source) is not _PrivateMutationProof
                    or source.owner._used is not True
                    or source.claim._invoked is not False
                    or source.claim._launch_ledger.count != 0
                    or source.claim._session._invocation_capture is not None
                    or source.owner._root
                        != source.claim._session._candidate._proofs[0]._root
                    or source.before[0] != source.after[0]
                    or source.before[1] == source.after[1]
                    or _file_facts(source.owner._root / source.owner._relative)
                        != source.after):
                raise ValueError("private bundle mutation proof changed")
            try:
                source.claim._session._candidate.invocation_binding_sha256()
            except ValueError:
                pass
            else:
                raise ValueError("private bundle mutation trust was restored")
            if row.observed_result != "trust_invalid":
                raise ValueError("private bundle mutation result differs")
        elif case_id == "replacement_race":
            source = row.proof
            if type(source) is not _PrivateReplacementProof:
                raise ValueError("private replacement proof differs")
            peer_names = ("held-evidence.json", "held-receipt.json",
                "evidence.json", "receipt.json")
            actual = tuple(_file_facts(source.owner.root / name)
                for name in peer_names)
            if (actual != source.peers
                    or source.peers[0][1] != source.facts.evidence_sha256
                    or source.peers[1][1] != source.facts.receipt_sha256
                    or source.facts.case_result is not None
                    or not all((source.facts.revalidation_refused,
                        source.facts.cleanup_refused, source.facts.originals_held,
                        source.facts.replacements_preserved))
                    or row.observed_result != "replacement_preserved"):
                raise ValueError("private replacement peers changed")
            from .sparse_story_private_run_receipt import (
                _rebuild_private_synthetic_run_receipt,
            )
            rebuilt = _rebuild_private_synthetic_run_receipt(
                receipt=source.receipt, frozen_row=indexed[case_id])
            if (source.receipt._claim is not source.claim
                    or source.peers[1][1] != hashlib.sha256(rebuilt).hexdigest()
                    or source.peers[0][1]
                        != hashlib.sha256(source.receipt._capture.stdout).hexdigest()):
                raise ValueError("private replacement receipt changed")
        else:
            source = row.proof
            if (type(source) is not _PrivateExactProof
                    or row.observed_result != "exact_rebuild"
                    or _observe_private_exact_rebuild_case(
                        claim=source.claim, frozen_row=indexed[case_id],
                        receipt=source.receipt) != source.facts):
                raise ValueError("private exact rebuild proof changed")
    rebuilt = _rebuild_private_adapter_observations(
        frozen_manifest=frozen_manifest, claims=adapter_claims,
        prepared_owners=prepared_owners)
    for row, actual in zip((row for row in proof.rows
            if row.case_id not in {"bundle_mutation", "replacement_race",
                "single_invocation", "receipt_rebuild"}), rebuilt.rows):
        if (row.case_id != actual.case_id
                or row.observed_result != actual.observed_result
                or row.proof.claim is not actual.claim
                or row.proof.capture is not actual.capture):
            raise ValueError("private adapter observation changed")
    return proof
