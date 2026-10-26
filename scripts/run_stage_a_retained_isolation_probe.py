#!/usr/bin/env python3
"""Run the full synthetic isolation matrix using the retained Stage A binary."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_backend_facade import open_seatbelt_backend_binding  # noqa: E402
from aegis360.sparse_story_probe_transcript import (  # noqa: E402
    _check_probe_row_values, parse_isolation_probe_transcript,
)
from aegis360.sparse_story_raw_probe_transport import _run_owned_raw_probe  # noqa: E402
from tests.test_sparse_story_raw_probe_transport import RawProbeTransportHostTests  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-retained-isolation-v2"
LAUNCHERS = ROOT / "build/stage-a-native-launcher-assets-v1"
ADAPTER = ROOT / "build/stage-a-native-adapter-v3/runtime"


def read_manifest(name: str) -> dict:
    return json.loads((REPO / f"docs/experiments/{name}.json").read_bytes())


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Retained isolation stage exists; inspect before retry")
    STAGE.mkdir(mode=0o700, parents=True)
    (STAGE / "tmp").mkdir(mode=0o700)
    tempfile.tempdir = str(STAGE / "tmp")
    start = time.monotonic()
    status = {"state": "running"}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    fixture = RawProbeTransportHostTests("test_same_retained_runtime_probes_through_native_launcher")
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
        ) as facade:
            with fixture.context(retained_facade=facade) as context:
                capture = _run_owned_raw_probe(context,
                    outside=context.owned_outside,
                    scratch=context.owned_scratch,
                    listeners=context.owned_listeners)
                status.update(returncode=capture.returncode,
                              completed=capture.completed,
                              group_gone=capture.group_gone,
                              postcheck_passed=capture.postcheck_passed,
                              reason=capture.reason,
                              stdout_bytes=len(capture.stdout))
                if not capture.completed:
                    raise RuntimeError("Retained isolation probe did not complete")
                rows = parse_isolation_probe_transcript(capture.stdout)
                bundle, model, prompt = context.allowed
                matrix = _check_probe_row_values(rows,
                    bundle_prefix=bundle.prefix, model_prefix=model.prefix,
                    prompt_prefix=prompt.prefix)
                status.update(row_count=len(rows), matrix=matrix)
                if not all(matrix.values()):
                    raise RuntimeError("Retained isolation matrix failed")
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
