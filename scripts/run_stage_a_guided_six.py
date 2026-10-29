#!/usr/bin/env python3
"""Two serial guided Stage A runs on the six frozen known-label packets."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_backend_facade import open_seatbelt_backend_binding  # noqa: E402
from aegis360.sparse_story_batch_policy import _open_batch_policy_candidate  # noqa: E402
from aegis360.sparse_story_media_tree import (  # noqa: E402
    publish_sanitized_media_gate, select_one_packet_media_inputs,
    validate_sanitized_media_gate,
)
from aegis360.sparse_story_projection import private_packet_sha256  # noqa: E402
from aegis360.sparse_story_raw_probe_transport import (  # noqa: E402
    _NativeLaunchLedger, _run_native_process,
)
from aegis360.sparse_story_runner_contract import build_runner_policy  # noqa: E402
from aegis360.sparse_story_semantics import _strict_raw, derive_event_class  # noqa: E402
from build_stage_a_preflight_bundle import _salt  # noqa: E402
from run_stage_a_guided_real_smoke import RuntimeMonitor, swap_bytes, thermal_state  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/sga2"
PREFLIGHT = ROOT / "outputs/stage-a-preflight-oldghost-skiing-v1"
FULL = ROOT / "outputs/stage-a-media-oldghost-skiing-v1"
LAUNCHERS = ROOT / "build/stage-a-native-launcher-assets-v1"
ADAPTER = ROOT / "build/stage-a-guided-adapter-v2b/runtime"
FROZEN = ROOT / "build/stage-a-frozen-assets-v1"
SALT = REPO / "outputs/stage-a-preflight/oldghost-skiing-v1.salt"
EXPECTED = (
    "story_change", "no_semantic_change", "story_change",
    "no_semantic_change", "capture_artifact", "no_semantic_change",
)


def manifest(name: str) -> dict:
    return json.loads((REPO / f"docs/experiments/{name}.json").read_bytes())


def persist(status: dict) -> None:
    data = json.dumps(status, sort_keys=True, indent=2).encode()
    temporary = STAGE / "status.next"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("status write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, STAGE / "status.json")
    parent = os.open(STAGE, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def read_metrics(path: Path) -> dict | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_bytes())
    if (type(value) is not dict
            or set(value) != {"schema_version", "peak_active_bytes",
                                  "final_active_bytes", "final_cache_bytes"}
            or value["schema_version"] != "aegis360.stage-a-guided-mlx-memory.v1"
            or any(type(value[name]) is not int or value[name] < 0 for name in (
                "peak_active_bytes", "final_active_bytes", "final_cache_bytes"))
            or value["peak_active_bytes"] < value["final_active_bytes"]):
        raise ValueError("MLX metrics sidecar invalid")
    return value


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Guided six-packet stage exists; inspect before any new run")
    build = json.loads((ADAPTER.parent / "status.json").read_bytes())
    if build.get("state") != "success":
        raise SystemExit("Guided metrics adapter is not a successful build")
    if swap_bytes() is None or thermal_state() in {"serious", "critical"}:
        raise SystemExit("Resource monitoring prerequisites failed")
    index = json.loads((PREFLIGHT / "adapter-index.json").read_bytes())
    packets = [json.loads((PREFLIGHT / f"private-packet-{i:02d}.json").read_bytes())
               for i in range(1, 7)]
    hashes = [private_packet_sha256(packet) for packet in packets]
    refs = [row["media_ref"] for packet in index["packets"]
            for row in packet["projection"]["rows"]]
    payloads = [(ref, (FULL / "bundle" / ref).read_bytes()) for ref in refs]
    salt = _salt(SALT)
    full_result = (FULL / "result.json").read_bytes()
    selected = [select_one_packet_media_inputs(
        result_bytes=full_result, index=index, private_packets=packets,
        ordered_private_packet_sha256s=hashes, salt_hex=salt,
        payloads=payloads, bundle=FULL / "bundle", presentation_ordinal=i)
        for i in range(1, 7)]
    if sorted(hashes.index(item[2][0]) for item in selected) != list(range(6)):
        raise ValueError("Selected six-packet composition is incomplete")

    STAGE.mkdir(mode=0o700, parents=True)
    status = {"state": "preparing", "expected_invocations": 12,
              "completed_invocations": 0, "rows": []}
    persist(status)
    try:
        for ordinal, (one, private, private_hashes, media) in enumerate(selected, 1):
            destination = STAGE / f"p{ordinal}"
            destination.mkdir(mode=0o700)
            publish_sanitized_media_gate(
                index=one, private_packets=private,
                ordered_private_packet_sha256s=private_hashes,
                salt_hex=salt, payloads=media,
                bundle_destination=destination / "bundle",
                result_destination=destination / "result.json")
            validate_sanitized_media_gate(
                result_bytes=(destination / "result.json").read_bytes(),
                index=one, private_packets=private,
                ordered_private_packet_sha256s=private_hashes,
                salt_hex=salt, payloads=media, bundle=destination / "bundle")
        status["state"] = "running"
        persist(status)
        with open_seatbelt_backend_binding(
            launcher_root=LAUNCHERS / "launcher",
            precommitted_launcher_manifest=manifest("stage-a-native-launcher-manifest-v1"),
            adapter_runtime_root=ADAPTER,
            precommitted_adapter_runtime_manifest=manifest(
                "stage-a-guided-adapter-runtime-v2b-manifest"),
            forbidden_exec_sentinel_runtime_root=LAUNCHERS / "sentinel",
            precommitted_forbidden_exec_sentinel_manifest=manifest(
                "stage-a-native-sentinel-manifest-v1"),
        ) as facade:
            policy = build_runner_policy(backend_manifest_sha256=hashlib.sha256(
                facade.canonical_manifest_bytes()).hexdigest())
            for run in (1, 2):
                for ordinal, (one, private, private_hashes, media) in enumerate(selected, 1):
                    scratch = STAGE / f"s{run}{ordinal}"
                    scratch.mkdir(mode=0o700)
                    for part in ("home", "tmp"):
                        (scratch / part).mkdir(mode=0o700)
                    destination = STAGE / f"p{ordinal}"
                    baseline_swap = swap_bytes()
                    baseline_thermal = thermal_state()
                    if baseline_swap is None or baseline_thermal in {"serious", "critical"}:
                        raise RuntimeError("Resource preflight failed during schedule")
                    candidate = _open_batch_policy_candidate(
                        facade=facade, bundle_root=destination / "bundle", index=one,
                        private_packets=private,
                        ordered_private_packet_sha256s=private_hashes,
                        salt_hex=salt, payloads=media,
                        media_result_bytes=(destination / "result.json").read_bytes(),
                        model_root=FROZEN / "model",
                        model_manifest=manifest("stage-a-frozen-model-manifest-v1"),
                        prompt_root=FROZEN / "prompt_schema",
                        prompt_manifest=manifest("stage-a-frozen-prompt-manifest-v1"),
                        scratch_root=scratch,
                        private_home=scratch / "home",
                        private_tmpdir=scratch / "tmp",
                        runner_policy=policy)
                    try:
                        request_hash = hashlib.sha256(candidate._request_bytes).hexdigest()
                        ledger = _NativeLaunchLedger(candidate)
                        monitor = RuntimeMonitor(ledger, baseline_swap)
                        monitor.peak_thermal = baseline_thermal
                        started = time.monotonic()
                        monitor.start()
                        try:
                            capture = _run_native_process(candidate, (),
                                postvalidate=candidate.invocation_binding_sha256,
                                request_bytes=candidate._request_bytes,
                                launch_ledger=ledger)
                        finally:
                            monitor.finish()
                        raw = capture.stdout
                        raw_path = scratch / "raw-output.bin"
                        fd = os.open(raw_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                        try:
                            view = memoryview(raw)
                            while view:
                                written = os.write(fd, view)
                                if written <= 0:
                                    raise OSError("raw-output write made no progress")
                                view = view[written:]
                            os.fsync(fd)
                        finally:
                            os.close(fd)
                        metrics = read_metrics(scratch / "tmp/stage-a-guided-metrics.json")
                        event_class = None
                        if capture.completed and raw:
                            try:
                                event_class = derive_event_class(_strict_raw(raw))
                            except ValueError:
                                pass
                        expected = EXPECTED[hashes.index(private_hashes[0])]
                        row = {
                            "run": run, "presentation_ordinal": ordinal,
                            "packet_id": one["packets"][0]["projection"]["packet_id"],
                            "request_sha256": request_hash,
                            "raw_sha256": hashlib.sha256(raw).hexdigest(),
                            "raw_bytes": len(raw), "event_class": event_class,
                            "expected_class": expected,
                            "transport_completed": capture.completed,
                            "group_gone": capture.group_gone,
                            "postcheck_passed": capture.postcheck_passed,
                            "returncode": capture.returncode,
                            "monitor_stop_reason": monitor.stop_reason,
                            "wall_seconds": round(time.monotonic() - started, 3),
                            "baseline_swap_bytes": baseline_swap,
                            "peak_swap_bytes": monitor.peak_swap,
                            "peak_sampled_rss_bytes": monitor.peak_rss,
                            "peak_child_rss_bytes": resource.getrusage(
                                resource.RUSAGE_CHILDREN).ru_maxrss,
                            "baseline_thermal": baseline_thermal,
                            "peak_thermal": monitor.peak_thermal,
                            "mlx_peak_active_bytes": metrics["peak_active_bytes"]
                                if metrics is not None else None,
                            "mlx_final_cache_bytes": metrics["final_cache_bytes"]
                                if metrics is not None else None,
                        }
                        status["rows"].append(row)
                        status["completed_invocations"] += 1
                        persist(status)
                        if (not capture.completed or event_class is None
                                or metrics is None or monitor.stop_reason is not None):
                            raise RuntimeError("Guided packet failed; no automatic retry")
                    finally:
                        candidate.close()
        if len(status["rows"]) != 12:
            raise RuntimeError("Schedule did not complete")
        by_ordinal = {ordinal: [row for row in status["rows"]
            if row["presentation_ordinal"] == ordinal] for ordinal in range(1, 7)}
        status["repeat_equal"] = all(
            len(rows) == 2 and rows[0]["raw_sha256"] == rows[1]["raw_sha256"]
            and rows[0]["request_sha256"] == rows[1]["request_sha256"]
            for rows in by_ordinal.values())
        status["all_classes_correct"] = all(
            row["event_class"] == row["expected_class"] for row in status["rows"])
        status["state"] = ("pass" if status["repeat_equal"]
                           and status["all_classes_correct"] else "reject")
    except BaseException as error:
        status["state"] = "invalid"
        status["error_type"] = type(error).__name__
        raise
    finally:
        status["unexecuted_invocations"] = 12 - status["completed_invocations"]
        persist(status)
        print(json.dumps({key: value for key, value in status.items() if key != "rows"},
                         sort_keys=True))
    return 0 if status["state"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
