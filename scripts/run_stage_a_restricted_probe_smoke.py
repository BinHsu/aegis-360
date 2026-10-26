#!/usr/bin/env python3
"""Launch two no-model probe cases through the retained Stage A policy."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_backend_facade import (  # noqa: E402
    _require_live, open_seatbelt_backend_binding,
)
from aegis360 import sparse_story_batch_policy as batch_policy  # noqa: E402
from aegis360.sparse_story_raw_probe_transport import _run_native_process  # noqa: E402
from aegis360.sparse_story_runner_contract import build_runner_policy  # noqa: E402
from tests.test_sparse_story_batch_policy import BatchPolicyTests  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-restricted-probe-v2"
LAUNCHERS = ROOT / "build/stage-a-native-launcher-assets-v1"
ADAPTER = ROOT / "build/stage-a-native-adapter-v3/runtime"


def read_manifest(name: str) -> dict:
    return json.loads((REPO / f"docs/experiments/{name}.json").read_bytes())


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Restricted probe stage exists; inspect before retry")
    STAGE.mkdir(mode=0o700, parents=True)
    (STAGE / "tmp").mkdir(mode=0o700)
    tempfile.tempdir = str(STAGE / "tmp")
    start = time.monotonic()
    status = {"state": "running", "cases": []}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    fixture = BatchPolicyTests("test_exact_policy_is_frozen_and_path_free_digest_only")
    initialized = False
    try:
        fixture.setUp()
        initialized = True
        with open_seatbelt_backend_binding(
            launcher_root=LAUNCHERS / "launcher",
            precommitted_launcher_manifest=read_manifest("stage-a-native-launcher-manifest-v1"),
            adapter_runtime_root=ADAPTER,
            precommitted_adapter_runtime_manifest=read_manifest(
                "stage-a-native-adapter-runtime-v3-manifest"),
            forbidden_exec_sentinel_runtime_root=LAUNCHERS / "sentinel",
            precommitted_forbidden_exec_sentinel_manifest=read_manifest(
                "stage-a-native-sentinel-manifest-v1"),
        ) as facade:
            live = _require_live(facade)
            batch_policy._require_live.return_value = live
            backend_hash = hashlib.sha256(facade.canonical_manifest_bytes()).hexdigest()
            args = dict(fixture.args)
            args["facade"] = facade
            args["runner_policy"] = build_runner_policy(
                backend_manifest_sha256=backend_hash)
            for case_id in ("stdout_empty", "environment_exact"):
                candidate = batch_policy._open_batch_policy_candidate(**args)
                try:
                    suffix = ("--aegis-synthetic-case", case_id, "--")
                    if case_id == "environment_exact":
                        suffix += (candidate._private_home.identity.path,
                                   candidate._private_tmpdir.identity.path)
                    capture = _run_native_process(candidate, suffix,
                                                  postvalidate=lambda: None)
                    row = {"case": case_id, "returncode": capture.returncode,
                           "completed": capture.completed,
                           "group_gone": capture.group_gone,
                           "postcheck_passed": capture.postcheck_passed,
                           "reason": capture.reason,
                           "stdout_bytes": len(capture.stdout)}
                    status["cases"].append(row)
                    if (not capture.group_gone or not capture.postcheck_passed
                            or capture.returncode != 0):
                        raise RuntimeError(f"Restricted {case_id} failed transport checks")
                    if case_id == "stdout_empty":
                        if capture.completed or capture.stdout or capture.reason != "native_process_invalid":
                            raise RuntimeError("Empty-output probe violated rejection contract")
                    elif not capture.completed or not capture.stdout:
                        raise RuntimeError(f"Restricted {case_id} did not complete")
                finally:
                    candidate.close()
        status["state"] = "success"
    except BaseException as error:
        status.update(state="failed", error_type=type(error).__name__)
        raise
    finally:
        if initialized:
            fixture.doCleanups()
        status["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (STAGE / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
