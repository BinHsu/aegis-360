#!/usr/bin/env python3
"""Freeze the six Stage A private packets from supplied local evidence; no media render."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import stat
import tempfile
import platform
import sys
import tomllib
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aegis360.context_views import build_context_view_grid  # noqa: E402
from aegis360.multi_signal_timeline import build_multi_signal_timeline  # noqa: E402
from aegis360.scene_change_candidates import build_scene_change_candidates  # noqa: E402
from aegis360.sparse_story_projection import (  # noqa: E402
    build_adapter_index, canonical_index_bytes, canonical_private_packet_bytes,
    index_sha256)
from aegis360.sparse_story_stage_a_lineage import (  # noqa: E402
    CENTERS, MANIFEST_SCHEMA, SOURCE_SLOTS, build_stage_a_private_packets)
from aegis360.sparse_story_stage_a_timeline_proof import (  # noqa: E402
    validate_stage_a_timeline_upstream)

_REPO = Path(__file__).resolve().parents[1]
_NAMES = ("old_ghost_road_360", "skiing_may_2019_360")


def _raw(value: object) -> bytes:
    return (json.dumps(value, allow_nan=False, ensure_ascii=True, sort_keys=True,
                       indent=2) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> tuple[dict, bytes]:
    raw = path.read_bytes()
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key in {path.name}")
            result[key] = value
        return result
    def bad(value):
        raise ValueError(f"nonfinite JSON in {path.name}: {value}")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=bad)
        json.dumps(value, allow_nan=False)
    except (UnicodeError, json.JSONDecodeError, OverflowError, TypeError) as error:
        raise ValueError(f"invalid JSON in {path.name}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON root in {path.name} must be object")
    return value, raw


def _source_hash(path: Path, expected_size: int, expected_sha: str) -> str:
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
        raise ValueError("benchmark source missing or size mismatch")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("benchmark source changed during hashing")
    if actual != expected_sha:
        raise ValueError("benchmark source SHA-256 mismatch")
    return actual


def _salt(path: Path) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
            raise ValueError("salt file must be owner-owned regular file with no group/other access")
        value = os.read(descriptor, 66)
    finally:
        os.close(descriptor)
    if value.endswith(b"\n"):
        value = value[:-1]
    if len(value) != 64 or any(c not in b"0123456789abcdef" for c in value):
        raise ValueError("salt file must contain exactly 64 lowercase hex characters")
    return value.decode("ascii")


def _fraction(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def _source_duration(asset: dict) -> Fraction:
    duration = Fraction(str(asset["reported_duration_seconds"]))
    if duration <= 0:
        raise ValueError("benchmark duration invalid")
    return duration


def _asset(manifest: dict, name: str) -> dict:
    rows = [row for row in manifest.get("asset", ()) if row.get("id") == name]
    if len(rows) != 1:
        raise ValueError("benchmark manifest asset missing or duplicated")
    row = rows[0]
    if (not isinstance(row.get("byte_size"), int) or row["byte_size"] <= 0
            or not isinstance(row.get("sha256"), str) or len(row["sha256"]) != 64):
        raise ValueError("benchmark manifest source declaration invalid")
    return row


def prepare_bundle(*, old_source: Path, old_grid: Path, old_scenes: Path,
                   old_timeline: Path, ski_source: Path, ski_scene_events: Path,
                   salt_file: Path, benchmark_manifest: Path = _REPO / "benchmarks/manifest.toml") -> tuple[dict[str, bytes], dict[str, object]]:
    """Pure prepublication preparation, apart from bounded local input reads."""
    manifest = tomllib.loads(benchmark_manifest.read_text(encoding="utf-8"))
    old_asset, ski_asset = (_asset(manifest, name) for name in _NAMES)
    old_sha = _source_hash(old_source, old_asset["byte_size"], old_asset["sha256"])
    ski_sha = _source_hash(ski_source, ski_asset["byte_size"], ski_asset["sha256"])
    old_grid_doc, old_grid_raw = _read_json(old_grid)
    old_scenes_doc, old_scenes_raw = _read_json(old_scenes)
    old_timeline_doc, old_timeline_raw = _read_json(old_timeline)
    old_id = old_grid_doc.get("source_id")
    if old_timeline_doc.get("source_id") != old_id or old_scenes_doc.get("source_id") != old_id:
        raise ValueError("Old Ghost upstream source IDs differ")
    validate_stage_a_timeline_upstream(grid_bytes=old_grid_raw,
        scene_candidates_bytes=old_scenes_raw, timeline_bytes=old_timeline_raw,
        timeline_sha256=_sha(old_timeline_raw))
    ski_events, ski_events_raw = _read_json(ski_scene_events)
    if (ski_events.get("schema_version") != "aegis360.ffmpeg-scene-events.v1"
            or ski_events.get("source_sha256") != ski_sha
            or not isinstance(ski_events.get("source_id"), str)
            or not isinstance(ski_events.get("config"), dict)
            or ski_events["config"].get("sample_fps") != 10.0
            or not isinstance(ski_events.get("events"), list)):
        raise ValueError("Skiing input is not the declared 10-fps scene evidence")
    ski_id = ski_events["source_id"]
    ski_grid_doc = build_context_view_grid(source_id=ski_id, start_seconds=0,
                                           duration_seconds=float(_source_duration(ski_asset)))
    ski_grid_raw = _raw(ski_grid_doc)
    ski_scenes_doc = build_scene_change_candidates(
        ski_events, scene_events_sha256=_sha(ski_events_raw),
        score_floor=0.25, minimum_separation_seconds=1.0)
    if ski_scenes_doc["candidates"]:
        raise ValueError("Skiing 10-fps scene evidence has nonzero selected candidates")
    ski_scenes_raw = _raw(ski_scenes_doc)
    ski_timeline_doc = build_multi_signal_timeline(ski_grid_doc, ski_scenes_doc,
        grid_sha256=_sha(ski_grid_raw), scene_candidates_sha256=_sha(ski_scenes_raw))
    ski_timeline_raw = _raw(ski_timeline_doc)
    validate_stage_a_timeline_upstream(grid_bytes=ski_grid_raw,
        scene_candidates_bytes=ski_scenes_raw, timeline_bytes=ski_timeline_raw,
        timeline_sha256=_sha(ski_timeline_raw))
    events = [event for event in old_timeline_doc["events"]
              if event.get("event_id") == "event:multi:0023"]
    if len(events) != 1 or not any(signal.get("signal_id") == "event:scene-change:0024"
                                    for signal in events[0]["signals"]):
        raise ValueError("Old Ghost frozen proposal event/signal missing")
    sources = [{"source_id": source_id, "source_sha256": source_sha,
                "duration": _fraction(_source_duration(asset))}
               for source_id, source_sha, asset in
               ((old_id, old_sha, old_asset), (ski_id, ski_sha, ski_asset))]
    grids = (old_grid_doc, ski_grid_doc)
    grid_bytes = (old_grid_raw, ski_grid_raw)
    timelines = (old_timeline_doc, ski_timeline_doc)
    timeline_bytes = (old_timeline_raw, ski_timeline_raw)
    execution = {"schema_version": MANIFEST_SCHEMA,
        "sources": [{"source_id": source["source_id"],
                     "source_sha256": source["source_sha256"],
                     "event_timeline_sha256": _sha(timeline_raw),
                     "context_view_grid_sha256": _sha(grid_raw)}
                    for source, timeline_raw, grid_raw in zip(sources, timeline_bytes, grid_bytes)],
        "selections": [{"source_id": sources[slot]["source_id"],
                        "role": "proposal" if number == 0 else "control",
                        "original_event_id": "event:multi:0023" if number == 0 else None,
                        "original_signal_ids": ["event:scene-change:0024"] if number == 0 else [],
                        "center_source_time": _fraction(center)}
                       for number, (slot, center) in enumerate(zip(SOURCE_SLOTS, CENTERS))]}
    execution_raw = _raw(execution)
    packets, hashes = build_stage_a_private_packets(
        execution_manifest=execution, execution_manifest_bytes=execution_raw,
        sources=sources, timelines=timelines, timeline_bytes=timeline_bytes,
        grids=grids, grid_bytes=grid_bytes)
    index = build_adapter_index(private_packets=packets,
                                ordered_private_packet_sha256s=hashes,
                                salt_hex=_salt(salt_file))
    # Recheck content, not only metadata, before any publication decision.
    _source_hash(old_source, old_asset["byte_size"], old_sha)
    _source_hash(ski_source, ski_asset["byte_size"], ski_sha)
    # A private bundle contains no source media, pixels, model, labels or salt.
    files = {"execution-manifest.json": execution_raw,
             "adapter-index.json": canonical_index_bytes(index),
             "old-grid.json": old_grid_raw, "old-scene-candidates.json": old_scenes_raw,
             "old-timeline.json": old_timeline_raw,
             "ski-grid.json": ski_grid_raw, "ski-scene-candidates.json": ski_scenes_raw,
             "ski-timeline.json": ski_timeline_raw}
    for number, packet in enumerate(packets, 1):
        files[f"private-packet-{number:02d}.json"] = canonical_private_packet_bytes(packet)
    # Link the predecessor's exact bytes without exposing their paths.
    summary = {"source_count": 2, "packet_count": len(packets),
               "proposal_count": 1, "control_count": 5,
               "source_sha256s": [old_sha, ski_sha],
               "ski_scene_events_sha256": _sha(ski_events_raw),
               "execution_manifest_sha256": _sha(execution_raw),
               "adapter_index_sha256": index_sha256(index),
               "file_sha256s": {name: _sha(payload) for name, payload in sorted(files.items())}}
    return files, summary


def _exclusive_rename(source: Path, destination: Path) -> None:
    """Atomic directory rename that refuses an existing destination."""
    libc = ctypes.CDLL(None, use_errno=True)
    system = platform.system()
    if system == "Darwin":
        rename = libc.renameatx_np
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                           ctypes.c_char_p, ctypes.c_uint)
        arguments = (-2, os.fsencode(source), -2, os.fsencode(destination), 0x4)
    elif system == "Linux":
        rename = libc.renameat2
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                           ctypes.c_char_p, ctypes.c_uint)
        arguments = (-100, os.fsencode(source), -100, os.fsencode(destination), 0x1)
    else:
        raise ValueError("exclusive atomic directory rename unavailable on this host")
    rename.restype = ctypes.c_int
    if rename(*arguments) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def publish_bundle(output_root: Path, files: dict[str, bytes]) -> None:
    """Stage exact files, then atomically publish a new directory only."""
    if not output_root.parent.is_dir():
        raise ValueError("output parent must exist")
    if output_root.exists() or output_root.is_symlink():
        raise FileExistsError("refusing to overwrite output root")
    staged = Path(tempfile.mkdtemp(prefix=".stage-a-preflight-", dir=output_root.parent))
    identity = staged.lstat()
    written = []
    published = False
    try:
        for name, payload in sorted(files.items()):
            if Path(name).name != name or not isinstance(payload, bytes):
                raise ValueError("bundle member name or payload invalid")
            target = staged / name
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            written.append((name, os.fstat(descriptor), payload))
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        for name, metadata, payload in written:
            target = staged / name
            now = target.lstat()
            if (now.st_dev, now.st_ino) != (metadata.st_dev, metadata.st_ino) or target.read_bytes() != payload:
                raise ValueError("staged bundle bytes changed during readback")
        directory_descriptor = os.open(staged, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
        _exclusive_rename(staged, output_root)
        published = True
        for name, _, payload in written:
            if (output_root / name).read_bytes() != payload:
                raise ValueError("published bundle bytes changed during readback")
    finally:
        if not published and staged.is_dir() and not staged.is_symlink():
            now = staged.lstat()
            if (now.st_dev, now.st_ino) == (identity.st_dev, identity.st_ino):
                for name, metadata, _ in written:
                    target = staged / name
                    if target.exists() and not target.is_symlink():
                        current = target.lstat()
                        if (current.st_dev, current.st_ino) == (metadata.st_dev, metadata.st_ino):
                            target.unlink()
                try:
                    staged.rmdir()
                except OSError:
                    pass


def main(argv: list[str] | None = None, *,
         benchmark_manifest: Path = _REPO / "benchmarks/manifest.toml") -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("old-source", "old-grid", "old-scenes", "old-timeline",
                 "ski-source", "ski-scene-events", "salt-file", "output-root"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        files, summary = prepare_bundle(old_source=args.old_source, old_grid=args.old_grid,
            old_scenes=args.old_scenes, old_timeline=args.old_timeline,
            ski_source=args.ski_source, ski_scene_events=args.ski_scene_events,
            salt_file=args.salt_file, benchmark_manifest=benchmark_manifest)
        if args.output_root.exists() or args.output_root.is_symlink():
            raise ValueError("refusing to overwrite output root")
        if not args.dry_run:
            publish_bundle(args.output_root, files)
        print(json.dumps(summary, sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Stage A preflight failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
