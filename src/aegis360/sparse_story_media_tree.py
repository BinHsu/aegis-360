"""Closed synthetic PNG tree publication for sparse-story adapter inputs."""

from __future__ import annotations

import binascii
import ctypes
import hashlib
import json
import os
import stat
import struct
import sys
import tempfile
import zlib
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from .sparse_story_projection import canonical_index_bytes, validate_adapter_index


PNG = b"\x89PNG\r\n\x1a\n"
CONTRACT = "sparse-story-png-rgb-rgba-960x540-v1"
RESULT_SCHEMA = "aegis360.sparse-story-sanitized-media-result.v1"
SHA = __import__("re").compile(r"^[0-9a-f]{64}$")
PRIVACY = {"contains_source_path": False, "contains_pixels": False,
    "contains_audio": False, "contains_identity": False,
    "contains_source_time": False, "contains_free_text": False}
AUTHORITY = {"sanitized_transient_media_input": True,
    "semantic_observation": False, "exact_boundary": False,
    "chapter_map": False, "camera": False, "reorder": False,
    "render": False, "model_invocation": False}


def _chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xffffffff)


def sanitize_png_bytes(data: bytes) -> bytes:
    if not isinstance(data, bytes) or not data.startswith(PNG):
        raise ValueError("payload is not PNG bytes")
    offset = 8; ihdr = None; idats = []; seen_idat = False; ended_idat = False; iend = False
    while offset < len(data):
        if offset + 12 > len(data): raise ValueError("PNG chunk is truncated")
        size = struct.unpack(">I", data[offset:offset + 4])[0]
        end = offset + 12 + size
        if end > len(data): raise ValueError("PNG payload is truncated")
        kind = data[offset + 4:offset + 8]; payload = data[offset + 8:offset + 8 + size]
        if len(kind) != 4 or not all(65 <= c <= 90 or 97 <= c <= 122 for c in kind) or not 65 <= kind[2] <= 90:
            raise ValueError("PNG chunk type is invalid")
        crc = struct.unpack(">I", data[offset + 8 + size:end])[0]
        if binascii.crc32(kind + payload) & 0xffffffff != crc: raise ValueError("PNG CRC mismatch")
        critical = not kind[0] & 32
        if kind == b"IHDR":
            if ihdr is not None or offset != 8 or len(payload) != 13: raise ValueError("PNG IHDR is invalid")
            width, height, depth, color, comp, filt, interlace = struct.unpack(">IIBBBBB", payload)
            if (width, height, depth, color, comp, filt, interlace) not in {(960, 540, 8, 2, 0, 0, 0), (960, 540, 8, 6, 0, 0, 0)}: raise ValueError("PNG image contract is invalid")
            ihdr = payload
        elif kind == b"IDAT":
            if ihdr is None or ended_idat or iend: raise ValueError("PNG IDAT order is invalid")
            seen_idat = True; idats.append(payload)
        elif kind == b"IEND":
            if ihdr is None or not seen_idat or iend or payload or end != len(data): raise ValueError("PNG IEND is invalid")
            iend = True
        elif ihdr is None:
            raise ValueError("PNG IHDR must be first")
        elif critical:
            raise ValueError("unknown critical PNG chunk is forbidden")
        elif seen_idat:
            ended_idat = True
        offset = end
    if not iend or ihdr is None: raise ValueError("PNG is incomplete")
    compressed = b"".join(idats); decoder = zlib.decompressobj()
    expected_size = 540 * (1 + 960 * (3 if ihdr[9] == 2 else 4))
    try: raw = decoder.decompress(compressed, expected_size + 1) + decoder.flush()
    except zlib.error as error: raise ValueError("PNG zlib stream is invalid") from error
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("PNG must contain exactly one complete zlib stream")
    bpp = 3 if ihdr[9] == 2 else 4; stride = 1 + 960 * bpp
    if len(raw) != 540 * stride or any(raw[row * stride] > 4 for row in range(540)):
        raise ValueError("PNG scanlines are invalid")
    return PNG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b"")


