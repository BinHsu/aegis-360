#!/usr/bin/env python3
"""Freeze the verified local Stage A model and prompt into strict T7 roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

from check_stage_a_model_assets import ROOT as SOURCE_MODEL, REVISION, main as check_source


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    canonical_asset_manifest_shape_bytes,
)


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-frozen-assets-v1"
MODEL = STAGE / "model"
PROMPT = STAGE / "prompt_schema"
PROMPT_SOURCE = REPO / "prompts/sparse-story-stage-a-v1"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze_file(source: Path, destination: Path) -> None:
    if not source.is_file() or source.is_symlink() or destination.exists():
        raise ValueError("Frozen asset leaf is not a fresh regular source")
    shutil.copyfile(source, destination)
    destination.chmod(0o444)
    if (destination.stat().st_size != source.stat().st_size
            or sha(destination) != sha(source)):
        raise ValueError("Frozen asset leaf differs from its source")


def manifest(root: Path, kind: str) -> dict:
    root.chmod(0o555)
    result = _observe_asset_manifest_shape(root=root, asset_kind=kind)
    proof = validate_asset_tree(manifest=result, root=root)
    try:
        return proof.manifest()
    finally:
        proof.close()


def main() -> int:
    if STAGE.exists():
        raise SystemExit("Frozen asset stage exists; inspect before retry")
    if check_source() != 0:
        raise SystemExit("Local model source inventory failed")
    inventory_path = SOURCE_MODEL / f".cache/huggingface/trees/{REVISION}.json"
    inventory = json.loads(inventory_path.read_text())["files"]
    if (len(inventory) != 14 or ".gitattributes" not in inventory
            or any("/" in name or (name.startswith(".") and name != ".gitattributes")
                   for name in inventory)):
        raise SystemExit("Unexpected model inventory shape")
    frozen_names = sorted(set(inventory) - {".gitattributes"})
    required = sum(int(inventory[name]["size"]) for name in frozen_names)
    if shutil.disk_usage(ROOT).free < required * 2:
        raise SystemExit("Insufficient external free space for verified copy")
    STAGE.mkdir(parents=True)
    MODEL.mkdir()
    PROMPT.mkdir()
    start = time.monotonic()
    status = {"state": "copying", "revision": REVISION,
              "source_files": len(inventory), "frozen_files": len(frozen_names)}
    (STAGE / "status.json").write_text(json.dumps(status, indent=2))
    try:
        for name in frozen_names:
            freeze_file(SOURCE_MODEL / name, MODEL / name)
        for name in ("prompt.txt", "raw-observation-schema.json"):
            freeze_file(PROMPT_SOURCE / name, PROMPT / name)
        if check_source() != 0:
            raise ValueError("Model source changed during copy")
        model_manifest = manifest(MODEL, "model")
        prompt_manifest = manifest(PROMPT, "prompt_schema")
        for kind, result in (("model", model_manifest), ("prompt", prompt_manifest)):
            target = REPO / f"docs/experiments/stage-a-frozen-{kind}-manifest-v1.json"
            if target.exists():
                raise ValueError("Frozen manifest destination exists")
            target.write_bytes(canonical_asset_manifest_shape_bytes(result))
        status.update(state="success", model_tree=model_manifest["root_tree_sha256"],
                      prompt_tree=prompt_manifest["root_tree_sha256"])
    except BaseException as error:
        status.update(state="failed", error_type=type(error).__name__)
        raise
    finally:
        status["elapsed_seconds"] = round(time.monotonic() - start, 3)
        (STAGE / "status.json").write_text(json.dumps(status, indent=2))
        print(json.dumps(status))
    return 0


if __name__ == "__main__":
    sys.exit(main())
