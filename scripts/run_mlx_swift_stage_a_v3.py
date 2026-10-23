#!/usr/bin/env python3
"""Run one isolated, offline MLXVLM build using the mounted Apple Metal compiler."""

from __future__ import annotations

import hashlib
import json
import os
import signal
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path("/Volumes/T7/aegis-360-items")
SOURCE = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v2/packages"
STAGE = ROOT / "build/mlx-swift-lm-stage-a-3.32.3-v3"
EXPECTED_TREE = "d0075df90a50b5116a008564790f145bc3e4806ea3f1d65eaff277c1a9070aab"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app"
METAL_TOOLCHAIN = Path(
    "/private/var/run/com.apple.security.cryptexd/mnt/"
    "com.apple.MobileAsset.MetalToolchain-v27.2.47.0.gp3qM5/Metal.xctoolchain"
)


def tree_digest(root: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            digest.update(f"L {relative} {os.readlink(path)}\n".encode())
        elif path.is_file():
            leaf = hashlib.sha256(path.read_bytes()).hexdigest()
            digest.update(f"F {relative} {leaf}\n".encode())
            count += 1
    return count, digest.hexdigest()


def main() -> int:
    if not os.path.ismount("/Volumes/T7") or not ROOT.is_dir():
        raise SystemExit("T7 is not mounted at the approved project root")
    if STAGE.exists():
        raise SystemExit(f"Refusing to overwrite {STAGE}")
    count, digest = tree_digest(SOURCE)
    if (count, digest) != (3457, EXPECTED_TREE):
        raise SystemExit(f"Source snapshot changed: {count} files, {digest}")
    if not (METAL_TOOLCHAIN / "usr/bin/metal").is_file():
        raise SystemExit("Pinned mounted Metal compiler is unavailable")
    developer_dir = XCODE / "Contents/Developer"
    env = os.environ.copy()
    env["DEVELOPER_DIR"] = str(developer_dir)
    version = subprocess.run(
        ["/usr/bin/xcodebuild", "-version"], env=env, capture_output=True, text=True, check=True
    ).stdout
    if version != "Xcode 27.2\nBuild version 27B48\n":
        raise SystemExit(f"Unexpected Xcode version: {version!r}")
    if shutil.disk_usage(ROOT).free < 20 * 1024**3:
        raise SystemExit("Less than 20 GiB free on T7")

    STAGE.mkdir()
    shutil.copytree(SOURCE, STAGE / "packages", symlinks=True)
    (STAGE / "tool-bin").mkdir()
    for name in ("scratch", "cache", "tmp", "module-cache"):
        (STAGE / name).mkdir()
    direct_bin = METAL_TOOLCHAIN / "usr/bin"
    wrappers = {
        "metal": f"#!/bin/zsh\nexec '{direct_bin / 'metal'}' '-fmodules-cache-path={STAGE / 'module-cache'}' \"$@\"\n",
        "metallib": f"#!/bin/zsh\nexec '{direct_bin / 'metallib'}' \"$@\"\n",
        "metal-ar": f"#!/bin/zsh\nexec '{direct_bin / 'metal-ar'}' \"$@\"\n",
    }
    for name, body in wrappers.items():
        path = STAGE / "tool-bin" / name
        path.write_text(body)
        path.chmod(0o755)

    env["PATH"] = f"{STAGE / 'tool-bin'}:{direct_bin}:{env['PATH']}"
    env["TMPDIR"] = str(STAGE / "tmp") + "/"
    env["XDG_CACHE_HOME"] = str(STAGE / "cache")
    env["CLANG_MODULE_CACHE_PATH"] = str(STAGE / "module-cache")
    swift = developer_dir / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"
    command = [
        "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
        str(swift), "build", "--package-path", str(STAGE / "packages/mlx-swift-lm"),
        "--scratch-path", str(STAGE / "scratch"), "--cache-path", str(STAGE / "cache"),
        "--disable-sandbox", "--skip-update", "--target", "MLXVLM", "--jobs", "2",
    ]
    status = STAGE / "status.json"
    status.write_text(json.dumps({"state": "running", "command": command, "start": time.time()}, indent=2))
    started = time.monotonic()
    with (STAGE / "build.log").open("w") as log:
        process = subprocess.Popen(command, cwd=STAGE, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = 124
        state = "timeout" if code == 124 else ("success" if code == 0 else "failed")
    status.write_text(json.dumps({"state": state, "exit_code": code, "elapsed_seconds": round(time.monotonic() - started, 3), "command": command}, indent=2))
    print(f"{state}: exit={code}, stage={STAGE}, elapsed={time.monotonic() - started:.1f}s")
    return code


if __name__ == "__main__":
    sys.exit(main())