def _refs(index: Mapping[str, object]) -> list[str]:
    try: refs = [row["media_ref"] for item in index["packets"] for row in item["projection"]["rows"]]
    except (KeyError, TypeError): raise ValueError("adapter index refs are invalid") from None
    if not refs or len(refs) != len(set(refs)): raise ValueError("adapter index refs are missing or duplicated")
    for ref in refs:
        if not isinstance(ref, str): raise ValueError("adapter media ref is unsafe")
        path = PurePosixPath(ref)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != ref or len(path.parts) != 3 or path.parts[0] != "media":
            raise ValueError("adapter media ref is unsafe")
    return refs


def _expected(index): return {"adapter-index.json", *_refs(index)}


class _TreeSnapshot:
    def __init__(self, root_fd: int, root_identity: tuple[int, int], directories, leaves):
        self.root_fd = root_fd; self.root_identity = root_identity
        self.directories = directories; self.leaves = leaves

    def leaf_hashes(self) -> dict[str, str]:
        leaf_hashes = {}
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        root = os.fstat(self.root_fd)
        if ((root.st_dev, root.st_ino) != self.root_identity
                or stat.S_IMODE(root.st_mode) != 0o555):
            raise ValueError("bundle root identity or mode changed")
        for _, fd, frozen in self.directories:
            current = os.fstat(fd)
            if ((current.st_dev, current.st_ino) != frozen
                    or not stat.S_ISDIR(current.st_mode)
                    or stat.S_IMODE(current.st_mode) != 0o555):
                raise ValueError("bundle directory identity or mode changed")
        for relative, fd, frozen in self.leaves:
            before = os.fstat(fd)
            if identity(before) != frozen or stat.S_IMODE(before.st_mode) != 0o444:
                raise ValueError("bundle leaf identity or mode changed")
            os.lseek(fd, 0, os.SEEK_SET); digest = hashlib.sha256()
            while chunk := os.read(fd, 1024 * 1024): digest.update(chunk)
            if identity(os.fstat(fd)) != frozen: raise ValueError("bundle leaf changed while hashing")
            leaf_hashes[relative] = digest.hexdigest()
        return leaf_hashes

    def digest(self) -> str:
        leaf_hashes = self.leaf_hashes()
        lines = [f"{leaf_hashes[relative]}  {relative}\n"
                 for relative in sorted(leaf_hashes, key=lambda x: x.encode("utf-8"))]
        return hashlib.sha256("".join(lines).encode()).hexdigest()

    def close(self):
        for _, fd, _ in self.leaves: os.close(fd)
        for _, fd, _ in reversed(self.directories): os.close(fd)
        os.close(self.root_fd)


def _tree_digest(leaf_hashes: Mapping[str, str]) -> str:
    lines = [f"{leaf_hashes[relative]}  {relative}\n"
             for relative in sorted(leaf_hashes, key=lambda x: x.encode("utf-8"))]
    return hashlib.sha256("".join(lines).encode()).hexdigest()

