"""Fail-closed renderer for transient blind chapter-review packets."""

from __future__ import annotations

import binascii
import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Mapping, Sequence

from aegis360.blind_chapter_review_schedule import (
    validate_exact_blind_chapter_review_schedule,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xffffffff)


def sanitize_png(path: Path, *, expected_width: int, expected_height: int) -> None:
    """Retain only image-bearing PNG chunks, rejecting malformed output."""
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("renderer did not produce PNG data")
    offset = len(PNG_SIGNATURE)
    kept: list[tuple[bytes, bytes]] = []
    seen_ihdr = seen_iend = False
    idat_count = 0
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError("truncated PNG payload")
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = struct.unpack(">I", data[offset + 8 + size:end])[0]
        if (binascii.crc32(kind + payload) & 0xffffffff) != crc:
            raise ValueError("PNG checksum mismatch")
        if kind == b"IHDR":
            if seen_ihdr or len(payload) != 13 or kept:
                raise ValueError("invalid PNG header")
            width, height = struct.unpack(">II", payload[:8])
            if (width, height) != (expected_width, expected_height):
                raise ValueError("renderer PNG dimensions do not match the contract")
            if (payload[8], payload[9], payload[10], payload[11], payload[12]) not in {
                    (8, 2, 0, 0, 0), (8, 6, 0, 0, 0)}:
                raise ValueError("renderer PNG pixel format is not metadata-free RGB/RGBA")
            seen_ihdr = True
            kept.append((kind, payload))
        elif kind == b"IDAT":
            if not seen_ihdr or seen_iend:
                raise ValueError("invalid PNG image-data order")
            idat_count += 1
            kept.append((kind, payload))
        elif kind == b"IEND":
            if not seen_ihdr or seen_iend or payload:
                raise ValueError("invalid PNG end chunk")
            seen_iend = True
            kept.append((kind, payload))
            if end != len(data):
                raise ValueError("trailing PNG data is forbidden")
        offset = end
    if not seen_ihdr or not seen_iend or idat_count == 0:
        raise ValueError("incomplete PNG output")
    sanitized = PNG_SIGNATURE + b"".join(_png_chunk(kind, payload) for kind, payload in kept)
    path.write_bytes(sanitized)


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _filter(mapping: Sequence[Mapping[str, object]], panel_width: int, panel_height: int) -> str:
    if len(mapping) != 4:
        raise ValueError("exactly four private cardinal mappings are required")
    parts = ["[0:v:0]split=4[in0][in1][in2][in3]"]
    for index, view in enumerate(mapping):
        parts.append(
            f"[in{index}]v360=input=equirect:output=flat:w={panel_width}:h={panel_height}:"
            f"yaw={float(view['yaw_degrees']):g}:pitch={float(view['pitch_degrees']):g}:"
            f"h_fov={float(view['horizontal_fov_degrees']):g}[view{index}]"
        )
    parts.append(
        f"[view0][view1][view2][view3]xstack=inputs=4:"
        f"layout=0_0|{panel_width}_0|0_{panel_height}|{panel_width}_{panel_height}[out]"
    )
    return ";".join(parts)


def render_blind_chapter_review_bundle(
    *, private_schedule_path: Path, public_index_path: Path,
    proposals_path: Path, config_path: Path, presentation_salt_path: Path,
    render_media_path: Path, output_directory: Path,
    proposals_sha256: str, source_sha256: str, policy_sha256: str,
    protocol_sha256: str, render_media_sha256: str,
    panel_width: int = 480, panel_height: int = 270,
    ffmpeg: str = "ffmpeg",
) -> dict[str, int]:
    """Exact-validate inputs, render neutral refs, and atomically publish."""
    paths = [private_schedule_path, public_index_path, proposals_path,
             config_path, presentation_salt_path, render_media_path]
    if any(not path.is_file() for path in paths):
        raise ValueError("a required blind-render input is missing")
    if output_directory.exists():
        raise ValueError("refusing to overwrite output directory")
    if panel_width <= 0 or panel_height <= 0 or panel_width % 2 or panel_height % 2:
        raise ValueError("panel dimensions must be positive even integers")
    salt_bytes = presentation_salt_path.read_bytes()
    if (len(salt_bytes) != 65 or salt_bytes[-1:] != b"\n"
            or any(byte not in b"0123456789abcdef" for byte in salt_bytes[:-1])):
        raise ValueError("presentation salt file must contain exactly one lowercase 64-hex line")
    private = _load_json(private_schedule_path)
    public = _load_json(public_index_path)
    proposals = _load_json(proposals_path)
    config = _load_json(config_path)
    config_sha256 = sha256_file(config_path)
    if sha256_file(proposals_path) != proposals_sha256:
        raise ValueError("chapter proposal file hash does not match")
    if sha256_file(render_media_path) != render_media_sha256:
        raise ValueError("render media file hash does not match")
    validate_exact_blind_chapter_review_schedule(
        private, public, proposals=proposals, proposals_sha256=proposals_sha256,
        source_sha256=source_sha256, policy_sha256=policy_sha256,
        protocol_sha256=protocol_sha256, config=config,
        config_sha256=config_sha256,
        presentation_salt_hex=salt_bytes[:-1].decode("ascii"),
    )
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent))
    try:
        # Serialize the validated public object; never copy coordinator files.
        (stage / "public-reviewer-index.json").write_text(
            json.dumps(public, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        rendered = 0
        for entry, packet in zip(private["entries"], public["packets"]):
            if entry["packet_id"] != packet["packet_id"]:
                raise ValueError("private/public packet mapping changed after validation")
            for private_row, public_row in zip(entry["rows"], packet["rows"]):
                relative = Path(public_row["media_ref"])
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                command = [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-ss", f"{private_row['absolute_proxy_time_seconds']:.9f}",
                    "-i", str(render_media_path), "-frames:v", "1",
                    "-filter_complex", _filter(private_row["cardinal_mapping"], panel_width, panel_height),
                    "-map", "[out]", "-an", "-c:v", "png", str(destination),
                ]
                try:
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE)
                except subprocess.CalledProcessError:
                    raise ValueError("media renderer failed") from None
                sanitize_png(destination, expected_width=panel_width * 2,
                             expected_height=panel_height * 2)
                rendered += 1
        expected_refs = {
            row["media_ref"] for packet in public["packets"] for row in packet["rows"]
        }
        actual_refs = {
            path.relative_to(stage).as_posix() for path in (stage / "media").rglob("*.png")
        }
        if actual_refs != expected_refs:
            raise ValueError("public media references are incomplete or contain extras")
        os.rename(stage, output_directory)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {"packet_count": len(public["packets"]), "row_count": rendered}
