#!/usr/bin/env python3
"""Check six relative PNG reads from a synthetic retained-cwd stand-in."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import zlib

from run_stage_a_native_request_smoke import fixture
from aegis360.sparse_story_runner_contract import canonical_adapter_request_shape_bytes


REPO = Path(__file__).resolve().parents[1]
ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-adapter-media-v1"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
SOURCES = REPO / "tools/stage_a_vlm"


def png(width: int, height: int, red: int) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        payload = kind + body
        return struct.pack(">I", len(body)) + payload + struct.pack(">I", zlib.crc32(payload))
    row = b"\x00" + bytes((red, 0, 0)) * width
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height))
            + chunk(b"IEND", b""))


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Adapter media stage exists; inspect before retry")
    STAGE.mkdir(parents=True)
    (STAGE / "cache").mkdir()
    (STAGE / "tmp").mkdir()
    copied = {}
    for name, target in (("StageAAdapterRequest.swift", "StageAAdapterRequest.swift"),
                         ("StageAResolvedMedia.swift", "StageAResolvedMedia.swift"),
                         ("adapter_media_smoke.swift", "main.swift")):
        source = SOURCES / name
        shutil.copy2(source, STAGE / target)
        copied[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    env = os.environ.copy()
    env.update(DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/",
               XDG_CACHE_HOME=str(STAGE / "cache"),
               CLANG_MODULE_CACHE_PATH=str(STAGE / "cache"))
    swiftc = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
    sdk = XCODE / "Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
    sandbox = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    command = [*sandbox, str(swiftc), "-target", "arm64-apple-macosx14.0",
               "-sdk", str(sdk), "-module-cache-path", str(STAGE / "cache"),
               str(STAGE / "StageAAdapterRequest.swift"),
               str(STAGE / "StageAResolvedMedia.swift"), str(STAGE / "main.swift"),
               "-o", str(STAGE / "adapter-media-smoke")]
    start = time.monotonic()
    with (STAGE / "build.log").open("w") as output:
        built = subprocess.run(command, cwd=STAGE, env=env,
                               stdout=output, stderr=subprocess.STDOUT, timeout=120)
    status = {"state": "build_failed", "source_sha256": copied,
              "cases": 0, "exit_code": built.returncode}
    if built.returncode == 0:
        request = fixture()
        data = canonical_adapter_request_shape_bytes(request)
        base = STAGE / "valid-bundle"
        for index, item in enumerate(request["media"], 1):
            target = base / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(png(960, 540, 20 * index))
            target.chmod(0o444)
        cases = [("valid", base, 0)]
        for name in ("missing", "wrong_size", "corrupt", "symlink"):
            destination = STAGE / f"{name}-bundle"
            shutil.copytree(base, destination)
            leaf = destination / request["media"][2]["path"]
            leaf.chmod(0o644)
            if name == "missing":
                leaf.unlink()
            elif name == "wrong_size":
                leaf.write_bytes(png(2, 2, 60)); leaf.chmod(0o444)
            elif name == "corrupt":
                leaf.write_bytes(b"not a PNG"); leaf.chmod(0o444)
            else:
                leaf.unlink()
                leaf.symlink_to(destination / request["media"][1]["path"])
            cases.append((name, destination, 3))
        with (STAGE / "cases.log").open("w") as output:
            for number, (name, directory, expected) in enumerate(cases):
                result = subprocess.run([*sandbox, str(STAGE / "adapter-media-smoke")],
                                        input=data, cwd=directory, env=env,
                                        capture_output=True, timeout=20)
                output.write(f"{name}: exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}\n")
                if (result.returncode != expected
                        or (expected == 0 and result.stdout != b"accepted 6 ordered PNGs\n")
                        or (expected == 3 and (result.stdout or result.stderr != b"invalid adapter media\n"))):
                    status.update(state="case_failed", exit_code=1, cases=number)
                    break
            else:
                status.update(state="success", exit_code=0, cases=len(cases))
    status["elapsed_seconds"] = round(time.monotonic() - start, 3)
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status))
    return int(status["exit_code"])


if __name__ == "__main__":
    sys.exit(main())