def _open_tree_snapshot(root: Path, index: Mapping[str, object]) -> _TreeSnapshot:
    expected_files = _expected(index)
    expected_dirs = {"", "media"} | {str(PurePosixPath(ref).parent) for ref in _refs(index)}
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    leaves = []; directories = []; actual_files = set(); actual_dirs = {""}
    try:
        root_stat = os.fstat(root_fd)
        if not stat.S_ISDIR(root_stat.st_mode) or stat.S_IMODE(root_stat.st_mode) != 0o555:
            raise ValueError("bundle root type or mode is invalid")
        def visit(directory_fd: int, prefix: str):
            for name in os.listdir(directory_fd):
                if not isinstance(name, str) or not name or "/" in name: raise ValueError("bundle name is invalid")
                relative = f"{prefix}/{name}" if prefix else name
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    actual_dirs.add(relative)
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
                    opened = os.fstat(child)
                    if ((opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
                            or not stat.S_ISDIR(opened.st_mode)
                            or stat.S_IMODE(opened.st_mode) != 0o555):
                        os.close(child); raise ValueError("bundle directory identity or mode is invalid")
                    directories.append((relative, child, (opened.st_dev, opened.st_ino)))
                    visit(child, relative)
                elif stat.S_ISREG(info.st_mode):
                    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
                    opened = os.fstat(fd)
                    if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                        os.close(fd); raise ValueError("bundle leaf is not singly-linked regular file")
                    actual_files.add(relative)
                    leaves.append((relative, fd, (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)))
                else: raise ValueError("bundle node type is forbidden")
        visit(root_fd, "")
        if actual_files != expected_files or actual_dirs != expected_dirs: raise ValueError("bundle tree scope is not exact")
        return _TreeSnapshot(root_fd, (root_stat.st_dev, root_stat.st_ino), directories, leaves)
    except BaseException:
        for _, fd, _ in leaves: os.close(fd)
        for _, fd, _ in reversed(directories): os.close(fd)
        os.close(root_fd)
        raise


def validate_closed_tree(root: Path, index: Mapping[str, object]) -> tuple[str, tuple[int, int]]:
    snapshot = _open_tree_snapshot(root, index)
    try:
        return snapshot.digest(), snapshot.root_identity
    finally:
        snapshot.close()


def _rename_exclusive(source: Path, destination: Path) -> None:
    if sys.platform != "darwin": raise ValueError("exclusive rename is unsupported")
    library = ctypes.CDLL(None, use_errno=True)
    rename = getattr(library, "renamex_np", None)
    if rename is None: raise ValueError("exclusive rename is unsupported")
    rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint); rename.restype = ctypes.c_int
    if rename(os.fsencode(source), os.fsencode(destination), 4) != 0:
        errno = ctypes.get_errno()
        if errno == __import__("errno").EEXIST: raise ValueError("refusing to overwrite destination")
        raise OSError(errno, "exclusive rename failed")


def _remove_owned_tree(path: Path, identity: tuple[int, int]) -> None:
    """Remove only a root whose no-follow identity is still ours."""
    try:
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        root_fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                          dir_fd=parent_fd)
    except (FileNotFoundError, NotADirectoryError, OSError):
        try: os.close(parent_fd)
        except (NameError, OSError): pass
        return
    try:
        current = os.fstat(root_fd)
        if (current.st_dev, current.st_ino) != identity: return

        def empty(directory_fd: int):
            os.fchmod(directory_fd, 0o700)
            for name in os.listdir(directory_fd):
                info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                    dir_fd=directory_fd)
                    try:
                        opened = os.fstat(child)
                        if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                            raise ValueError("owned cleanup directory changed")
                        empty(child)
                        current_name = os.stat(name, dir_fd=directory_fd,
                                               follow_symlinks=False)
                        if ((current_name.st_dev, current_name.st_ino)
                                != (opened.st_dev, opened.st_ino)
                                or not stat.S_ISDIR(current_name.st_mode)):
                            raise ValueError("owned cleanup directory was replaced")
                        os.rmdir(name, dir_fd=directory_fd)
                    finally: os.close(child)
                else:
                    os.unlink(name, dir_fd=directory_fd)
        empty(root_fd)
        current_name = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if ((current_name.st_dev, current_name.st_ino) == identity
                and stat.S_ISDIR(current_name.st_mode)):
            os.rmdir(path.name, dir_fd=parent_fd)
    finally:
        os.close(root_fd); os.close(parent_fd)


def build_result(*, adapter_index_sha256: str,
                 input_payloads: Sequence[tuple[str, str]],
                 bundle_tree_sha256: str):
    if (not isinstance(adapter_index_sha256, str) or SHA.fullmatch(adapter_index_sha256) is None
            or not isinstance(bundle_tree_sha256, str) or SHA.fullmatch(bundle_tree_sha256) is None
            or not isinstance(input_payloads, Sequence)):
        raise ValueError("sanitized media result inputs are invalid")
    inputs = list(input_payloads)
    if (inputs != sorted(inputs, key=lambda x: x[0].encode())
            or len(inputs) != len({ref for ref, _ in inputs})
            or any(not isinstance(ref, str) or not isinstance(digest, str)
                   or SHA.fullmatch(digest) is None for ref, digest in inputs)):
        raise ValueError("sanitized media input payload proof is invalid")
    rows = [{"media_ref": ref, "sha256": digest} for ref, digest in inputs]
    return {"schema_version": RESULT_SCHEMA,
        "inputs": {"adapter_index_sha256": adapter_index_sha256, "sanitizer_contract_id": CONTRACT, "input_payloads": rows},
        "outputs": {"media_file_count": len(rows), "total_file_count": len(rows) + 1, "bundle_tree_sha256": bundle_tree_sha256},
        "privacy": dict(PRIVACY), "authority": dict(AUTHORITY)}


