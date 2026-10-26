#!/usr/bin/env python3
"""Compare the native Stage A request shape gate with the Python contract."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    canonical_adapter_request_shape_bytes, validate_adapter_request_shape,
)
from aegis360.sparse_story_projection import (  # noqa: E402
    PROJECTION_SCHEMA, PUBLIC_AUTHORITY, PUBLIC_PRIVACY, ROLES,
)


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-native-request-v4"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
SOURCES = REPO / "tools/stage_a_vlm"


def fixture() -> dict:
    packet = "packet-" + "a" * 20
    rows = []
    media = []
    for index, role in enumerate(ROLES, 1):
        ref = f"media/{packet}/row-{index:02d}.png"
        rows.append({"row_number": index, "row_role": role, "media_ref": ref,
                     "views": ["view-1", "view-2", "view-3", "view-4"]})
        media.append({"media_ref": ref, "path": ref})
    return {"schema_version": "aegis360.sparse-story-adapter-request.v1",
            "packet_id": packet,
            "projection": {"schema_version": PROJECTION_SCHEMA, "packet_id": packet,
                           "rows": rows, "privacy": PUBLIC_PRIVACY,
                           "authority": PUBLIC_AUTHORITY},
            "media": media,
            "prompt_schema": {"manifest_sha256": "a" * 64,
                              "root_path": "/private/tmp/stage-a-prompt",
                              "prompt_path": "prompt.txt",
                              "schema_path": "raw-observation-schema.json"},
            "model": {"manifest_sha256": "b" * 64,
                      "root_path": "/private/tmp/stage-a-model"}}


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Native request stage exists; inspect before retry")
    STAGE.mkdir(parents=True)
    (STAGE / "cache").mkdir()
    (STAGE / "tmp").mkdir()
    copied = {}
    for name, target in (("StageAAdapterRequest.swift", "StageAAdapterRequest.swift"),
                         ("adapter_request_smoke.swift", "main.swift")):
        source = SOURCES / name
        shutil.copy2(source, STAGE / target)
        copied[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    env = os.environ.copy()
    env.update(DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/",
               XDG_CACHE_HOME=str(STAGE / "cache"),
               CLANG_MODULE_CACHE_PATH=str(STAGE / "cache"))
    swiftc = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc"
    sandbox = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    sdk = XCODE / "Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"
    command = [*sandbox, str(swiftc), "-target", "arm64-apple-macosx14.0",
               "-sdk", str(sdk),
               "-module-cache-path", str(STAGE / "cache"),
               str(STAGE / "StageAAdapterRequest.swift"), str(STAGE / "main.swift"),
               "-o", str(STAGE / "native-request-smoke")]
    start = time.monotonic()
    with (STAGE / "build.log").open("w") as output:
        built = subprocess.run(command, cwd=STAGE, env=env,
                               stdout=output, stderr=subprocess.STDOUT, timeout=120)
    status = {"state": "build_failed", "source_sha256": copied,
              "cases": 0, "exit_code": built.returncode}
    if built.returncode == 0:
        valid = fixture()
        validate_adapter_request_shape(valid)
        cases = [("valid", valid, True)]
        changed = copy.deepcopy(valid); changed["media"][1]["path"] = changed["media"][0]["path"]
        cases.append(("media_order", changed, False))
        changed = copy.deepcopy(valid); changed["projection"]["rows"][0]["row_number"] = True
        cases.append(("boolean_row", changed, False))
        changed = copy.deepcopy(valid); changed["projection"]["rows"][0]["row_number"] = 1.0
        cases.append(("float_row", changed, False))
        changed = copy.deepcopy(valid); changed["projection"]["privacy"]["contains_identity"] = True
        cases.append(("privacy", changed, False))
        changed = copy.deepcopy(valid); changed["prompt_schema"]["root_path"] = "/private/tmp/../prompt"
        cases.append(("root", changed, False))
        changed = copy.deepcopy(valid); changed["extra"] = "forbidden"
        cases.append(("extra_key", changed, False))
        changed = copy.deepcopy(valid); changed["media"] = changed["media"][:-1]
        cases.append(("five_media", changed, False))
        canonical = canonical_adapter_request_shape_bytes(valid)
        cases.append(("duplicate_key", b'{"packet_id":"' + valid["packet_id"].encode()
                      + b'",' + canonical[1:], False))
        cases.append(("trailing_space", canonical + b" ", False))
        cases.append(("empty", b"", False))
        cases.append(("over_limit", b" " * 65_537, False))
        with (STAGE / "cases.log").open("w") as output:
            for number, (name, payload, accepted) in enumerate(cases):
                if isinstance(payload, bytes):
                    data = payload
                elif accepted:
                    data = canonical_adapter_request_shape_bytes(payload)
                else:
                    try:
                        validate_adapter_request_shape(payload)
                    except ValueError:
                        data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                    else:
                        raise SystemExit(f"Python contract unexpectedly accepted {name}")
                result = subprocess.run([*sandbox, str(STAGE / "native-request-smoke")],
                                        input=data, cwd=STAGE, env=env,
                                        capture_output=True, timeout=10)
                expected_code = 0 if accepted else 3
                output.write(f"{name}: exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}\n")
                if (result.returncode != expected_code
                        or (accepted and result.stderr)
                        or (not accepted and (result.stdout or result.stderr != b"invalid adapter request\n"))):
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
