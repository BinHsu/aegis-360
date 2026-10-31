#!/usr/bin/env python3
"""One bounded unguided decoder control on an exact prior synthetic input."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

from run_stage_a_guided_sensitivity import (
    MAX_RSS_BYTES, MAX_SECONDS, MAX_SWAP_DELTA, ROOT, rss_bytes,
    stop_owned, swap_bytes, thermal_state,
)

VARIANT = sys.argv[1] if len(sys.argv) == 2 else ""
INPUTS = {
    "static": ROOT / "build/stage-a-guided-sensitivity-static-v1",
    "palette_step": ROOT / "build/stage-a-guided-sensitivity-palette-v1",
}
STAGE = ROOT / "build" / f"stage-a-unguided-sensitivity-{VARIANT}-v1"
ADAPTER = ROOT / "build/stage-a-native-adapter-v3/runtime/stage-a-adapter"


def main() -> int:
    if VARIANT not in INPUTS:
        raise SystemExit("usage: run_stage_a_unguided_sensitivity.py static|palette_step")
    if STAGE.exists():
        raise SystemExit("control stage exists; inspect durable result before another run")
    source = INPUTS[VARIANT]
    prior = json.loads((source / "result.json").read_bytes())
    if prior.get("state") != "pass" or prior.get("variant") != VARIANT:
        raise ValueError("guided stimulus was not operationally valid")
    payload = (source / "request.json").read_bytes()
    if hashlib.sha256(payload).hexdigest() != prior["request_sha256"]:
        raise ValueError("canonical request changed")
    request = json.loads(payload)
    actual = [hashlib.sha256((source / "bundle" / row["path"]).read_bytes()).hexdigest()
              for row in request["media"]]
    if actual != prior["image_sha256s"]:
        raise ValueError("synthetic image inputs changed")
    if not ADAPTER.is_file() or json.loads(
            (ADAPTER.parents[1] / "status.json").read_bytes()).get("state") != "success":
        raise ValueError("pinned unguided runtime is unavailable")
    baseline_swap = swap_bytes()
    baseline_thermal = thermal_state()
    if baseline_thermal in {"serious", "critical"}:
        raise RuntimeError("host thermal state is elevated")
    STAGE.mkdir(mode=0o700, parents=True)
    for name in ("home", "tmp", "cache"):
        (STAGE / name).mkdir(mode=0o700)
    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
           "HOME": str(STAGE / "home"), "TMPDIR": str(STAGE / "tmp") + "/",
           "XDG_CACHE_HOME": str(STAGE / "cache"),
           "DEVELOPER_DIR": str(ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer")}
    command = ["/usr/bin/sandbox-exec", "-p",
               "(version 1)(allow default)(deny network*)", str(ADAPTER)]
    started = time.monotonic()
    peak_swap = baseline_swap
    peak_rss = 0
    peak_thermal = baseline_thermal
    stop_reason = None
    with (STAGE / "stdout.bin").open("wb") as stdout, (STAGE / "stderr.bin").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=source / "bundle", env=env,
                                   stdin=subprocess.PIPE, stdout=stdout,
                                   stderr=stderr, start_new_session=True)
        assert process.stdin is not None
        process.stdin.write(payload)
        process.stdin.close()
        while process.poll() is None:
            time.sleep(2)
            if time.monotonic() - started > MAX_SECONDS:
                stop_reason = "timeout"
            try:
                peak_swap = max(peak_swap, swap_bytes())
                peak_rss = max(peak_rss, rss_bytes(process.pid))
                state = thermal_state()
                if {"nominal": 0, "fair": 1, "serious": 2, "critical": 3}[state] > {
                        "nominal": 0, "fair": 1, "serious": 2, "critical": 3}[peak_thermal]:
                    peak_thermal = state
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
                stop_reason = "monitor_failed"
            if stop_reason is None and peak_swap - baseline_swap > MAX_SWAP_DELTA:
                stop_reason = "swap_limit"
            if stop_reason is None and peak_rss > MAX_RSS_BYTES:
                stop_reason = "rss_limit"
            if stop_reason is None and peak_thermal in {"serious", "critical"}:
                stop_reason = "thermal_limit"
            if stop_reason:
                stop_owned(process)
                break
        code = process.wait(timeout=5)
    raw = (STAGE / "stdout.bin").read_bytes()
    stderr_bytes = (STAGE / "stderr.bin").read_bytes()
    operational = bool(code == 0 and stop_reason is None and raw
                       and len(raw) <= 65_536 and not stderr_bytes)
    result = {
        "state": "operational_pass" if operational else "operational_fail",
        "scope": "unguided_synthetic_decoder_control_only",
        "variant": VARIANT,
        "request_sha256": hashlib.sha256(payload).hexdigest(),
        "image_sha256s": actual,
        "stdout_bytes": len(raw),
        "stdout_sha256": hashlib.sha256(raw).hexdigest(),
        "stderr_bytes": len(stderr_bytes),
        "exit_code": code,
        "stop_reason": stop_reason,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "baseline_swap_bytes": baseline_swap,
        "peak_swap_bytes": peak_swap,
        "peak_sampled_rss_bytes": peak_rss,
        "peak_child_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "baseline_thermal": baseline_thermal,
        "peak_thermal": peak_thermal,
        "unexecuted_invocations": 0,
    }
    (STAGE / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2))
    print(json.dumps(result, sort_keys=True))
    return 0 if operational else 1


if __name__ == "__main__":
    raise SystemExit(main())
