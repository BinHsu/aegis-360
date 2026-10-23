#!/usr/bin/env python3
"""Prepare a pinned, local-only Swift tokenizer source graph on T7."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path("/Volumes/T7/aegis-360-items")
STAGE = ROOT / "build/stage-a-tokenizer-1.3.0-v3"
SOURCES = {
    "swift-transformers": ("swift-transformers-1.3.0", "b38443e44d93eca770f2eb68e2a4d0fa100f9aa2"),
    "swift-jinja": ("swift-jinja-2.0.0", "1e6f84d6fca8ee93217b5594ce2025cbb0209c3a"),
    "swift-huggingface": ("swift-huggingface-0.9.0", "b721959445b617d0bf03910b2b4aced345fd93bf"),
    "swift-collections": ("swift-collections-1.7.2", "3b69cedbaa49957e97c092ae400bb57602ef941f"),
    "swift-crypto": ("swift-crypto-3.0.0", "629f0b679d0fd0a6ae823d7f750b9ab032c00b80"),
    "yyjson": ("yyjson-0.12.0", "8b4a38dc994a110abaec8a400615567bd996105f"),
    "EventSource": ("EventSource-1.3.0", "ca2a9d90cbe49e09b92f4b6ebd922c03ebea51d0"),
}


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()


def source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if ".git" in item.relative_to(path).parts:
            continue
        relative = item.relative_to(path).as_posix()
        if item.is_symlink():
            digest.update(f"L {relative} {os.readlink(item)}\n".encode())
        elif item.is_file():
            leaf = hashlib.sha256(item.read_bytes()).hexdigest()
            digest.update(f"F {relative} {leaf}\n".encode())
    return digest.hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text()
    if content.count(old) != 1:
        raise SystemExit(f"Expected exactly one manifest occurrence in {path.name}: {old}")
    path.write_text(content.replace(old, new))


def main() -> int:
    if not ROOT.is_dir() or STAGE.exists():
        raise SystemExit("T7 unavailable or tokenizer stage already exists")
    metadata = {}
    for name, (directory, commit) in SOURCES.items():
        source = ROOT / "sources" / directory
        if git(source, "rev-parse", "HEAD") != commit or git(source, "status", "--porcelain"):
            raise SystemExit(f"Pinned source checkout changed: {name}")
        metadata[name] = {"commit": commit, "tree": git(source, "rev-parse", "HEAD^{tree}"),
                          "source_digest": source_digest(source)}
    (STAGE / "packages").mkdir(parents=True)
    for name, (directory, _) in SOURCES.items():
        source = ROOT / "sources" / directory
        target = STAGE / "packages" / name
        shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns(".git"))
        if source_digest(target) != metadata[name]["source_digest"]:
            raise SystemExit(f"Copy mismatch: {name}")

    packages = STAGE / "packages"
    transformers = packages / "swift-transformers"
    (transformers / "Package@swift-6.1.swift").rename(transformers / "Package@swift-6.1.swift.disabled")
    manifest = transformers / "Package.swift"
    rewrites = {
        '.package(url: "https://github.com/huggingface/swift-jinja.git", from: "2.0.0")': '.package(path: "../swift-jinja")',
        '.package(url: "https://github.com/huggingface/swift-huggingface.git", from: "0.8.1")': '.package(path: "../swift-huggingface")',
        '.package(url: "https://github.com/apple/swift-collections.git", from: "1.0.0")': '.package(path: "../swift-collections")',
        '.package(url: "https://github.com/apple/swift-crypto.git", "3.0.0"..<"5.0.0")': '.package(path: "../swift-crypto")',
        '.package(url: "https://github.com/ibireme/yyjson.git", exact: "0.12.0")': '.package(path: "../yyjson")',
    }
    for old, new in rewrites.items():
        replace_once(manifest, old, new)

    huggingface = packages / "swift-huggingface"
    (huggingface / "Package@swift-6.0.swift").rename(huggingface / "Package@swift-6.0.swift.disabled")
    manifest = huggingface / "Package.swift"
    replace_once(manifest, '.package(url: "https://github.com/mattt/EventSource.git", from: "1.0.0")', '.package(path: "../EventSource")')
    replace_once(manifest, '.package(url: "https://github.com/apple/swift-crypto.git", "1.0.0" ..< "5.0.0")', '.package(path: "../swift-crypto")')
    replace_once(manifest, '        .package(url: "https://github.com/huggingface/swift-xet.git", from: "0.2.0"),\n', '')
    replace_once(manifest, '                .product(name: "Xet", package: "swift-xet", condition: .when(traits: ["Xet"])),\n', '')

    replace_once(packages / "swift-jinja/Package.swift",
                 '.package(url: "https://github.com/apple/swift-collections.git", from: "1.0.0")',
                 '.package(path: "../swift-collections")')
    for name in SOURCES:
        for path in (packages / name).glob("Package*.swift"):
            if ".package(url:" in path.read_text():
                raise SystemExit(f"Remote package reference remains: {name}/{path.name}")
    metadata["manifest_sha256"] = {
        name: hashlib.sha256((packages / name / "Package.swift").read_bytes()).hexdigest()
        for name in SOURCES
    }
    (STAGE / "source-manifest.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps({"stage": str(STAGE), "packages": sorted(SOURCES),
                      "manifest_sha256": metadata["manifest_sha256"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
