#!/usr/bin/env python3
"""Verify externally stored model assets without downloading anything."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import tomllib


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("data_root", type=Path)
    args = parser.parse_args()
    document = tomllib.loads(args.manifest.read_text(encoding="utf-8"))
    if document.get("implicit_downloads_allowed") is not False:
        parser.error("model manifest must prohibit implicit downloads")
    models = document.get("model")
    if not isinstance(models, list) or not models:
        parser.error("model manifest contains no models")
    failed = False
    seen: set[str] = set()
    for model in models:
        model_id = model.get("id")
        relative = model.get("relative_path")
        expected_hash = model.get("sha256")
        expected_bytes = model.get("byte_size")
        if (
            not isinstance(model_id, str) or not model_id
            or model_id in seen
            or not isinstance(relative, str) or not relative
            or Path(relative).is_absolute() or ".." in Path(relative).parts
            or not isinstance(expected_hash, str) or len(expected_hash) != 64
            or not isinstance(expected_bytes, int) or expected_bytes <= 0
        ):
            parser.error("invalid or duplicate model manifest entry")
        seen.add(model_id)
        path = args.data_root / relative
        if not path.is_file():
            print(f"MISSING {model_id}: {path}", file=sys.stderr)
            failed = True
            continue
        actual_bytes = path.stat().st_size
        actual_hash = sha256(path)
        if actual_bytes != expected_bytes or actual_hash != expected_hash:
            print(
                f"MISMATCH {model_id}: bytes={actual_bytes} sha256={actual_hash}",
                file=sys.stderr,
            )
            failed = True
            continue
        print(f"VERIFIED {model_id}: {relative}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
