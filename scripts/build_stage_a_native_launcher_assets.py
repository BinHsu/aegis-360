#!/usr/bin/env python3
"""Build the retained launcher and forbidden-exec sentinel with T7 Xcode."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    canonical_asset_manifest_shape_bytes,
)


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-native-launcher-assets-v1"
XCODE = ROOT / "toolchains/xcode-27.2-rc/Xcode.app/Contents/Developer"
CLANG = XCODE / "Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"
SDK = XCODE / "Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk"


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Launcher asset stage exists; inspect before retry")
    if not CLANG.is_file() or not SDK.is_dir():
        raise SystemExit("Pinned T7 compiler or SDK missing")
    STAGE.mkdir(mode=0o700, parents=True)
    (STAGE / "tmp").mkdir(mode=0o700)
    env = os.environ.copy()
    env.update(AEGIS_CLANG=str(CLANG), AEGIS_SDK=str(SDK),
               DEVELOPER_DIR=str(XCODE), TMPDIR=str(STAGE / "tmp") + "/")
    sandbox = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    specifications = (
        ("launcher", "build_sparse_story_native_launcher.sh",
         "bin/aegis-sparse-story-launcher"),
        ("sentinel", "build_sparse_story_forbidden_exec_sentinel.sh",
         "bin/aegis-forbidden-exec-sentinel"),
    )
    start = time.monotonic()
    status = {"state": "building", "source_sha256": {
        name: hashlib.sha256((REPO / "scripts" / name).read_bytes()).hexdigest()
        for _, name, _ in specifications}}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    try:
        for role, script, entrypoint in specifications:
            root = STAGE / role
            with (STAGE / f"{role}.log").open("w") as output:
                result = subprocess.run([*sandbox, str(REPO / "scripts" / script), str(root)],
                                        cwd=STAGE, env=env, stdout=output,
                                        stderr=subprocess.STDOUT, timeout=60)
            if result.returncode:
                raise RuntimeError(f"{role} build failed with exit {result.returncode}")
            manifest = _observe_asset_manifest_shape(
                root=root, asset_kind="runtime", entrypoint=entrypoint)
            proof = validate_asset_tree(manifest=manifest, root=root)
            try:
                target = REPO / f"docs/experiments/stage-a-native-{role}-manifest-v1.json"
                if target.exists():
                    raise RuntimeError("Native runtime manifest destination exists")
                target.write_bytes(canonical_asset_manifest_shape_bytes(manifest))
                status[f"{role}_tree"] = manifest["root_tree_sha256"]
            finally:
                proof.close()
        status.update(state="success", exit_code=0)
    except BaseException as error:
        status.update(state="failed", error_type=type(error).__name__, exit_code=1)
        raise
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (STAGE / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
