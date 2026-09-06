"""Sanitized renderer and canonical tree proof for structural blind review."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from fractions import Fraction
from pathlib import Path, PurePosixPath
from typing import Mapping

from .blind_chapter_review_renderer import sanitize_png
from .structural_blind_schedule import (
    CONFIG_SHA256, PROOF_SHA256, validate_exact_schedule,
)


SHA = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _refs(public_index: Mapping[str, object]) -> set[str]:
    try:
        refs = [row["media_ref"] for packet in public_index["packets"]
                for row in packet["rows"]]
    except (KeyError, TypeError):
        raise ValueError("public reviewer media references are invalid") from None
    if len(refs) != 48 or len(set(refs)) != 48:
        raise ValueError("public reviewer media references are incomplete")
    for ref in refs:
        path = PurePosixPath(ref)
        if (not isinstance(ref, str) or path.is_absolute() or ".." in path.parts
                or path.as_posix() != ref or not ref.startswith("media/")
                or not ref.endswith(".png")):
            raise ValueError("public reviewer media reference is unsafe")
    return set(refs)


def canonical_bundle_tree_sha256(bundle_directory: Path,
                                 public_index: Mapping[str, object]) -> str:
    expected = {"public-reviewer-index.json", *_refs(public_index)}
    if not bundle_directory.is_dir() or bundle_directory.is_symlink():
        raise ValueError("review bundle directory is invalid")
    actual = set()
    for path in bundle_directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("review bundle symlinks are forbidden")
        if path.is_file():
            actual.add(path.relative_to(bundle_directory).as_posix())
    if actual != expected:
        raise ValueError("review bundle files do not match the closed tree scope")
    lines = []
    for relative in sorted(expected):
        path = bundle_directory / PurePosixPath(relative)
        if path.is_symlink() or not path.is_file():
            raise ValueError("review bundle scoped file is not regular")
        lines.append(f"{sha256_file(path)}  {relative}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def validate_canonical_bundle_tree(bundle_directory: Path,
                                   public_index: Mapping[str, object],
                                   expected_sha256: str) -> None:
    if SHA.fullmatch(expected_sha256 or "") is None:
        raise ValueError("bundle tree checksum is invalid")
    if canonical_bundle_tree_sha256(bundle_directory, public_index) != expected_sha256:
        raise ValueError("bundle tree checksum does not match")


def _terminating_decimal(value: Mapping[str, int]) -> str:
    fraction = Fraction(value["numerator"], value["denominator"])
    denominator = fraction.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2; twos += 1
    while denominator % 5 == 0:
        denominator //= 5; fives += 1
    if denominator != 1:
        raise ValueError("render time is not a terminating base-10 rational")
    places = max(twos, fives)
    scaled = fraction.numerator * (10 ** places) // fraction.denominator
    sign = "-" if scaled < 0 else ""
    digits = str(abs(scaled)).rjust(places + 1, "0")
    if places == 0:
        return sign + digits
    result = sign + digits[:-places] + "." + digits[-places:]
    return result.rstrip("0").rstrip(".")


def _filter(views, width, height):
    if len(views) != 4:
        raise ValueError("renderer requires four cardinal views")
    parts = ["[0:v:0]split=4[in0][in1][in2][in3]"]
    for index, view in enumerate(views):
        parts.append(f"[in{index}]v360=input=equirect:output=flat:w={width}:h={height}:yaw={float(view['yaw_degrees']):g}:pitch={float(view['pitch_degrees']):g}:h_fov={float(view['horizontal_fov_degrees']):g}[v{index}]")
    parts.append(f"[v0][v1][v2][v3]xstack=inputs=4:layout=0_0|{width}_0|0_{height}|{width}_{height}[out]")
    return ";".join(parts)


def render_structural_blind_bundle(*, private_schedule_path: Path,
        private_schedule_sha256: str, public_index_path: Path,
        public_index_sha256: str, selection_proof_path: Path,
        config_path: Path, presentation_salt_path: Path,
        render_media_path: Path, render_media_sha256: str,
        output_directory: Path, ffmpeg: str = "ffmpeg") -> dict[str, object]:
    paths = (private_schedule_path, public_index_path, selection_proof_path,
             config_path, presentation_salt_path, render_media_path)
    if any(not path.is_file() for path in paths) or output_directory.exists():
        raise ValueError("required render input is missing or output exists")
    if any(SHA.fullmatch(value or "") is None for value in
           (private_schedule_sha256, public_index_sha256, render_media_sha256)):
        raise ValueError("render input checksum is invalid")
    raw = {"private": private_schedule_path.read_bytes(),
           "public": public_index_path.read_bytes(),
           "proof": selection_proof_path.read_bytes(),
           "config": config_path.read_bytes(),
           "salt": presentation_salt_path.read_bytes()}
    if (hashlib.sha256(raw["private"]).hexdigest() != private_schedule_sha256
            or hashlib.sha256(raw["public"]).hexdigest() != public_index_sha256
            or hashlib.sha256(raw["proof"]).hexdigest() != PROOF_SHA256
            or hashlib.sha256(raw["config"]).hexdigest() != CONFIG_SHA256
            or sha256_file(render_media_path) != render_media_sha256):
        raise ValueError("render input checksum does not match")
    if (len(raw["salt"]) != 65 or raw["salt"][-1:] != b"\n"
            or any(byte not in b"0123456789abcdef" for byte in raw["salt"][:-1])
            or stat.S_IMODE(presentation_salt_path.stat().st_mode) & 0o077):
        raise ValueError("presentation salt format is invalid")
    try:
        private, public = json.loads(raw["private"]), json.loads(raw["public"])
        proof, config = json.loads(raw["proof"]), json.loads(raw["config"])
    except json.JSONDecodeError:
        raise ValueError("render JSON input is invalid") from None
    validate_exact_schedule(private, public, selection_proof=proof,
        selection_proof_sha256=PROOF_SHA256, config=config,
        config_sha256=CONFIG_SHA256,
        presentation_salt_hex=raw["salt"][:-1].decode("ascii"))
    if render_media_sha256 != config["selection"]["source_sha256"]:
        raise ValueError("render media does not match the proof-selected source")
    width, height = config["render"]["panel_width"], config["render"]["panel_height"]
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent))
    try:
        (stage / "public-reviewer-index.json").write_bytes(raw["public"])
        rendered = 0
        for entry, packet in zip(private["entries"], public["packets"]):
            if entry["packet_id"] != packet["packet_id"]:
                raise ValueError("private/public packet order changed")
            for private_row, public_row in zip(entry["rows"], packet["rows"]):
                destination = stage / PurePosixPath(public_row["media_ref"])
                destination.parent.mkdir(parents=True, exist_ok=True)
                command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                    "-ss", _terminating_decimal(private_row["absolute_source_time"]),
                    "-i", str(render_media_path), "-frames:v", "1", "-filter_complex",
                    _filter(private_row["views"], width, height), "-map", "[out]",
                    "-an", "-c:v", "png", str(destination)]
                try:
                    subprocess.run(command, check=True, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE)
                except (OSError, subprocess.CalledProcessError):
                    raise ValueError("structural review media renderer failed") from None
                sanitize_png(destination, expected_width=width * 2,
                             expected_height=height * 2)
                rendered += 1
        tree_sha = canonical_bundle_tree_sha256(stage, public)
        os.rename(stage, output_directory)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return {"packet_count": 8, "row_count": rendered,
            "bundle_tree_sha256": tree_sha}
