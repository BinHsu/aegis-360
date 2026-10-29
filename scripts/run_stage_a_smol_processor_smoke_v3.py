#!/usr/bin/env python3
"""Prepare six synthetic images with the pinned SmolVLM2 processor offline."""

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
STAGE = ROOT / "build/stage-a-smol-processor-v3"
VLM = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v4"
TOKENIZER = ROOT / "build/stage-a-tokenizer-1.3.0-v3"
MODEL = ROOT / "models/smolvlm2-2.2b-instruct-mlx-bf16"
LIBRARY = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v5-shaders/default.metallib"
EXPECTED_LIB = "8f042bff23726e999c5f1a37a9acf454b057d7f42a4a7dbefd22d5a2b133ba59"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
REPO = Path(__file__).resolve().parents[1]


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
        raise SystemExit("Smol processor stage exists; inspect before retry")
    if json.loads((VLM / "status.json").read_text())["state"] != "success":
        raise SystemExit("MLXVLM target build not verified")
    if json.loads((TOKENIZER / "build-status.json").read_text())["state"] != "success":
        raise SystemExit("Tokenizer target build not verified")
    subprocess.run([sys.executable, str(REPO / "scripts/check_stage_a_model_assets.py")], check=True)
    if hashlib.sha256(LIBRARY.read_bytes()).hexdigest() != EXPECTED_LIB:
        raise SystemExit("Metal library changed")
    sources = REPO / "tools/stage_a_vlm"
    (STAGE / "Sources/smol-processor-smoke").mkdir(parents=True)
    (STAGE / "tmp").mkdir()
    (STAGE / "cache").mkdir()
    copied = {}
    for name, target in (("TokenizerBridge.swift", "TokenizerBridge.swift"),
                         ("StageAFrameSequence.swift", "StageAFrameSequence.swift"),
                         ("StageASmolProcessorRegistry.swift", "StageASmolProcessorRegistry.swift"),
                         ("smol_processor_smoke.swift", "SmolProcessorSmoke.swift")):
        path = sources / name
        shutil.copy2(path, STAGE / "Sources/smol-processor-smoke" / target)
        copied[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    prompt = REPO / "prompts/sparse-story-stage-a-v1/prompt.txt"
    shutil.copy2(prompt, STAGE / "prompt.txt")
    copied["prompt.txt"] = hashlib.sha256(prompt.read_bytes()).hexdigest()
    manifest = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "stage-a-smol-processor",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift-lm"),
        .package(path: "../mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift"),
        .package(path: "../stage-a-tokenizer-1.3.0-v3/packages/swift-transformers"),
    ],
    targets: [.executableTarget(name: "smol-processor-smoke", dependencies: [
        .product(name: "MLXVLM", package: "mlx-swift-lm"),
        .product(name: "MLXLMCommon", package: "mlx-swift-lm"),
        .product(name: "Tokenizers", package: "swift-transformers"),
        .product(name: "MLX", package: "mlx-swift"),
    ])]
)
'''
    (STAGE / "Package.swift").write_text(manifest)
    env = os.environ.copy()
    env.update(DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/",
               XDG_CACHE_HOME=str(STAGE / "cache"))
    swift = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    graph_command = [
        "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
        str(swift), "package", "--package-path", str(STAGE),
        "--scratch-path", str(STAGE / "scratch"), "--cache-path", str(STAGE / "cache"),
        "--disable-sandbox", "show-dependencies", "--format", "json",
    ]
    graph_result = subprocess.run(graph_command, cwd=STAGE, env=env,
                                  capture_output=True, text=True, timeout=60)
    (STAGE / "graph.log").write_text(graph_result.stderr)
    if graph_result.returncode:
        raise SystemExit("Combined local dependency graph failed")
    graph = json.loads(graph_result.stdout)
    def check_graph(node: object) -> None:
        if isinstance(node, dict):
            if str(node.get("url", "")).startswith(("http:", "https:")):
                raise SystemExit("Remote package in combined graph")
            for value in node.values():
                check_graph(value)
        elif isinstance(node, list):
            for value in node:
                check_graph(value)
    check_graph(graph)
    (STAGE / "dependencies.json").write_text(graph_result.stdout)
    command = [
        "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
        str(swift), "build", "--package-path", str(STAGE),
        "--scratch-path", str(STAGE / "scratch"), "--cache-path", str(STAGE / "cache"),
        "--disable-sandbox", "--skip-update", "--build-system", "native",
        "--product", "smol-processor-smoke", "--jobs", "2",
    ]
    started = time.monotonic()
    status = {"state": "building", "source_sha256": copied}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    code = invoke(command, env=env, log=STAGE / "build.log", timeout=900)
    if code != 0:
        state = "build_failed"
    else:
        binary = STAGE / "scratch/arm64-apple-macosx/debug/smol-processor-smoke"
        command = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)", str(binary)]
        code = invoke([*command, str(MODEL), str(LIBRARY), str(STAGE / "prompt.txt")],
                      env=env, log=STAGE / "run.log", timeout=90)
        state = "success" if code == 0 else "run_failed"
    status.update(state=state, exit_code=code,
                  elapsed_seconds=round(time.monotonic() - started, 3))
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    return code


if __name__ == "__main__":
    sys.exit(main())
