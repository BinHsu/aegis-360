#!/usr/bin/env python3
"""Retain one real Stage A packet and verify its native request without inference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_backend_facade import open_seatbelt_backend_binding  # noqa: E402
from aegis360.sparse_story_batch_policy import _open_batch_policy_candidate  # noqa: E402
from aegis360.sparse_story_media_tree import publish_selected_one_packet_media_gate  # noqa: E402
from aegis360.sparse_story_projection import private_packet_sha256  # noqa: E402
from aegis360.sparse_story_runner_contract import build_runner_policy  # noqa: E402
from run_stage_a_media_preflight import _salt  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-smoke-input-v3"
PREFLIGHT = ROOT / "outputs/stage-a-preflight-oldghost-skiing-v1"
FULL = ROOT / "outputs/stage-a-media-oldghost-skiing-v1"
LAUNCHERS = ROOT / "build/stage-a-native-launcher-assets-v1"
ADAPTER = ROOT / "build/stage-a-native-adapter-v3/runtime"
FROZEN = ROOT / "build/stage-a-frozen-assets-v1"
SALT = REPO / "outputs/stage-a-preflight/oldghost-skiing-v1.salt"
NATIVE_SHAPE = ROOT / "build/stage-a-native-request-v4/native-request-smoke"


def read_manifest(name: str) -> dict:
    return json.loads((REPO / f"docs/experiments/{name}.json").read_bytes())


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Smoke input stage exists; inspect before retry")
    STAGE.mkdir(mode=0o700, parents=True)
    start = time.monotonic()
    status = {"state": "running"}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    try:
        index = json.loads((PREFLIGHT / "adapter-index.json").read_bytes())
        packets = [json.loads((PREFLIGHT / f"private-packet-{i:02d}.json").read_bytes())
                   for i in range(1, 7)]
        hashes = [private_packet_sha256(packet) for packet in packets]
        refs = [row["media_ref"] for packet in index["packets"]
                for row in packet["projection"]["rows"]]
        if len(refs) != 36 or len(set(refs)) != 36:
            raise ValueError("Published Stage A input has incomplete media refs")
        payloads = [(ref, (FULL / "bundle" / ref).read_bytes()) for ref in refs]
        salt = _salt(SALT)
        _, one, selected, selected_hashes, selected_payloads = (
            publish_selected_one_packet_media_gate(
                result_bytes=(FULL / "result.json").read_bytes(),
                index=index, private_packets=packets,
                ordered_private_packet_sha256s=hashes, salt_hex=salt,
                payloads=payloads, bundle=FULL / "bundle",
                presentation_ordinal=1,
                bundle_destination=STAGE / "bundle",
                result_destination=STAGE / "result.json"))
        scratch = STAGE / "scratch"
        home = scratch / "home"
        tmpdir = scratch / "tmp"
        for path in (scratch, home, tmpdir):
            path.mkdir(mode=0o700)
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
                facade=facade, bundle_root=STAGE / "bundle", index=one,
                private_packets=selected,
                ordered_private_packet_sha256s=selected_hashes,
                salt_hex=salt, payloads=selected_payloads,
                media_result_bytes=(STAGE / "result.json").read_bytes(),
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
                checked = subprocess.run([str(NATIVE_SHAPE)], input=request,
                    cwd=STAGE, capture_output=True, timeout=10)
                packet_id = one["packets"][0]["projection"]["packet_id"]
                expected = ("accepted " + packet_id
                            + " with 6 rows\n").encode()
                if checked.returncode != 0 or checked.stdout != expected or checked.stderr:
                    raise RuntimeError("Actual retained request failed native shape gate")
                status.update(packet_id=packet_id,
                              request_sha256=hashlib.sha256(request).hexdigest(),
                              request_bytes=len(request),
                              selected_result_sha256=hashlib.sha256(
                                  (STAGE / "result.json").read_bytes()).hexdigest(),
                              native_shape_accepted=True,
                              candidate_binding_sha256=candidate.invocation_binding_sha256())
            finally:
                candidate.close()
        status["state"] = "success"
    except BaseException as error:
        status.update(state="failed", error_type=type(error).__name__)
        raise
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (STAGE / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
