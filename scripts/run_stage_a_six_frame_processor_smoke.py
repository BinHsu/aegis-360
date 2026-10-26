#!/usr/bin/env python3
"""Check the pinned MLXVLM frame-selection path using synthetic pixels only."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-six-frame-processor-v2"
VLM = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v4"
LIBRARY = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v5-shaders/default.metallib"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
SOURCE = Path(__file__).resolve().parents[1] / "tools/stage_a_vlm/six_frame_processor_smoke.swift"
FRAME_SOURCE = Path(__file__).resolve().parents[1] / "tools/stage_a_vlm/StageAFrameSequence.swift"
EXPECTED_LIB = "8f042bff23726e999c5f1a37a9acf454b057d7f42a4a7dbefd22d5a2b133ba59"


def invoke(command: list[str], *, env: dict[str, str], log: Path, timeout: int) -> int:
    with log.open("w") as output:
        process = subprocess.Popen(command, cwd=STAGE, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            return 124


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Six-frame stage exists; inspect before retry")
    if json.loads((VLM / "status.json").read_text())["state"] != "success":
        raise SystemExit("Pinned MLXVLM build not verified")
    if hashlib.sha256(LIBRARY.read_bytes()).hexdigest() != EXPECTED_LIB:
        raise SystemExit("Metal library changed")
    (STAGE / "Sources/six-frame-smoke").mkdir(parents=True)
    (STAGE / "tmp").mkdir()
    (STAGE / "cache").mkdir()
    shutil.copy2(SOURCE, STAGE / "Sources/six-frame-smoke/SixFrameProcessorSmoke.swift")
    shutil.copy2(FRAME_SOURCE, STAGE / "Sources/six-frame-smoke/StageAFrameSequence.swift")
    source_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                     for path in (SOURCE, FRAME_SOURCE)}
    manifest = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "stage-a-six-frame-processor",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift-lm"),
        .package(path: "../mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift"),
    ],
    targets: [.executableTarget(name: "six-frame-smoke", dependencies: [
        .product(name: "MLXVLM", package: "mlx-swift-lm"),
        .product(name: "MLXLMCommon", package: "mlx-swift-lm"),
        .product(name: "MLX", package: "mlx-swift")])]
)
'''
    (STAGE / "Package.swift").write_text(manifest)
    env = os.environ.copy()
    env.update(DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/",
               XDG_CACHE_HOME=str(STAGE / "cache"))
    swift = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    sandbox = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    common = ["--package-path", str(STAGE), "--scratch-path", str(STAGE / "scratch"),
              "--cache-path", str(STAGE / "cache"), "--disable-sandbox"]
    graph = subprocess.run([*sandbox, str(swift), "package", *common,
                            "show-dependencies", "--format", "json"],
                           cwd=STAGE, env=env, capture_output=True, text=True, timeout=60)
    (STAGE / "graph.log").write_text(graph.stderr)
    if graph.returncode:
        raise SystemExit("Local graph failed")
    def check_graph(node: object) -> None:
        if isinstance(node, dict):
            if str(node.get("url", "")).startswith(("http:", "https:")):
                raise SystemExit("Remote dependency in graph")
            for value in node.values():
                check_graph(value)
        elif isinstance(node, list):
            for value in node:
                check_graph(value)
    check_graph(json.loads(graph.stdout))
    (STAGE / "dependencies.json").write_text(graph.stdout)
    start = time.monotonic()
    (STAGE / "status.json").write_text(json.dumps({"state": "building", "source_sha256": source_hashes}))
    code = invoke([*sandbox, str(swift), "build", *common, "--skip-update",
                   "--build-system", "native", "--product", "six-frame-smoke", "--jobs", "2"],
                  env=env, log=STAGE / "build.log", timeout=900)
    state = "build_failed"
    if code == 0:
        binary = STAGE / "scratch/arm64-apple-macosx/debug/six-frame-smoke"
        command = [*sandbox, str(binary), str(LIBRARY)]
        code = invoke([*command, "ordered"], env=env, log=STAGE / "run.log", timeout=60)
        state = "run_failed"
        if code == 0:
            negative = invoke([*command, "reversed"], env=env,
                              log=STAGE / "reversed.log", timeout=60)
            short = invoke([*command, "short"], env=env,
                           log=STAGE / "short.log", timeout=60)
            if (negative == 4 and (STAGE / "reversed.log").read_text() == "six-frame order mismatch\n"
                    and short == 5 and (STAGE / "short.log").read_text() == "six-frame processing error\n"):
                state = "success"
            else:
                state = "negative_control_failed"
                code = 4
    status = {"state": state, "source_sha256": source_hashes, "exit_code": code,
              "elapsed_seconds": round(time.monotonic() - start, 3)}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    return code


if __name__ == "__main__":
    sys.exit(main())