def canonical_result_bytes(result): return json.dumps(result, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def validate_result(result: Mapping[str, object], **inputs) -> None:
    if result != build_result(**inputs): raise ValueError("sanitized media result must exactly rebuild")


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0: raise OSError("short file write")
        offset += written


def _write_leaf(directory_fd: int, name: str, data: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory_fd)
    try:
        _write_all(fd, data); os.fsync(fd); os.fchmod(fd, 0o444); os.fsync(fd)
    finally: os.close(fd)


def _publish_sanitized_bundle(*, index: Mapping[str, object],
        private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], salt_hex: str,
        payloads: Sequence[tuple[str, bytes]], destination: Path):
    validate_adapter_index(index, private_packets=private_packets,
        ordered_private_packet_sha256s=ordered_private_packet_sha256s, salt_hex=salt_hex)
    index_bytes = canonical_index_bytes(index)
    index_sha256 = hashlib.sha256(index_bytes).hexdigest()
    refs = _refs(index)
    if not isinstance(payloads, Sequence) or isinstance(payloads, (str, bytes)): raise ValueError("payload set is invalid")
    supplied = {}; ordered_inputs = []
    for ref, data in payloads:
        if not isinstance(ref, str) or not isinstance(data, bytes) or ref in supplied: raise ValueError("payload set is invalid")
        supplied[ref] = data; ordered_inputs.append((ref, hashlib.sha256(data).hexdigest()))
    if set(supplied) != set(refs): raise ValueError("payload refs do not exactly match index")
    frozen = sorted(ordered_inputs, key=lambda x: x[0].encode())
    destination.parent.mkdir(parents=True, exist_ok=True)
    old_umask = os.umask(0o077)
    try: stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)); stage.chmod(0o700)
    finally: os.umask(old_umask)
    stage_stat = os.stat(stage, follow_symlinks=False)
    stage_identity = (stage_stat.st_dev, stage_stat.st_ino)
    published = False; owned_identity = None; snapshot = None; handed_off = False
    try:
        leaves = {"adapter-index.json": index_bytes, **{ref: sanitize_png_bytes(supplied[ref]) for ref in refs}}
        root_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _write_leaf(root_fd, "adapter-index.json", leaves["adapter-index.json"])
            os.mkdir("media", 0o700, dir_fd=root_fd)
            media_fd = os.open("media", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
            try:
                by_packet = {}
                for ref in refs:
                    _, packet, filename = PurePosixPath(ref).parts
                    by_packet.setdefault(packet, []).append((filename, leaves[ref]))
                for packet, rows in by_packet.items():
                    os.mkdir(packet, 0o700, dir_fd=media_fd)
                    packet_fd = os.open(packet, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=media_fd)
                    try:
                        for filename, data in rows: _write_leaf(packet_fd, filename, data)
                        os.fchmod(packet_fd, 0o555); os.fsync(packet_fd)
                    finally: os.close(packet_fd)
                os.fchmod(media_fd, 0o555); os.fsync(media_fd)
            finally: os.close(media_fd)
            os.fchmod(root_fd, 0o555); os.fsync(root_fd)
        finally: os.close(root_fd)
        snapshot = _open_tree_snapshot(stage, index)
        leaf_hashes = snapshot.leaf_hashes(); tree_sha = _tree_digest(leaf_hashes)
        owned_identity = snapshot.root_identity
        if sorted((ref, hashlib.sha256(data).hexdigest()) for ref, data in payloads) != frozen: raise ValueError("caller payload bytes changed")
        parent_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd); _rename_exclusive(stage, destination)
            published = True; os.fsync(parent_fd)
        finally: os.close(parent_fd)
        retained_sha = snapshot.digest()
        post_sha, post_identity = validate_closed_tree(destination, index)
        if retained_sha != tree_sha or post_sha != tree_sha or post_identity != owned_identity:
            raise ValueError("published bundle identity or hash mismatch")
        result = canonical_result_bytes(build_result(adapter_index_sha256=index_sha256,
            input_payloads=frozen, bundle_tree_sha256=tree_sha))
        handed_off = True
        return result, snapshot, tree_sha, leaf_hashes
    except BaseException:
        if published and owned_identity is not None:
            _remove_owned_tree(destination, owned_identity)
        elif not published: _remove_owned_tree(stage, stage_identity)
        raise
    finally:
        if snapshot is not None and not handed_off: snapshot.close()


