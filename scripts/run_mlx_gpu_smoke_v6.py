#!/usr/bin/env python3
"""Build and run a tiny offline MLX GPU operation using the pinned T7 sources."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from run_mlx_swift_stage_a_v4 import EXPECTED_TREE, tree_digest


ROOT = Path("/Volumes/T7/aegis-360-items")
PACKAGES = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v4/packages"
LIBRARY = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v5-shaders/default.metallib"
STAGE = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v6-gpu-smoke"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
METAL_BIN = Path("/private/var/run/com.apple.security.cryptexd/mnt/com.apple.MobileAsset.MetalToolchain-v27.2.47.0.gp3qM5/Metal.xctoolchain/usr/bin")
EXPECTED_LIB = "8f042bff23726e999c5f1a37a9acf454b057d7f42a4a7dbefd22d5a2b133ba59"


def main() -> int:
    import hashlib

    if STAGE.exists():
        raise SystemExit(f"Refusing to overwrite {STAGE}")
    if tree_digest(PACKAGES) != (3457, EXPECTED_TREE):
        raise SystemExit("Pinned source snapshot changed")
    if hashlib.sha256(LIBRARY.read_bytes()).hexdigest() != EXPECTED_LIB:
        raise SystemExit("Metal library changed")
    if not (METAL_BIN / "metal").is_file():
        raise SystemExit("Mounted Metal compiler unavailable")
    (STAGE / "Sources/smoke").mkdir(parents=True)
    (STAGE / "tmp").mkdir()
    (STAGE / "cache").mkdir()
    (STAGE / "tool-bin").mkdir()
    source = Path(__file__).resolve().parents[1] / "tools/check_mlx_gpu_smoke.swift"
    shutil.copy2(source, STAGE / "Sources/smoke/main.swift")
    manifest = f'''// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "mlx-gpu-smoke",
    platforms: [.macOS(.v14)],
    dependencies: [.package(path: "{PACKAGES / 'mlx-swift'}")],
    targets: [.executableTarget(name: "smoke", dependencies: [.product(name: "MLX", package: "mlx-swift")])]
)
'''
    (STAGE / "Package.swift").write_text(manifest)
    (STAGE / "tool-bin/metal").write_text(
        f"#!/bin/zsh\nexec '{METAL_BIN / 'metal'}' '-fmodules-cache-path={STAGE / 'cache'}' \"$@\"\n"
    )
    (STAGE / "tool-bin/metal").chmod(0o755)
    env = os.environ.copy()
    env.update(
        DEVELOPER_DIR=str(XCODE),
        TMPDIR=str(STAGE / "tmp") + "/",
        XDG_CACHE_HOME=str(STAGE / "cache"),
        PATH=str(STAGE / "tool-bin") + ":" + env["PATH"],
    )
    swift = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    command = [
        "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
        str(swift), "build", "--package-path", str(STAGE),
        "--scratch-path", str(STAGE / "scratch"), "--cache-path", str(STAGE / "cache"),
        "--disable-sandbox", "--skip-update", "--build-system", "native",
        "--product", "smoke", "--jobs", "2",
    ]
    started = time.monotonic()
    status: dict[str, object] = {"state": "building", "build_command": command}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    with (STAGE / "build.log").open("w") as log:
        result = subprocess.run(command, cwd=STAGE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
    if result.returncode:
        status.update(state="build_failed", exit_code=result.returncode)
    else:
        binary = STAGE / "scratch/arm64-apple-macosx/debug/smoke"
        with (STAGE / "run.log").open("w") as log:
            result = subprocess.run(
                ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
                 str(binary), str(LIBRARY)],
                cwd=STAGE, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60,
            )
        status.update(state="success" if result.returncode == 0 else "run_failed", exit_code=result.returncode)
    status["elapsed_seconds"] = round(time.monotonic() - started, 3)
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps({k: v for k, v in status.items() if k != "build_command"}))
    return int(status["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
