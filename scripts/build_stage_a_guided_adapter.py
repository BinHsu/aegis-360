#!/usr/bin/env python3
"""Build the guided Stage A diagnostic adapter offline without invoking weights."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import struct
import subprocess
import sys
import time


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-guided-adapter-v1"
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
        raise SystemExit("Native adapter stage exists; inspect before retry")
    if json.loads((VLM / "status.json").read_text())["state"] != "success":
        raise SystemExit("MLXVLM target build not verified")
    if json.loads((TOKENIZER / "build-status.json").read_text())["state"] != "success":
        raise SystemExit("Tokenizer target build not verified")
    subprocess.run([sys.executable, str(REPO / "scripts/check_stage_a_model_assets.py")], check=True)
    if hashlib.sha256(LIBRARY.read_bytes()).hexdigest() != EXPECTED_LIB:
        raise SystemExit("Metal library changed")
    sources = REPO / "tools/stage_a_vlm"
    (STAGE / "Sources/stage-a-guided-adapter").mkdir(parents=True)
    (STAGE / "Sources/StageAProbe/include").mkdir(parents=True)
    (STAGE / "tmp").mkdir()
    (STAGE / "cache").mkdir()
    copied = {}
    for name, target in (("TokenizerBridge.swift", "TokenizerBridge.swift"),
                         ("StageAFrameSequence.swift", "StageAFrameSequence.swift"),
                         ("StageASmolProcessorRegistry.swift", "StageASmolProcessorRegistry.swift"),
                         ("StageAAdapterRequest.swift", "StageAAdapterRequest.swift"),
                         ("StageAResolvedMedia.swift", "StageAResolvedMedia.swift"),
                         ("StageAGuidedAdapterMain.swift", "StageAGuidedAdapterMain.swift")):
        path = sources / name
        shutil.copy2(path, STAGE / "Sources/stage-a-guided-adapter" / target)
        copied[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for name, target in (("sparse_story_synthetic_adapter_fixture.c",
                          "sparse_story_synthetic_adapter_fixture.c"),
                         ("seatbelt_feasibility_probe.c", "seatbelt_feasibility_probe.c")):
        path = REPO / "tools" / name
        shutil.copy2(path, STAGE / "Sources/StageAProbe" / target)
        copied[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    header = sources / "StageAProbe.h"
    shutil.copy2(header, STAGE / "Sources/StageAProbe/include/StageAProbe.h")
    copied["StageAProbe.h"] = hashlib.sha256(header.read_bytes()).hexdigest()
    manifest = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "stage-a-guided-adapter",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift-lm"),
        .package(path: "../mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift"),
        .package(path: "../stage-a-tokenizer-1.3.0-v3/packages/swift-transformers"),
    ],
    targets: [
      .target(name: "StageAProbe", exclude: ["seatbelt_feasibility_probe.c"],
              publicHeadersPath: "include",
              cSettings: [.define("AEGIS_PROBE_ENTRY", to: "aegis_probe_dispatch")]),
      .executableTarget(name: "stage-a-guided-adapter", dependencies: [
        "StageAProbe",
        .product(name: "MLXVLM", package: "mlx-swift-lm"),
        .product(name: "MLXLMCommon", package: "mlx-swift-lm"),
        .product(name: "MLXGuidedGeneration", package: "mlx-swift-lm"),
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
        "--product", "stage-a-guided-adapter", "--jobs", "2",
    ]
    started = time.monotonic()
    status = {"state": "building", "source_sha256": copied}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    code = invoke(command, env=env, log=STAGE / "build.log", timeout=900)
    if code != 0:
        state = "build_failed"
    else:
        binary = STAGE / "scratch/arm64-apple-macosx/debug/stage-a-guided-adapter"
        header = binary.read_bytes()[:32]
        if len(header) != 32 or struct.unpack("<IiiI", header[:16]) != (
                0xFEEDFACF, 0x0100000C, 0, 2):
            raise SystemExit("Built entrypoint is not thin ARM64_ALL Mach-O executable")
        runtime = STAGE / "runtime"
        runtime.mkdir()
        shutil.copy2(binary, runtime / "stage-a-guided-adapter")
        shutil.copy2(LIBRARY, runtime / "default.metallib")
        (runtime / "stage-a-guided-adapter").chmod(0o555)
        (runtime / "default.metallib").chmod(0o444)
        runtime.chmod(0o555)
        command = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
                   str(runtime / "stage-a-guided-adapter")]
        with (STAGE / "run.log").open("w") as output:
            dry = subprocess.run(command, input=b"{}", cwd=STAGE, env=env,
                                 stdout=output, stderr=subprocess.STDOUT, timeout=10)
        code = 0 if dry.returncode == 3 and (STAGE / "run.log").read_bytes() == b"" else 5
        with (STAGE / "probe.log").open("w") as output:
            probe = subprocess.run([*command, "--aegis-synthetic-case", "stdout_empty", "--"],
                                   cwd=STAGE, env=env, stdout=output,
                                   stderr=subprocess.STDOUT, timeout=10)
        if probe.returncode != 0 or (STAGE / "probe.log").read_bytes() != b"":
            code = 6
        state = "success" if code == 0 else "dry_run_failed"
    status.update(state=state, exit_code=code,
                  elapsed_seconds=round(time.monotonic() - started, 3))
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    return code


if __name__ == "__main__":
    sys.exit(main())
