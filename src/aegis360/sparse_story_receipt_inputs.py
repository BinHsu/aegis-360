"""Private, live-derived input lineage for a future run receipt.

These six hashes are input facts only. They do not attest a launch, stdout,
policy installation, cleanup, or publication.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .sparse_story_backend_facade import _require_live
from .sparse_story_batch_policy import _BatchPolicyCandidate
from .sparse_story_projection import canonical_projection_bytes
from .sparse_story_runner_contract import canonical_adapter_request_shape_bytes


@dataclass(frozen=True, slots=True)
class _PrivateReceiptInputs:
    adapter_projection_sha256: str
    sanitized_media_result_sha256: str
    runtime_manifest_sha256: str
    model_manifest_sha256: str
    prompt_schema_manifest_sha256: str
    runner_policy_sha256: str


def _derive_private_receipt_inputs(candidate):
    """Rebuild six input digests while the exact candidate remains live."""
    if type(candidate) is not _BatchPolicyCandidate:
        raise ValueError("receipt inputs require an exact retained candidate")
    before = candidate._binding_bytes()
    request = json.loads(candidate._request_bytes)
    if canonical_adapter_request_shape_bytes(request) != candidate._request_bytes:
        raise ValueError("retained request bytes are not canonical")
    live = _require_live(candidate._facade)
    runtime_sha = live._adapter_binding._runtime.backend_identity()[2]
    model_sha = candidate._proofs[1].backend_identity()[2]
    prompt_sha = candidate._proofs[2].backend_identity()[2]
    if (request["model"]["manifest_sha256"] != model_sha
            or request["prompt_schema"]["manifest_sha256"] != prompt_sha
            or request["model"]["root_path"] != str(candidate._proofs[1]._root)
            or request["prompt_schema"]["root_path"] != str(candidate._proofs[2]._root)):
        raise ValueError("retained request asset lineage changed")
    result = _PrivateReceiptInputs(
        adapter_projection_sha256=hashlib.sha256(
            canonical_projection_bytes(request["projection"])).hexdigest(),
        sanitized_media_result_sha256=candidate._media_result_sha256,
        runtime_manifest_sha256=runtime_sha,
        model_manifest_sha256=model_sha,
        prompt_schema_manifest_sha256=prompt_sha,
        runner_policy_sha256=hashlib.sha256(candidate._runner_policy_bytes).hexdigest())
    if candidate._binding_bytes() != before:
        raise ValueError("receipt input binding changed during derivation")
    return result
