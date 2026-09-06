import copy
import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_media_tree import (  # noqa: E402
    PNG, canonical_result_bytes, publish_sanitized_bundle, sanitize_png_bytes,
    validate_closed_tree, validate_result, validate_sanitized_media_gate,
    publish_sanitized_media_gate, _rename_exclusive, _remove_owned_tree,
    _publish_sanitized_bundle, _write_result_exclusive,
)
from tests import test_sparse_story_projection as projection_helpers


def chunk(kind, payload):
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)


def image(filter_byte=0, width=960, height=540, extra=True):
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(bytes([filter_byte]) + b"\x10\x20\x30" * width for _ in range(height))
    middle = chunk(b"tEXt", b"secret") if extra else b""
    return PNG + chunk(b"IHDR", ihdr) + middle + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def local_rename(source, destination):
    if Path(destination).exists(): raise ValueError("refusing to overwrite destination")
    os.rename(source, destination)


class SparseStoryMediaTreeTests(unittest.TestCase):
    def fixture(self):
        helper = projection_helpers.SparseStoryProjectionTests(); packets, hashes, index = helper.build(1)
        return packets, hashes, index

    def publish_args(self, packets, hashes, index):
        return dict(index=index, private_packets=packets,
            ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)

    def payloads(self, index):
        return [(row["media_ref"], image()) for item in index["packets"] for row in item["projection"]["rows"]]

    def test_png_deterministic_sanitize_and_failures(self):
        source = image(); first = sanitize_png_bytes(source); second = sanitize_png_bytes(source)
        self.assertEqual(first, second); self.assertNotIn(b"tEXt", first)
        bad = []
        changed = bytearray(source); changed[-1] ^= 1; bad.append(bytes(changed))
        bad.extend((source[:-1], image(width=959), image(filter_byte=5)))
        ihdr = struct.pack(">IIBBBBB", 960, 540, 8, 2, 0, 0, 0)
        raw = b"".join(b"\0" + b"\0" * 2880 for _ in range(540))
        bad.append(PNG + chunk(b"IHDR", ihdr) + chunk(b"PLTE", b"") + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
        bad.append(PNG + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw) + zlib.compress(b"x")) + chunk(b"IEND", b""))
        for value in bad:
            with self.assertRaises(ValueError): sanitize_png_bytes(value)

    def test_atomic_publish_exact_tree_modes_result_and_immutability(self):
        packets, hashes, index = self.fixture(); index_bytes = json.dumps(index, allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
        payloads = self.payloads(index); frozen = list(payloads)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); destination = root / "bundle"
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename):
                result_bytes = publish_sanitized_bundle(**self.publish_args(packets, hashes, index), payloads=payloads,
                    destination=destination)
            result = json.loads(result_bytes); self.assertEqual(canonical_result_bytes(result), result_bytes)
            tree_sha, _ = validate_closed_tree(destination, index)
            self.assertEqual(result["outputs"]["bundle_tree_sha256"], tree_sha)
            input_proof = [(item["media_ref"], item["sha256"])
                           for item in result["inputs"]["input_payloads"]]
            validate_result(result,
                adapter_index_sha256=hashlib.sha256(index_bytes).hexdigest(),
                input_payloads=input_proof, bundle_tree_sha256=tree_sha)
            changed = copy.deepcopy(result); changed["authority"]["render"] = True
            with self.assertRaises(ValueError): validate_result(changed,
                adapter_index_sha256=hashlib.sha256(index_bytes).hexdigest(),
                input_payloads=input_proof, bundle_tree_sha256=tree_sha)
            self.assertEqual(payloads, frozen)
            self.assertEqual(stat_mode(destination), 0o555)
            self.assertTrue(all(stat_mode(path) == 0o444 for path in destination.rglob("*") if path.is_file()))
            result_path = root / "result.json"
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename):
                result_sha, _ = _write_result_exclusive(result_path, result_bytes)
            self.assertEqual(result_sha, hashlib.sha256(result_bytes).hexdigest())
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename):
                with self.assertRaises(ValueError): _write_result_exclusive(result_path, result_bytes)
            replacement_path = root / "replacement-result.json"
            def replace_after_rename(source, target):
                os.rename(source, target); Path(target).unlink(); Path(target).write_bytes(b"replacement")
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=replace_after_rename):
                with self.assertRaisesRegex(ValueError, "identity"):
                    _write_result_exclusive(replacement_path, result_bytes)
            self.assertEqual(replacement_path.read_bytes(), b"replacement")
            validate_sanitized_media_gate(result_bytes=result_bytes,
                **self.publish_args(packets, hashes, index), payloads=payloads,
                bundle=destination)

    def test_scope_payload_and_publish_race_cleanup(self):
        packets, hashes, index = self.fixture(); payloads = self.payloads(index)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for changed in (payloads[:-1], payloads + [("media/extra/x.png", image())], payloads + [payloads[0]]):
                with self.assertRaises(ValueError): publish_sanitized_bundle(**self.publish_args(packets, hashes, index), payloads=changed, destination=root / "bad")
            destination = root / "race"
            def race(source, target):
                Path(target).mkdir(); raise ValueError("refusing to overwrite destination")
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=race):
                with self.assertRaises(ValueError): publish_sanitized_bundle(**self.publish_args(packets, hashes, index), payloads=payloads, destination=destination)
            self.assertTrue(destination.exists())
            self.assertEqual(list(root.glob(".race.*")), [])
            # Existing replacement is not owned and must survive.
            (destination / "owner").write_text("keep")
            self.assertEqual((destination / "owner").read_text(), "keep")
            fsync_destination = root / "fsync-fail"
            with mock.patch("aegis360.sparse_story_media_tree.os.fsync", side_effect=OSError("synthetic")):
                with self.assertRaises(OSError): publish_sanitized_bundle(**self.publish_args(packets, hashes, index), payloads=payloads,
                    destination=fsync_destination)
            self.assertFalse(fsync_destination.exists())
            self.assertEqual(list(root.glob(".fsync-fail.*")), [])

    def test_high_level_validation_modes_and_result_failure_cleanup(self):
        packets, hashes, index = self.fixture(); payloads = self.payloads(index)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); bundle = root / "bundle"; result_path = root / "result.json"
            changed = copy.deepcopy(index); changed["packet_count"] = 6
            with self.assertRaises(ValueError):
                publish_sanitized_bundle(**self.publish_args(packets, hashes, changed),
                    payloads=payloads, destination=bundle)
            rename_calls = 0
            def fail_result_publish(source, target):
                nonlocal rename_calls
                rename_calls += 1
                if rename_calls == 1: local_rename(source, target)
                else: raise OSError("result publication failure")
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=fail_result_publish):
                with self.assertRaises(OSError):
                    publish_sanitized_media_gate(**self.publish_args(packets, hashes, index),
                        payloads=payloads, bundle_destination=bundle,
                        result_destination=result_path)
            self.assertFalse(bundle.exists()); self.assertFalse(result_path.exists())
            self.assertEqual(list(root.glob(".result.json.*")), [])

            def replace_leaf_after_publisher(**kwargs):
                outcome = _publish_sanitized_bundle(**kwargs)
                leaf = next((bundle / "media").glob("*/*.png")); parent = leaf.parent
                parent.chmod(0o755); leaf.unlink(); leaf.write_bytes(image(filter_byte=1, extra=False))
                leaf.chmod(0o444); parent.chmod(0o555)
                return outcome
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename), \
                    mock.patch("aegis360.sparse_story_media_tree._publish_sanitized_bundle", side_effect=replace_leaf_after_publisher):
                with self.assertRaises(ValueError):
                    publish_sanitized_media_gate(**self.publish_args(packets, hashes, index),
                        payloads=payloads, bundle_destination=bundle,
                        result_destination=result_path)
            self.assertFalse(bundle.exists()); self.assertFalse(result_path.exists())

            def mutate_bundle_after_result(path, data):
                outcome = _write_result_exclusive(path, data)
                leaf = next((bundle / "media").glob("*/*.png"))
                leaf.chmod(0o644); leaf.write_bytes(b"changed")
                return outcome
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename), \
                    mock.patch("aegis360.sparse_story_media_tree._write_result_exclusive", side_effect=mutate_bundle_after_result):
                with self.assertRaises(ValueError):
                    publish_sanitized_media_gate(**self.publish_args(packets, hashes, index),
                        payloads=payloads, bundle_destination=bundle,
                        result_destination=result_path)
            self.assertFalse(bundle.exists()); self.assertFalse(result_path.exists())

            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename):
                publish_sanitized_bundle(**self.publish_args(packets, hashes, index),
                    payloads=payloads, destination=bundle)
            bundle.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "mode"):
                validate_closed_tree(bundle, index)

    def test_owned_cleanup_stops_on_child_name_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "owned"; root.mkdir(); child = root / "child"
            child.mkdir(); (child / "leaf").write_bytes(b"owned")
            identity_stat = root.stat(); identity = (identity_stat.st_dev, identity_stat.st_ino)
            real_stat = os.stat; child_stats = 0
            def swap_on_recheck(path, *args, **kwargs):
                nonlocal child_stats
                if path == "child" and kwargs.get("dir_fd") is not None:
                    child_stats += 1
                    if child_stats == 2:
                        child.rename(root / "moved-owned-child")
                        child.mkdir(); (child / "replacement").write_bytes(b"keep")
                return real_stat(path, *args, **kwargs)
            with mock.patch("aegis360.sparse_story_media_tree.os.stat", side_effect=swap_on_recheck):
                with self.assertRaisesRegex(ValueError, "replaced"):
                    _remove_owned_tree(root, identity)
            self.assertEqual((child / "replacement").read_bytes(), b"keep")

    @unittest.skipUnless(sys.platform == "darwin", "Darwin renamex_np integration")
    def test_real_darwin_exclusive_rename_success_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"; source.write_bytes(b"new")
            target = root / "target"
            _rename_exclusive(source, target)
            self.assertEqual(target.read_bytes(), b"new"); self.assertFalse(source.exists())
            source_dir = root / "source-directory"; source_dir.mkdir()
            (source_dir / "payload").write_bytes(b"directory")
            target_dir = root / "target-directory"
            _rename_exclusive(source_dir, target_dir)
            self.assertEqual((target_dir / "payload").read_bytes(), b"directory")
            self.assertFalse(source_dir.exists())
            for target_kind in ("file", "empty-dir", "nonempty-dir"):
                source = root / f"source-for-{target_kind}"; source.mkdir()
                (source / "payload").write_bytes(b"replacement")
                destination = root / f"existing-{target_kind}"
                if target_kind == "file": destination.write_bytes(b"keep")
                else:
                    destination.mkdir()
                    if target_kind == "nonempty-dir": (destination / "keep").write_bytes(b"keep")
                with self.assertRaises(ValueError): _rename_exclusive(source, destination)
                self.assertEqual((source / "payload").read_bytes(), b"replacement")
                if target_kind == "file": self.assertEqual(destination.read_bytes(), b"keep")
                elif target_kind == "nonempty-dir": self.assertEqual((destination / "keep").read_bytes(), b"keep")
                else: self.assertEqual(list(destination.iterdir()), [])
            packets, hashes, index = self.fixture(); payloads = self.payloads(index)
            bundle = root / "real-gate-bundle"; result = root / "real-gate-result.json"
            result_sha = publish_sanitized_media_gate(
                **self.publish_args(packets, hashes, index), payloads=payloads,
                bundle_destination=bundle, result_destination=result)
            self.assertEqual(result_sha, hashlib.sha256(result.read_bytes()).hexdigest())
            validate_sanitized_media_gate(result_bytes=result.read_bytes(),
                **self.publish_args(packets, hashes, index), payloads=payloads,
                bundle=bundle)


def stat_mode(path): return __import__("stat").S_IMODE(path.stat().st_mode)


if __name__ == "__main__": unittest.main()
