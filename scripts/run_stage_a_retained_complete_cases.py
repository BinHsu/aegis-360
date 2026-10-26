#!/usr/bin/env python3
"""Execute the 37 native synthetic cases with the retained Stage A adapter."""

from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_backend_facade import open_seatbelt_backend_binding  # noqa: E402
from aegis360.sparse_story_coordinator_mutation import _OwnedSelectedBundleMutation, _TOKEN  # noqa: E402
from aegis360.sparse_story_private_complete_cases import (  # noqa: E402
    _observe_private_complete_synthetic_cases_once,
    _revalidate_private_complete_synthetic_observations,
)
from aegis360.sparse_story_private_run_publication import _OwnedPrivateRunRoot  # noqa: E402
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch  # noqa: E402
from aegis360.sparse_story_runner_contract import CASE_SPECS  # noqa: E402
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_adapter_schedule,
)
from tests.test_sparse_story_raw_probe_transport import RawProbeTransportHostTests  # noqa: E402
from tests.test_sparse_story_synthetic_plan import SyntheticCasePlanTests  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-retained-complete-v2"
LAUNCHERS = ROOT / "build/stage-a-native-launcher-assets-v1"
ADAPTER = ROOT / "build/stage-a-native-adapter-v3/runtime"
COORDINATOR = {"bundle_mutation", "replacement_race", "single_invocation", "receipt_rebuild"}
DYNAMIC = {"network_ipv4_denied", "network_ipv6_denied",
           "unix_socket_denied", "outside_write_denied"}


def read_manifest(name: str) -> dict:
    return json.loads((REPO / f"docs/experiments/{name}.json").read_bytes())


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Retained complete stage exists; inspect before retry")
    STAGE.mkdir(mode=0o700, parents=True)
    (STAGE / "tmp").mkdir(mode=0o700)
    tempfile.tempdir = str(STAGE / "tmp")
    start = time.monotonic()
    status = {"state": "running", "prepared": 0, "observed": 0}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    fixture = RawProbeTransportHostTests("test_thirty_three_live_claims_freeze_adapter_schedule")
    try:
        with open_seatbelt_backend_binding(
            launcher_root=LAUNCHERS / "launcher",
            precommitted_launcher_manifest=read_manifest("stage-a-native-launcher-manifest-v1"),
            adapter_runtime_root=ADAPTER,
            precommitted_adapter_runtime_manifest=read_manifest(
                "stage-a-native-adapter-runtime-v3-manifest"),
            forbidden_exec_sentinel_runtime_root=LAUNCHERS / "sentinel",
            precommitted_forbidden_exec_sentinel_manifest=read_manifest(
                "stage-a-native-sentinel-manifest-v1"),
        ) as facade, ExitStack() as stack:
            fixed, prepared, denial_sources, coordinator = {}, {}, {}, {}
            mutation_owner = None
            for case_id, _ in CASE_SPECS:
                inputs = stack.enter_context(fixture.context(
                    own_batch_scratch=True, coordinated=True,
                    retained_facade=facade))
                session = _open_retained_probed_batch(**inputs)
                stack.callback(session.close)
                claim = session.claim_once()
                if case_id in COORDINATOR:
                    coordinator[case_id] = claim
                    if case_id == "bundle_mutation":
                        selected_root = session._candidate._proofs[0]._root
                        identity = os.lstat(selected_root)
                        relative = next(relative for relative, *_ in
                            session._candidate._proofs[0]._leaves
                            if relative.endswith(".png"))
                        mutation_owner = _OwnedSelectedBundleMutation(_TOKEN,
                            selected_root, (identity.st_dev, identity.st_ino), relative)
                elif case_id in DYNAMIC:
                    prepared[case_id] = claim._prepare_fixed_synthetic_owned_case(case_id)
                else:
                    fixed[case_id] = claim
                if case_id in {"neighbor_packet_read_denied", "result_read_denied"}:
                    denial_sources[case_id] = inputs["denial_source"]
                status["prepared"] += 1
                (STAGE / "status.json").write_text(json.dumps(status, indent=2))
            planned = SyntheticCasePlanTests().stimuli()
            planned["bundle_mutation"] = {**planned["bundle_mutation"],
                "argv": (mutation_owner._relative,)}
            packet_id = json.loads(next(iter(fixed.values()))._session
                ._candidate._request_bytes)["packet_id"]
            parameters = dict(
                adapter_manifest_sha256=hashlib.sha256(
                    (REPO / "docs/experiments/stage-a-native-adapter-runtime-v3-manifest.json")
                    .read_bytes()).hexdigest(),
                repeat_packet_id=packet_id, fixed_claims=fixed,
                prepared_owners=prepared, denial_sources=denial_sources,
                coordinator_stimuli={case_id: planned[case_id]
                    for case_id in COORDINATOR})
            _, manifest = _freeze_private_synthetic_adapter_schedule(**parameters)
            if len(manifest["cases"]) != 37:
                raise RuntimeError("Frozen schedule is incomplete")
            replacement_owner = _OwnedPrivateRunRoot(STAGE)
            with mock.patch("aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS",
                            5_000_000_000):
                proof = _observe_private_complete_synthetic_cases_once(
                    frozen_manifest=manifest, fixed_claims=fixed,
                    prepared_owners=prepared, denial_sources=denial_sources,
                    coordinator_stimuli=parameters["coordinator_stimuli"],
                    mutation_claim=coordinator["bundle_mutation"],
                    mutation_owner=mutation_owner,
                    replacement_claim=coordinator["replacement_race"],
                    replacement_owner=replacement_owner,
                    exact_claims={case_id: coordinator[case_id] for case_id in
                        ("single_invocation", "receipt_rebuild")})
            _revalidate_private_complete_synthetic_observations(
                proof=proof, frozen_manifest=manifest,
                prepared_owners=prepared)
            status.update(observed=len(proof.rows),
                          all_expected=tuple(row.observed_result for row in proof.rows)
                          == tuple(expected for _, expected in CASE_SPECS),
                          authority=proof.authority)
            if status["observed"] != 37 or not status["all_expected"] or proof.authority:
                raise RuntimeError("Retained schedule observations differ")
        status["state"] = "success"
    except BaseException as error:
        status.update(state="failed", error_type=type(error).__name__)
        raise
    finally:
        fixture.doCleanups()
        status["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (STAGE / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
