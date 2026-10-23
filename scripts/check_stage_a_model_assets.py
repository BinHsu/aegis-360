#!/usr/bin/env python3
"""Verify the pinned local SmolVLM2 asset tree against its cached revision inventory."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tomllib


REVISION = "844516024a1c4400d34489b89ee067d794e432ed"
ROOT = Path("/Volumes/T7/aegis-360-items/models/smolvlm2-2.2b-instruct-mlx-bf16")
REPO = Path(__file__).resolve().parents[1]


def hashes(path: Path) -> tuple[str, str, int]:
    size = path.stat().st_size
    git = hashlib.sha1(f"blob {size}\0".encode())
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            git.update(chunk)
            sha.update(chunk)
    return git.hexdigest(), sha.hexdigest(), size


def main() -> int:
    manifest = tomllib.loads((REPO / "model-manifests/manifest.toml").read_text())
    model = next(row for row in manifest["model"] if row["id"] == "smolvlm2_2_2b_instruct_mlx_bf16")
    if model["conversion_revision"] != REVISION:
        raise SystemExit("Pinned model revision changed")
    inventory = json.loads((ROOT / f".cache/huggingface/trees/{REVISION}.json").read_text())["files"]
    present = {
        path.relative_to(ROOT).as_posix(): path
        for path in ROOT.iterdir() if path.is_file() or path.is_symlink()
    }
    if set(present) != set(inventory):
        raise SystemExit(f"Asset names differ: missing={sorted(set(inventory)-set(present))}, extra={sorted(set(present)-set(inventory))}")
    digest = hashlib.sha256()
    for name in sorted(inventory):
        path = present[name]
        if path.is_symlink():
            raise SystemExit(f"Symlink asset: {name}")
        git, sha, size = hashes(path)
        expected = inventory[name]
        if size != expected["size"]:
            raise SystemExit(f"Size mismatch: {name}")
        if "lfs_sha256" in expected:
            if sha != expected["lfs_sha256"]:
                raise SystemExit(f"LFS hash mismatch: {name}")
        elif git != expected["blob_id"]:
            raise SystemExit(f"Git blob mismatch: {name}")
        if name == model["filename"] and (sha != model["sha256"] or size != model["byte_size"]):
            raise SystemExit("Repository weight manifest mismatch")
        digest.update(f"{name} {size} {sha}\n".encode())
    print(json.dumps({"revision": REVISION, "files": len(inventory), "tree_digest": digest.hexdigest()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
