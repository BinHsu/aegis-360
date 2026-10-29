#!/usr/bin/env python3
"""One bounded synthetic smoke for scratch-root MLX metrics on T7."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

from PIL import Image, ImageDraw


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    canonical_adapter_request_shape_bytes, validate_adapter_request_shape,
)
from aegis360.sparse_story_semantics import _decode_raw, validate_raw_observation  # noqa: E402
from run_stage_a_native_request_smoke import fixture  # noqa: E402


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-guided-v3-smoke-v1"
ADAPTER = ROOT / "build/stage-a-guided-adapter-v3/runtime/stage-a-guided-adapter"
PROMPT = ROOT / "build/stage-a-frozen-assets-v1/prompt_schema"
MODEL = ROOT / "build/stage-a-frozen-assets-v1/model"
THERMAL = ROOT / "build/stage-a-guided-feasibility-v2/thermal-state"
MAX_SECONDS = 120
MAX_SWAP_DELTA = 5 * 1024**3
MAX_RSS_BYTES = 8 * 1024**3


def swap_bytes() -> int:
    import re
    result = subprocess.run(["/usr/sbin/sysctl", "-n", "vm.swapusage"],
                            capture_output=True, text=True, timeout=5, check=True)
    match = re.search(r"used = ([0-9]+(?:\.[0-9]+)?)M", result.stdout)
    if match is None:
        raise RuntimeError("swap measurement unavailable")
    return round(float(match.group(1)) * 1024 * 1024)


def thermal_state() -> str:
    result = subprocess.run([str(THERMAL)], capture_output=True,
                            text=True, timeout=5, check=True)
    state = result.stdout.strip()
    if state not in {"nominal", "fair", "serious", "critical"}:
        raise RuntimeError("thermal measurement unavailable")
    return state


def rss_bytes(pid: int) -> int:
    result = subprocess.run(["/bin/ps", "-o", "rss=", "-p", str(pid)],
                            capture_output=True, text=True, timeout=5)
    return int(result.stdout.strip()) * 1024 if result.returncode == 0 else 0


def stop_owned(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Smoke stage exists; inspect durable result before a new run")
    if not ADAPTER.is_file() or not THERMAL.is_file():
        raise SystemExit("Guided adapter or thermal monitor is missing")
    status = json.loads((ADAPTER.parents[1] / "status.json").read_text())
    if status.get("state") != "success":
        raise SystemExit("Guided adapter build is not verified")
    baseline_swap = swap_bytes()
    baseline_thermal = thermal_state()
    if baseline_thermal in {"serious", "critical"}:
        raise SystemExit("Host thermal state is already elevated")

    STAGE.mkdir(mode=0o700, parents=True)
    bundle = STAGE / "bundle"
    scratch = STAGE / "scratch"
    for path in (bundle, scratch, scratch / "home", scratch / "tmp", scratch / "cache"):
        path.mkdir(mode=0o700)
    request = fixture()
    old_id = request["packet_id"]
    new_id = "packet-" + "b" * 20
    request["packet_id"] = new_id
    request["projection"]["packet_id"] = new_id
    for row, media in zip(request["projection"]["rows"], request["media"], strict=True):
        row["media_ref"] = row["media_ref"].replace(old_id, new_id)
        media["media_ref"] = media["media_ref"].replace(old_id, new_id)
        media["path"] = media["path"].replace(old_id, new_id)
    request["prompt_schema"].update(
        manifest_sha256=hashlib.sha256((REPO / "docs/experiments/stage-a-frozen-prompt-manifest-v1.json").read_bytes()).hexdigest(),
        root_path=str(PROMPT))
    request["model"].update(
        manifest_sha256=hashlib.sha256((REPO / "docs/experiments/stage-a-frozen-model-manifest-v1.json").read_bytes()).hexdigest(),
        root_path=str(MODEL))
    validate_adapter_request_shape(request)
    payload = canonical_adapter_request_shape_bytes(request)
    (STAGE / "request.json").write_bytes(payload)

    palette = [(38, 72, 150), (165, 74, 50), (49, 130, 83), (166, 143, 50)]
    for number, media in enumerate(request["media"], 1):
        image = Image.new("RGB", (960, 540))
        draw = ImageDraw.Draw(image)
        for quadrant, color in enumerate(palette):
            x0 = (quadrant % 2) * 480
            y0 = (quadrant // 2) * 270
            draw.rectangle((x0, y0, x0 + 479, y0 + 269), fill=color)
        draw.rectangle((20 + number * 17, 20, 100 + number * 17, 100),
                       fill=(230, 230, 230))
        path = bundle / media["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, format="PNG")

    env = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
           "HOME": str(scratch / "home"), "TMPDIR": str(scratch / "tmp") + "/",
           "XDG_CACHE_HOME": str(scratch / "cache"),
           "DEVELOPER_DIR": str(ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer")}
    command = ["/usr/bin/sandbox-exec", "-p",
               "(version 1)(allow default)(deny network*)", str(ADAPTER)]
    started = time.monotonic()
    max_rss = 0
    peak_thermal = baseline_thermal
    peak_swap = baseline_swap
    stop_reason = None
    with (STAGE / "stdout.bin").open("wb") as stdout, (STAGE / "stderr.bin").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=bundle, env=env, stdin=subprocess.PIPE,
                                   stdout=stdout, stderr=stderr, start_new_session=True)
        assert process.stdin is not None
        process.stdin.write(payload)
        process.stdin.close()
        while process.poll() is None:
            time.sleep(2)
            elapsed = time.monotonic() - started
            try:
                peak_swap = max(peak_swap, swap_bytes())
                state = thermal_state()
                if {"nominal": 0, "fair": 1, "serious": 2, "critical": 3}[state] > {
                    "nominal": 0, "fair": 1, "serious": 2, "critical": 3}[peak_thermal]:
                    peak_thermal = state
                max_rss = max(max_rss, rss_bytes(process.pid))
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
                stop_reason = "monitor_failed"
            if stop_reason is None and elapsed > MAX_SECONDS:
                stop_reason = "timeout"
            if stop_reason is None and peak_swap - baseline_swap > MAX_SWAP_DELTA:
                stop_reason = "swap_limit"
            if stop_reason is None and max_rss > MAX_RSS_BYTES:
                stop_reason = "rss_limit"
            if stop_reason is None and peak_thermal in {"serious", "critical"}:
                stop_reason = "thermal_limit"
            if stop_reason is not None:
                stop_owned(process)
                break
        code = process.wait(timeout=5)

    raw = (STAGE / "stdout.bin").read_bytes()
    stderr = (STAGE / "stderr.bin").read_bytes()
    metrics_path = scratch / "stage-a-guided-metrics.json"
    tmp_empty = not any((scratch / "tmp").iterdir())
    metrics = None
    if metrics_path.is_file():
        try:
            metrics = json.loads(metrics_path.read_bytes())
        except (ValueError, OSError):
            pass
    metrics_valid = (isinstance(metrics, dict)
        and metrics.get("schema_version") == "aegis360.stage-a-guided-mlx-memory.v1"
        and all(type(metrics.get(name)) is int and metrics[name] >= 0 for name in (
            "peak_active_bytes", "final_active_bytes", "final_cache_bytes"))
        and metrics["peak_active_bytes"] >= metrics["final_active_bytes"])
    valid = False
    if code == 0 and stop_reason is None and raw and not stderr and len(raw) <= 65_536:
        try:
            document = _decode_raw(raw)
            validate_raw_observation(document)
            valid = bool(metrics_valid and tmp_empty)
        except ValueError:
            pass
    result = {
        "state": "pass" if valid else "fail",
        "scope": "synthetic_format_only",
        "exit_code": code, "stop_reason": stop_reason,
        "stdout_bytes": len(raw), "stdout_sha256": hashlib.sha256(raw).hexdigest(),
        "stderr_bytes": len(stderr), "request_sha256": hashlib.sha256(payload).hexdigest(),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "baseline_swap_bytes": baseline_swap, "peak_swap_bytes": peak_swap,
        "max_sampled_rss_bytes": max_rss,
        "peak_child_rss_bytes": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "baseline_thermal": baseline_thermal, "peak_thermal": peak_thermal,
        "mlx_metrics_present": bool(metrics_valid),
        "private_tmp_empty": tmp_empty,
        "mlx_peak_active_bytes": metrics["peak_active_bytes"] if metrics_valid else None,
        "mlx_final_cache_bytes": metrics["final_cache_bytes"] if metrics_valid else None,
    }
    (STAGE / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