def publish_sanitized_bundle(**inputs) -> bytes:
    result, snapshot, _, _ = _publish_sanitized_bundle(**inputs)
    try: return result
    finally: snapshot.close()


def _remove_owned_file(path: Path, identity: tuple[int, int]) -> None:
    try:
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        current = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        if ((current.st_dev, current.st_ino) == identity
                and stat.S_ISREG(current.st_mode)):
            os.unlink(path.name, dir_fd=parent_fd)
    except (FileNotFoundError, NotADirectoryError, OSError): pass
    finally:
        try: os.close(parent_fd)
        except (NameError, OSError): pass


def _write_result_exclusive(path: Path, result_bytes: bytes) -> tuple[str, tuple[int, int]]:
    if not isinstance(result_bytes, bytes): raise ValueError("result must be canonical bytes")
    parsed = json.loads(result_bytes)
    if canonical_result_bytes(parsed) != result_bytes: raise ValueError("result bytes are not canonical")
    path.parent.mkdir(parents=True, exist_ok=True); fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary); published = False; owned_identity = None
    try:
        _write_all(fd, result_bytes); os.fsync(fd); os.fchmod(fd, 0o444); os.fsync(fd)
        frozen = os.fstat(fd); owned_identity = (frozen.st_dev, frozen.st_ino)
        _rename_exclusive(temporary_path, path)
        published = True
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY); os.fsync(parent_fd); os.close(parent_fd)
        os.lseek(fd, 0, os.SEEK_SET); retained = b""
        while chunk := os.read(fd, 1024 * 1024): retained += chunk
        current = os.stat(path, follow_symlinks=False)
        if (retained != result_bytes or (current.st_dev, current.st_ino) != owned_identity
                or not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
                or stat.S_IMODE(current.st_mode) != 0o444):
            raise ValueError("persisted result bytes or identity changed")
        return hashlib.sha256(result_bytes).hexdigest(), owned_identity
    except BaseException:
        if published:
            _remove_owned_file(path, owned_identity)
        raise
    finally:
        if fd >= 0: os.close(fd)
        temporary_path.unlink(missing_ok=True)


def _derive_gate_result(*, index: Mapping[str, object],
        private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], salt_hex: str,
        payloads: Sequence[tuple[str, bytes]], bundle: Path):
    validate_adapter_index(index, private_packets=private_packets,
        ordered_private_packet_sha256s=ordered_private_packet_sha256s,
        salt_hex=salt_hex)
    refs = _refs(index); supplied = {}
    if not isinstance(payloads, Sequence) or isinstance(payloads, (str, bytes)):
        raise ValueError("payload set is invalid")
    for item in payloads:
        if (not isinstance(item, tuple) or len(item) != 2
                or not isinstance(item[0], str) or not isinstance(item[1], bytes)
                or item[0] in supplied):
            raise ValueError("payload set is invalid")
        supplied[item[0]] = item[1]
    if set(supplied) != set(refs): raise ValueError("payload refs do not exactly match index")
    input_hashes = sorted(((ref, hashlib.sha256(data).hexdigest())
                           for ref, data in supplied.items()), key=lambda row: row[0].encode())
    index_bytes = canonical_index_bytes(index)
    expected_leaf_hashes = {"adapter-index.json": hashlib.sha256(index_bytes).hexdigest()}
    expected_leaf_hashes.update({ref: hashlib.sha256(sanitize_png_bytes(supplied[ref])).hexdigest()
                                 for ref in refs})
    expected_tree_sha = _tree_digest(expected_leaf_hashes)
    snapshot = _open_tree_snapshot(bundle, index)
    try:
        if snapshot.leaf_hashes() != expected_leaf_hashes:
            raise ValueError("bundle leaves do not derive from canonical index and original payloads")
        tree_sha = snapshot.digest()
        if tree_sha != expected_tree_sha: raise ValueError("bundle tree digest does not derive")
        expected = canonical_result_bytes(build_result(
            adapter_index_sha256=hashlib.sha256(index_bytes).hexdigest(),
            input_payloads=input_hashes, bundle_tree_sha256=tree_sha))
        return expected, snapshot, tree_sha, expected_leaf_hashes
    except BaseException:
        snapshot.close(); raise


