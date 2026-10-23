#!/usr/bin/env python3
"""Build pinned MLX Metal shaders offline with Apple's mounted compiler."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import time

from run_mlx_swift_stage_a_v4 import EXPECTED_TREE, tree_digest


ROOT = Path("/Volumes/T7/aegis-360-items")
SOURCE = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v4/packages/mlx-swift/Source/Cmlx/mlx-generated/metal"
STAGE = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v5-shaders"
METAL_BIN = Path("/private/var/run/com.apple.security.cryptexd/mnt/com.apple.MobileAsset.MetalToolchain-v27.2.47.0.gp3qM5/Metal.xctoolchain/usr/bin")
SDK = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX27.2.sdk"
SHADERS = (
    "arg_reduce.metal", "conv.metal", "dot.metal", "layer_norm.metal",
    "random.metal", "rms_norm.metal", "rope.metal",
    "scaled_dot_product_attention.metal", "searchsorted.metal",
    "steel/attn/kernels/steel_attention.metal",
)


def main() -> int:
    if not ROOT.is_dir() or not SDK.is_dir() or not (METAL_BIN / "metal").is_file():
        raise SystemExit("Pinned T7 Xcode or mounted Metal toolchain is unavailable")
    if tree_digest(SOURCE.parents[4]) != (3457, EXPECTED_TREE):
        raise SystemExit("Pinned package source snapshot changed")
    present = sorted(p.relative_to(SOURCE).as_posix() for p in SOURCE.rglob("*.metal"))
    if present != sorted(SHADERS):
        raise SystemExit(f"Shader source set changed: {present}")
    if STAGE.exists():
        raise SystemExit(f"Refusing to overwrite {STAGE}")
    (STAGE / "air").mkdir(parents=True)
    (STAGE / "module-cache").mkdir()
    started = time.monotonic()
    status = {"state": "running", "shaders": list(SHADERS)}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    with (STAGE / "build.log").open("w") as log:
        for name in SHADERS:
            output = STAGE / "air" / name.replace("/", "_").replace(".metal", ".air")
            command = [
                "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
                str(METAL_BIN / "metal"),
                f"-fmodules-cache-path={STAGE / 'module-cache'}", "-c",
                "-target", "air64-apple-macos14.0", "-isysroot", str(SDK),
                "-fmetal-math-mode=fast", "-fmetal-math-fp32-functions=fast",
                "-o", str(output), str(SOURCE / name),
            ]
            log.write(f"Compiling {name}\n")
            log.flush()
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
            if result.returncode:
                status.update(state="failed", shader=name, exit_code=result.returncode)
                break
        else:
            air = sorted((STAGE / "air").glob("*.air"))
            command = [
                "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
                str(METAL_BIN / "metallib"), *map(str, air),
                "-o", str(STAGE / "default.metallib"),
            ]
            log.write("Linking default.metallib\n")
            log.flush()
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
            status.update(state="success" if result.returncode == 0 else "failed", exit_code=result.returncode)
    status["elapsed_seconds"] = round(time.monotonic() - started, 3)
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    return int(status["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
