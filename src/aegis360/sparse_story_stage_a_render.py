"""Trusted, bounded FFmpeg acquisition of Stage A row PNG payloads.

This produces private in-memory payloads for the closed media-tree publisher.
It grants no model or semantic authority.
"""

from __future__ import annotations

import hashlib
import selectors
import subprocess
import time
from fractions import Fraction
from pathlib import Path
from typing import Mapping, Sequence

from .sparse_story_media_tree import sanitize_png_bytes
from .sparse_story_projection import (
    private_packet_sha256, validate_adapter_index, validate_private_packet,
)


MAX_PNG_BYTES = 16 * 1024 * 1024


def _decimal(value: Mapping[str, int]) -> str:
    fraction = Fraction(value["numerator"], value["denominator"])
    denominator = fraction.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2; twos += 1
    while denominator % 5 == 0:
        denominator //= 5; fives += 1
    if denominator != 1:
        raise ValueError("source time has no exact decimal representation")
    places = max(twos, fives)
    scaled = fraction.numerator * (10 ** places) // fraction.denominator
    digits = str(scaled).rjust(places + 1, "0")
    return digits if places == 0 else digits[:-places] + "." + digits[-places:]


def _filter(views: Sequence[Mapping[str, object]]) -> str:
    if len(views) != 4:
        raise ValueError("row needs exactly four cardinal views")
    parts = ["[0:v:0]split=4[in0][in1][in2][in3]"]
    for number, view in enumerate(views):
        parts.append(
            f"[in{number}]v360=input=equirect:output=flat:w=480:h=270:"
            f"yaw={view['yaw_degrees']:g}:pitch={view['pitch_degrees']:g}:"
            f"h_fov={view['horizontal_fov_degrees']:g}:interp=linear[v{number}]"
        )
    parts.append("[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|480_0|0_270|480_270,format=rgb24[out]")
    return ";".join(parts)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _capture_png(command: list[str]) -> bytes:
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
        try:
            output = bytearray(); deadline = time.monotonic() + 90
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        raise ValueError("Stage A row render timed out")
                    block = process.stdout.read1(min(65536, MAX_PNG_BYTES + 1 - len(output)))
                    if not block:
                        selector.unregister(process.stdout)
                    else:
                        output.extend(block)
                        if len(output) > MAX_PNG_BYTES:
                            raise ValueError("Stage A row PNG exceeds bound")
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except (ValueError, subprocess.TimeoutExpired):
            process.kill(); process.wait()
            raise ValueError("Stage A row render failed or exceeded bound") from None
        if process.returncode != 0 or len(output) > MAX_PNG_BYTES:
            raise ValueError("Stage A row render failed or exceeded byte bound")
        return bytes(output)
    except OSError:
        raise ValueError("Stage A row render could not start") from None


def render_stage_a_payloads(*, index: Mapping[str, object],
        private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], salt_hex: str,
        source_by_id: Mapping[str, Path], ffmpeg: str = "ffmpeg") -> list[tuple[str, bytes]]:
    """Render 36 rows serially, binding source bytes before and after use."""
    validate_adapter_index(index, private_packets=private_packets,
        ordered_private_packet_sha256s=ordered_private_packet_sha256s,
        salt_hex=salt_hex)
    if set(source_by_id) != {packet["source_id"] for packet in private_packets}:
        raise ValueError("source map does not match packet set")
    source_hashes = {}
    for packet in private_packets:
        validate_private_packet(packet)
        source_id = packet["source_id"]
        expected = packet["inputs"]["source_sha256"]
        if source_id in source_hashes and source_hashes[source_id] != expected:
            raise ValueError("source hash declarations disagree")
        source_hashes[source_id] = expected
    for source_id, expected in source_hashes.items():
        if _hash_file(source_by_id[source_id]) != expected:
            raise ValueError("source hash mismatch before rendering")
    projections = {item["projection"]["packet_id"]: item["projection"]
                   for item in index["packets"]}
    payloads = []
    for packet, packet_hash in zip(private_packets, ordered_private_packet_sha256s):
        if private_packet_sha256(packet) != packet_hash:
            raise ValueError("private packet changed")
        # The one-packet derivation uses the same opaque ID as the full index.
        from .sparse_story_projection import build_adapter_index
        projection = build_adapter_index(private_packets=[packet],
            ordered_private_packet_sha256s=[packet_hash], salt_hex=salt_hex)["packets"][0]["projection"]
        public = projections[projection["packet_id"]]
        for private_row, public_row in zip(packet["rows"], public["rows"]):
            command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
                "-ss", _decimal(private_row["absolute_source_time"]),
                "-i", str(source_by_id[packet["source_id"]]), "-frames:v", "1",
                "-filter_complex", _filter(private_row["cardinal_views"]),
                "-map", "[out]", "-an", "-c:v", "png", "-f", "image2pipe", "pipe:1"]
            payloads.append((public_row["media_ref"], sanitize_png_bytes(_capture_png(command))))
    for source_id, expected in source_hashes.items():
        if _hash_file(source_by_id[source_id]) != expected:
            raise ValueError("source hash mismatch after rendering")
    return payloads
