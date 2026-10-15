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


def _observe_private_complete_synthetic_cases_once(*, frozen_manifest,
        adapter_proof, mutation_claim, mutation_owner, replacement_claim,
        replacement_owner, exact_claims, prepared_owners):
    """Run coordinator cases and interleave them with 33 retained adapter facts.

    ``adapter_proof`` must come from the independent 33-row reconstructor; an
    arbitrary sequence of caller-provided result strings is never accepted.
    All owners must remain live until this function finishes.
    """
    from .sparse_story_private_adapter_rebuild import (
        _PrivateAdapterRowsProof, _rebuild_private_adapter_observations,
    )

    if type(frozen_manifest) is not dict:
        raise ValueError("frozen case manifest is invalid")
    validate_case_manifest(frozen_manifest,
        synthetic_adapter_manifest_sha256=frozen_manifest.get(
            "synthetic_adapter_manifest_sha256"),
        cases=frozen_manifest.get("cases"),
        repeat_packet_id=frozen_manifest.get("repeat_packet_id"))
    if (type(adapter_proof) is not _PrivateAdapterRowsProof
            or type(mutation_owner) is not _OwnedSelectedBundleMutation
            or type(replacement_owner) is not _OwnedPrivateRunRoot
            or type(exact_claims) is not dict
            or set(exact_claims) != {"single_invocation", "receipt_rebuild"}):
        raise ValueError("complete synthetic case owners or adapter proof differ")
    rows = {row["case_id"]: row for row in frozen_manifest["cases"]}
    claims = {"bundle_mutation": mutation_claim,
        "replacement_race": replacement_claim, **exact_claims}
    if (any(type(claim) is not _ClaimedProbedBatch for claim in claims.values())
            or len({id(claim) for claim in claims.values()}) != 4
            or len({id(claim._session._candidate) for claim in claims.values()}) != 4):
        raise ValueError("coordinator claims are duplicated")
    coordinator_roots = {claim._session._candidate._proofs[0]._root
        for claim in claims.values()}
    if len(coordinator_roots) != 4:
        raise ValueError("coordinator selected bundles overlap")
    for case_id, claim in claims.items():
        _require_uninvoked_claim(claim,
            packet_id=frozen_manifest["repeat_packet_id"], case_id=case_id)
    if (mutation_owner._root != mutation_claim._session._candidate._proofs[0]._root
            or replacement_owner._used):
        raise ValueError("coordinator owner does not match retained claim")
    replacement_owner.revalidate_empty()
    if type(prepared_owners) is not dict:
        raise ValueError("prepared adapter owners are missing")
    adapter_claims = {row.case_id: row.claim for row in adapter_proof.rows
        if row.case_id not in prepared_owners}
    rebuilt = _rebuild_private_adapter_observations(
        frozen_manifest=frozen_manifest, claims=adapter_claims,
        prepared_owners=prepared_owners)
    if (adapter_proof.manifest_sha256 != rebuilt.manifest_sha256
            or len(adapter_proof.rows) != len(rebuilt.rows)
            or any(left.case_id != right.case_id
                or left.observed_result != right.observed_result
                or left.claim is not right.claim
                or left.capture is not right.capture
                for left, right in zip(adapter_proof.rows, rebuilt.rows))):
        raise ValueError("adapter proof does not exactly rebuild")
    adapter_rows = tuple(_PrivateObservedCase(row.case_id,
        row.observed_result, row) for row in rebuilt.rows)
    if len(adapter_rows) != 33:
        raise ValueError("adapter reconstruction is incomplete")
    if {id(claim) for claim in claims.values()} & {
            id(row.proof.claim) for row in adapter_rows}:
        raise ValueError("coordinator and adapter claims overlap")
    if coordinator_roots & {row.proof.claim._session._candidate._proofs[0]._root
            for row in adapter_rows}:
        raise ValueError("coordinator and adapter selected bundles overlap")

    observed = {}
    # Successful native rows precede the trust-negative mutation, which changes
    # one selected bundle irreversibly within the private synthetic workspace.
    for case_id in ("replacement_race", "single_invocation", "receipt_rebuild"):
        claim = claims[case_id]
        frozen_row = rows[case_id]
        capture = claim._run_coordinator_fixture_case_once(case_id, frozen_row)
        if not capture.completed:
            raise ValueError(f"{case_id} native observation is incomplete")
        receipt = _build_private_synthetic_run_receipt(
            claim=claim, frozen_row=frozen_row)
        if case_id == "replacement_race":
            facts = _observe_attested_private_replacement(
                owner=replacement_owner, receipt=receipt, frozen_row=frozen_row)
            peer_names = ("held-evidence.json", "held-receipt.json",
                "evidence.json", "receipt.json")
            peer_facts = tuple(_file_facts(replacement_owner.root / name)
                for name in peer_names)
            observed[case_id] = _PrivateObservedCase(case_id,
                "replacement_preserved", _PrivateReplacementProof(
                    claim, receipt, replacement_owner, facts, peer_facts))
        else:
            facts = _observe_private_exact_rebuild_case(
                claim=claim, frozen_row=frozen_row, receipt=receipt)
            observed[case_id] = _PrivateObservedCase(case_id,
                "exact_rebuild", _PrivateExactProof(claim, receipt, facts))
    mutation_path = mutation_owner._root / mutation_owner._relative
    before_mutation = _file_facts(mutation_path)
    mutation = _observe_claimed_selected_bundle_mutation_once(
        claim=mutation_claim, owner=mutation_owner,
        frozen_row=rows["bundle_mutation"])
    if mutation != "trust_invalid":
        raise ValueError("bundle mutation did not reject trust")
    after_mutation = _file_facts(mutation_path)
    if (before_mutation[0] != after_mutation[0]
            or before_mutation[1] == after_mutation[1]):
        raise ValueError("bundle mutation did not retain changed leaf")
    observed["bundle_mutation"] = _PrivateObservedCase(
        "bundle_mutation", "trust_invalid", _PrivateMutationProof(
            mutation_claim, mutation_owner, before_mutation, after_mutation))
    by_id = {row.case_id: row for row in adapter_rows}
    if (len(by_id) != 33 or set(by_id) & set(observed)
            or set(by_id) | set(observed) != {case_id for case_id, _ in CASE_SPECS}):
        raise ValueError("complete synthetic observations are misaligned")
    by_id.update(observed)
    ordered = tuple(by_id[case_id] for case_id, _ in CASE_SPECS)
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
    indexed = {row["case_id"]: row for row in frozen_manifest["cases"]}
    if (len(indexed) != 37 or len({row.case_id for row in proof.rows}) != 37
            or tuple(row.case_id for row in proof.rows)
                != tuple(case_id for case_id, _ in CASE_SPECS)):
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
