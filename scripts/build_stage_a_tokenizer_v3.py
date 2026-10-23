#!/usr/bin/env python3
"""Build the reviewed local-only Swift tokenizer target with network denied."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


STAGE = Path("/Volumes/T7/aegis-360-items/build/stage-a-tokenizer-1.3.0-v3")
XCODE = Path("/Volumes/T7/aegis-360-items/toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer")
PACKAGES = STAGE / "packages"
EXPECTED = {"EventSource", "swift-collections", "swift-crypto", "swift-huggingface", "swift-jinja", "swift-transformers", "yyjson"}


def main() -> int:
    manifest = json.loads((STAGE / "source-manifest.json").read_text())
    expected_hashes = manifest["manifest_sha256"]
    if set(expected_hashes) != EXPECTED or {p.name for p in PACKAGES.iterdir() if p.is_dir()} != EXPECTED:
        raise SystemExit("Tokenizer package set changed")
    for name, expected in expected_hashes.items():
        path = PACKAGES / name / "Package.swift"
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Manifest changed: {name}")
        if ".package(url:" in path.read_text():
            raise SystemExit(f"Remote package reference: {name}")
    graph = json.loads((STAGE / "dependencies.json").read_text())
    def check_graph(node: object) -> None:
        if isinstance(node, dict):
            if "url" in node and str(node["url"]).startswith(("http:", "https:")):
                raise SystemExit("Remote dependency in resolved graph")
            for value in node.values():
                check_graph(value)
        elif isinstance(node, list):
            for value in node:
                check_graph(value)
    check_graph(graph)
    env = os.environ.copy()
    for name in ("tmp", "cache", "scratch"):
        (STAGE / name).mkdir(exist_ok=True)
    env.update(DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/",
               XDG_CACHE_HOME=str(STAGE / "cache"))
    version = subprocess.check_output(["/usr/bin/xcodebuild", "-version"], env=env, text=True)
    if version != "Xcode 27.2\nBuild version 27B48\n":
        raise SystemExit(f"Unexpected Xcode: {version!r}")
    command = [
        "/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)",
        str(XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swift"), "build",
        "--package-path", str(PACKAGES / "swift-transformers"),
        "--scratch-path", str(STAGE / "scratch"), "--cache-path", str(STAGE / "cache"),
        "--disable-sandbox", "--skip-update", "--build-system", "native",
        "--target", "Tokenizers", "--jobs", "2",
    ]
    status = STAGE / "build-status.json"
    if status.exists():
        raise SystemExit("Existing build status; inspect before retry")
    started = time.monotonic()
    status.write_text(json.dumps({"state": "running", "command": command}, indent=2))
    with (STAGE / "build.log").open("w") as log:
        process = subprocess.Popen(command, cwd=STAGE, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
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
    state = "success" if code == 0 else ("timeout" if code == 124 else "failed")
    status.write_text(json.dumps({"state": state, "exit_code": code,
                                  "elapsed_seconds": round(time.monotonic() - started, 3),
                                  "command": command}, indent=2))
    print(f"{state}: exit={code}, elapsed={time.monotonic() - started:.1f}s")
    return code


if __name__ == "__main__":
    sys.exit(main())
