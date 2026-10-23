#!/usr/bin/env python3
"""Build and run one local-only tokenizer round trip in an isolated T7 stage."""

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
GRAPH = ROOT / "build/stage-a-tokenizer-1.3.0-v3"
STAGE = ROOT / "build/stage-a-tokenizer-smoke-v1"
MODEL = ROOT / "models/smolvlm2-2.2b-instruct-mlx-bf16"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
REPO = Path(__file__).resolve().parents[1]


def run(command: list[str], *, env: dict[str, str], log: Path, timeout: int) -> int:
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
        raise SystemExit("Tokenizer smoke stage exists; inspect before retry")
    graph_status = json.loads((GRAPH / "build-status.json").read_text())
    if graph_status["state"] != "success" or graph_status["exit_code"] != 0:
        raise SystemExit("Pinned tokenizer target did not build")
    subprocess.run([sys.executable, str(REPO / "scripts/check_stage_a_model_assets.py")], check=True)
    (STAGE / "Sources/smoke").mkdir(parents=True)
    (STAGE / "tmp").mkdir()
    (STAGE / "cache").mkdir()
    source = REPO / "tools/check_stage_a_tokenizer.swift"
    shutil.copy2(source, STAGE / "Sources/smoke/main.swift")
    manifest = '''// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "stage-a-tokenizer-smoke",
    platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../stage-a-tokenizer-1.3.0-v3/packages/swift-transformers")],
    targets: [.executableTarget(name: "smoke", dependencies: [.product(name: "Tokenizers", package: "swift-transformers")])]
)
'''
    (STAGE / "Package.swift").write_text(manifest)
    env = os.environ.copy()
    env.update(DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/",
               XDG_CACHE_HOME=str(STAGE / "cache"))
    swift = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    command = [
        "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
        str(swift), "build", "--package-path", str(STAGE),
        "--scratch-path", str(STAGE / "scratch"), "--cache-path", str(STAGE / "cache"),
        "--disable-sandbox", "--skip-update", "--build-system", "native",
        "--product", "smoke", "--jobs", "2",
    ]
    status = {"state": "building", "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    started = time.monotonic()
    code = run(command, env=env, log=STAGE / "build.log", timeout=900)
    if code == 0:
        binary = STAGE / "scratch/arm64-apple-macosx/debug/smoke"
        code = run(["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
                    str(binary), str(MODEL)], env=env, log=STAGE / "run.log", timeout=60)
        state = "success" if code == 0 else "run_failed"
    else:
        state = "build_failed"
    status.update(state=state, exit_code=code,
                  elapsed_seconds=round(time.monotonic() - started, 3))
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    return code


if __name__ == "__main__":
    sys.exit(main())
