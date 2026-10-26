#!/usr/bin/env python3
"""Run one bounded genuine Stage A packet through the retained native adapter."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_backend_facade import open_seatbelt_backend_binding  # noqa: E402
from aegis360.sparse_story_batch_policy import _open_batch_policy_candidate  # noqa: E402
from aegis360.sparse_story_media_tree import select_one_packet_media_inputs  # noqa: E402
from aegis360.sparse_story_projection import private_packet_sha256  # noqa: E402
from aegis360.sparse_story_projection import canonical_index_bytes  # noqa: E402
from aegis360.sparse_story_raw_probe_transport import (  # noqa: E402
    _NativeLaunchLedger, _run_native_process,
)
from aegis360.sparse_story_runner_contract import build_runner_policy  # noqa: E402
from build_stage_a_preflight_bundle import _salt  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-model-smoke-v2"
INPUT = ROOT / "build/stage-a-smoke-input-v3"
PREFLIGHT = ROOT / "outputs/stage-a-preflight-oldghost-skiing-v1"
FULL = ROOT / "outputs/stage-a-media-oldghost-skiing-v1"
LAUNCHERS = ROOT / "build/stage-a-native-launcher-assets-v1"
ADAPTER = ROOT / "build/stage-a-native-adapter-v3/runtime"
FROZEN = ROOT / "build/stage-a-frozen-assets-v1"
SALT = REPO / "outputs/stage-a-preflight/oldghost-skiing-v1.salt"


def read_manifest(name: str) -> dict:
    return json.loads((REPO / f"docs/experiments/{name}.json").read_bytes())


def swap_bytes() -> int | None:
    result = subprocess.run(["/usr/sbin/sysctl", "-n", "vm.swapusage"],
                            capture_output=True, text=True, timeout=5)
    if result.returncode:
        return None
    import re
    match = re.search(r"used = ([0-9]+(?:\.[0-9]+)?)M", result.stdout)
    return round(float(match.group(1)) * 1024 * 1024) if match else None


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Stage A model smoke exists; inspect before retry")
    input_status = json.loads((INPUT / "status.json").read_bytes())
    if input_status.get("state") != "success" or not input_status.get("native_shape_accepted"):
        raise SystemExit("Real one-packet input proof is absent")
    STAGE.mkdir(mode=0o700, parents=True)
    scratch = STAGE / "scratch"
    home = scratch / "home"
    tmpdir = scratch / "tmp"
    for path in (scratch, home, tmpdir):
        path.mkdir(mode=0o700)
    start = time.monotonic()
    status = {"state": "running", "invocations": 0,
              "swap_before_bytes": swap_bytes()}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    try:
        index = json.loads((PREFLIGHT / "adapter-index.json").read_bytes())
        packets = [json.loads((PREFLIGHT / f"private-packet-{i:02d}.json").read_bytes())
                   for i in range(1, 7)]
        hashes = [private_packet_sha256(packet) for packet in packets]
        refs = [row["media_ref"] for packet in index["packets"]
                for row in packet["projection"]["rows"]]
        payloads = [(ref, (FULL / "bundle" / ref).read_bytes()) for ref in refs]
        salt = _salt(SALT)
        one, selected, selected_hashes, selected_payloads = select_one_packet_media_inputs(
            result_bytes=(FULL / "result.json").read_bytes(),
            index=index, private_packets=packets,
            ordered_private_packet_sha256s=hashes, salt_hex=salt,
            payloads=payloads, bundle=FULL / "bundle", presentation_ordinal=1)
        if ((INPUT / "bundle/adapter-index.json").read_bytes() !=
                canonical_index_bytes(one)):
            raise ValueError("Selected one-packet index changed")
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
            candidate = _open_batch_policy_candidate(
                facade=facade, bundle_root=INPUT / "bundle", index=one,
                private_packets=selected,
                ordered_private_packet_sha256s=selected_hashes,
                salt_hex=salt, payloads=selected_payloads,
                media_result_bytes=(INPUT / "result.json").read_bytes(),
                model_root=FROZEN / "model",
                model_manifest=read_manifest("stage-a-frozen-model-manifest-v1"),
                prompt_root=FROZEN / "prompt_schema",
                prompt_manifest=read_manifest("stage-a-frozen-prompt-manifest-v1"),
                scratch_root=scratch, private_home=home,
                private_tmpdir=tmpdir,
                runner_policy=build_runner_policy(
                    backend_manifest_sha256=hashlib.sha256(
                        facade.canonical_manifest_bytes()).hexdigest()))
            try:
                request = candidate._request_bytes
                if hashlib.sha256(request).hexdigest() != input_status["request_sha256"]:
                    raise ValueError("Retained request changed since native input proof")
                ledger = _NativeLaunchLedger(candidate)
                capture = _run_native_process(candidate, (),
                    postvalidate=candidate.invocation_binding_sha256,
                    request_bytes=request, launch_ledger=ledger)
                status.update(invocations=ledger.count,
                              returncode=capture.returncode,
                              completed=capture.completed,
                              group_gone=capture.group_gone,
                              postcheck_passed=capture.postcheck_passed,
                              reason=capture.reason,
                              stdout_bytes=len(capture.stdout))
                if capture.stdout:
                    output = STAGE / "raw-output.json"
                    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    try:
                        view = memoryview(capture.stdout)
                        while view:
                            view = view[os.write(fd, view):]
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                    status["stdout_sha256"] = hashlib.sha256(capture.stdout).hexdigest()
            finally:
                candidate.close()
        status["state"] = "success" if status.get("completed") else "operational_abstention"
    except BaseException as error:
        status.update(state="failed", error_type=type(error).__name__)
        raise
    finally:
        status.update(elapsed_seconds=round(time.monotonic() - start, 3),
                      peak_child_rss_bytes=resource.getrusage(
                          resource.RUSAGE_CHILDREN).ru_maxrss,
                      swap_after_bytes=swap_bytes())
        (STAGE / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status))
    return 0 if status["state"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
