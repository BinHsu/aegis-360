#!/usr/bin/env python3
"""Render the frozen Stage A rows into a local closed, sanitized media gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_media_tree import (  # noqa: E402
    build_result, canonical_result_bytes, publish_sanitized_media_gate,
    sanitize_png_bytes)
from aegis360.sparse_story_projection import (  # noqa: E402
    canonical_index_bytes, private_packet_sha256)
from aegis360.sparse_story_stage_a_render import render_stage_a_payloads  # noqa: E402
from build_stage_a_preflight_bundle import _salt, prepare_bundle  # noqa: E402


def validate_output_placement(output_root: Path, data_root: Path) -> None:
    if (not output_root.is_absolute() or not data_root.is_absolute()
            or not data_root.is_dir() or data_root.is_symlink()):
        raise ValueError("external data root and output must be absolute directories")
    resolved_data = data_root.resolve(strict=True)
    resolved_output = output_root.resolve(strict=False)
    if resolved_output == resolved_data or not resolved_output.is_relative_to(resolved_data):
        raise ValueError("media output must be under the external data root")


def preview_hashes(index: dict, payloads: list[tuple[str, bytes]]) -> tuple[str, str]:
    leaves = {"adapter-index.json": canonical_index_bytes(index)}
    inputs = []
    for ref, payload in payloads:
        if ref in leaves:
            raise ValueError("duplicate media ref in prepublication preview")
        leaves[ref] = sanitize_png_bytes(payload)
        inputs.append((ref, hashlib.sha256(payload).hexdigest()))
    if len(inputs) != 36:
        raise ValueError("Stage A prepublication preview needs 36 images")
    lines = [f"{hashlib.sha256(leaves[ref]).hexdigest()}  {ref}\n"
             for ref in sorted(leaves, key=lambda value: value.encode("utf-8"))]
    tree_sha = hashlib.sha256("".join(lines).encode()).hexdigest()
    result_bytes = canonical_result_bytes(build_result(
        adapter_index_sha256=hashlib.sha256(leaves["adapter-index.json"]).hexdigest(),
        input_payloads=sorted(inputs, key=lambda value: value[0].encode("utf-8")),
        bundle_tree_sha256=tree_sha))
    return tree_sha, hashlib.sha256(result_bytes).hexdigest()


def run(*, preflight_root: Path, old_source: Path, old_grid: Path,
        old_scenes: Path, old_timeline: Path, ski_source: Path,
        ski_scene_events: Path, salt_file: Path, output_root: Path,
        benchmark_manifest: Path = ROOT / "benchmarks/manifest.toml",
        expected_tree_sha256: str | None = None,
        expected_result_sha256: str | None = None) -> dict[str, object]:
    if (expected_tree_sha256 is None) != (expected_result_sha256 is None):
        raise ValueError("both expected output hashes are required together")
    if output_root.exists() or output_root.is_symlink():
        raise ValueError("refusing to overwrite media output root")
    if not output_root.parent.is_dir():
        raise ValueError("media output parent must already exist")
    files, summary = prepare_bundle(old_source=old_source, old_grid=old_grid,
        old_scenes=old_scenes, old_timeline=old_timeline,
        ski_source=ski_source, ski_scene_events=ski_scene_events,
        salt_file=salt_file, benchmark_manifest=benchmark_manifest)
    if (not preflight_root.is_dir() or preflight_root.is_symlink()
            or {p.name for p in preflight_root.iterdir()} != set(files)):
        raise ValueError("published preflight bundle scope differs")
    for name, expected in files.items():
        path = preflight_root / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != expected:
            raise ValueError("published preflight bundle differs from exact rebuild")
    index = json.loads(files["adapter-index.json"])
    packets = [json.loads(files[f"private-packet-{number:02d}.json"])
               for number in range(1, 7)]
    packet_hashes = [private_packet_sha256(packet) for packet in packets]
    source_ids = [source["source_id"] for source in
                  json.loads(files["execution-manifest.json"])["sources"]]
    if len(source_ids) != 2 or source_ids[0] == source_ids[1]:
        raise ValueError("published source pair is invalid")
    payloads = render_stage_a_payloads(index=index, private_packets=packets,
        ordered_private_packet_sha256s=packet_hashes, salt_hex=_salt(salt_file),
        source_by_id={source_ids[0]: old_source, source_ids[1]: ski_source})
    preview_tree, preview_result = preview_hashes(index, payloads)
    if expected_tree_sha256 is not None and (
            preview_tree != expected_tree_sha256
            or preview_result != expected_result_sha256):
        raise ValueError("rendered output differs from approved prepublication hashes")
    # The output is local and ignored by Git. The closed gate publishes two
    # exclusive peers, then revalidates their exact content and identity.
    output_root.mkdir(mode=0o700)
    owned = output_root.stat()
    try:
        result_sha = publish_sanitized_media_gate(index=index,
            private_packets=packets, ordered_private_packet_sha256s=packet_hashes,
            salt_hex=_salt(salt_file), payloads=payloads,
            bundle_destination=output_root / "bundle",
            result_destination=output_root / "result.json")
    except BaseException:
        current = output_root.stat()
        if ((current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino)
                and not any(output_root.iterdir())):
            os.rmdir(output_root)
        raise
    result = json.loads((output_root / "result.json").read_bytes())
    if (result["outputs"]["bundle_tree_sha256"] != preview_tree
            or result_sha != preview_result):
        raise ValueError("published output differs from prepublication preview")
    return {"packet_count": len(packets), "media_file_count": len(payloads),
        "adapter_index_sha256": summary["adapter_index_sha256"],
        "execution_manifest_sha256": summary["execution_manifest_sha256"],
        "bundle_tree_sha256": result["outputs"]["bundle_tree_sha256"],
        "result_sha256": result_sha}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    for name in ("preflight-root", "old-source", "old-grid", "old-scenes",
                 "old-timeline", "ski-source", "ski-scene-events",
                 "salt-file", "output-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--expected-tree-sha256")
    parser.add_argument("--expected-result-sha256")
    args = parser.parse_args()
    try:
        validate_output_placement(args.output_root, args.data_root)
        inputs = vars(args).copy(); inputs.pop("data_root")
        report = run(**inputs)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Stage A media preflight failed: {error}\n")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