def validate_sanitized_media_gate(*, result_bytes: bytes, index: Mapping[str, object],
        private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], salt_hex: str,
        payloads: Sequence[tuple[str, bytes]], bundle: Path) -> None:
    expected, snapshot, _, _ = _derive_gate_result(index=index, private_packets=private_packets,
        ordered_private_packet_sha256s=ordered_private_packet_sha256s,
        salt_hex=salt_hex, payloads=payloads, bundle=bundle)
    try:
        if result_bytes != expected: raise ValueError("sanitized media gate result does not exactly derive")
    finally: snapshot.close()


def publish_sanitized_media_gate(*, index: Mapping[str, object],
        private_packets: Sequence[Mapping[str, object]],
        ordered_private_packet_sha256s: Sequence[str], salt_hex: str,
        payloads: Sequence[tuple[str, bytes]], bundle_destination: Path,
        result_destination: Path) -> str:
    result_bytes, publisher_snapshot, published_tree_sha, published_leaf_hashes = _publish_sanitized_bundle(index=index,
        private_packets=private_packets,
        ordered_private_packet_sha256s=ordered_private_packet_sha256s,
        salt_hex=salt_hex, payloads=payloads, destination=bundle_destination)
    owned_identity = publisher_snapshot.root_identity
    gate_snapshot = None; result_identity = None
    try:
        # The publisher's original descriptors remain open across every later check.
        if (publisher_snapshot.leaf_hashes() != published_leaf_hashes
                or publisher_snapshot.digest() != published_tree_sha):
            raise ValueError("publisher snapshot changed before result derivation")
        expected, gate_snapshot, tree_sha, expected_leaf_hashes = _derive_gate_result(index=index,
            private_packets=private_packets,
            ordered_private_packet_sha256s=ordered_private_packet_sha256s,
            salt_hex=salt_hex, payloads=payloads, bundle=bundle_destination)
        if gate_snapshot.root_identity != owned_identity or expected != result_bytes:
            raise ValueError("published bundle result or identity mismatch")
        if published_leaf_hashes != expected_leaf_hashes or published_tree_sha != tree_sha:
            raise ValueError("publisher output does not derive from original inputs")
        result_sha, result_identity = _write_result_exclusive(result_destination, result_bytes)
        if (publisher_snapshot.leaf_hashes() != expected_leaf_hashes
                or publisher_snapshot.digest() != tree_sha
                or gate_snapshot.leaf_hashes() != expected_leaf_hashes
                or gate_snapshot.digest() != tree_sha):
            raise ValueError("bundle changed across result publication")
        post_sha, post_identity = validate_closed_tree(bundle_destination, index)
        if post_sha != tree_sha or post_identity != owned_identity:
            raise ValueError("bundle changed after result publication")
        validate_sanitized_media_gate(result_bytes=result_bytes, index=index,
            private_packets=private_packets,
            ordered_private_packet_sha256s=ordered_private_packet_sha256s,
            salt_hex=salt_hex, payloads=payloads, bundle=bundle_destination)
        return result_sha
    except BaseException:
        if result_identity is not None: _remove_owned_file(result_destination, result_identity)
        _remove_owned_tree(bundle_destination, owned_identity)
        raise
    finally:
        if gate_snapshot is not None: gate_snapshot.close()
        publisher_snapshot.close()
