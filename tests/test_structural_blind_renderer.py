import hashlib
import json
import os
import struct
import sys
import tempfile
import unittest
import zlib
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.blind_chapter_review_renderer import PNG_SIGNATURE  # noqa: E402
from aegis360.structural_blind_renderer import (  # noqa: E402
    _terminating_decimal, canonical_bundle_tree_sha256,
    render_structural_blind_bundle, validate_canonical_bundle_tree,
)
from tests import test_structural_blind_schedule as schedule_helpers  # noqa: E402
from aegis360.structural_blind_schedule import build_structural_blind_schedule  # noqa: E402


def digest(data): return hashlib.sha256(data).hexdigest()


def chunk(kind, payload):
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)


def png(width=960, height=540):
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = b"".join(b"\0" + b"\x10\x20\x30" * width for _ in range(height))
    return PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"tEXt", b"secret") + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")


class StructuralBlindRendererTests(unittest.TestCase):
    def schedule(self):
        helper = schedule_helpers.StructuralBlindScheduleTests()
        helper.config = json.loads((ROOT / "config/structural-chapter-blind-schedule-v1.json").read_bytes())
        helper.salt = "4" * 64
        proof = helper.proof()
        centers = {}
        for rank, selected in enumerate(proof["selected"], start=1):
            center = Fraction(400 + rank * 40, 4)
            value = {"numerator": center.numerator,
                     "denominator": center.denominator}
            selected["source_time"] = value
            centers[(selected["event_id"], selected["signal_id"])] = value
        for row in proof["universe"]:
            key = (row["event_id"], row["signal_id"])
            if key in centers:
                row["source_time"] = centers[key]
        private, public = build_structural_blind_schedule(
            selection_proof=proof,
            selection_proof_sha256="ad6f29b1cf34374ad3130afa3bd2535ac81676fdb4300a2891fb5c6c8712a567",
            config=helper.config,
            config_sha256="3964162f0cb99bf9959cee1b19bef9fd041a04a76dfae9085052c9babb30d8ba",
            presentation_salt_hex=helper.salt)
        return proof, helper.config, private, public

    def test_terminating_decimal_and_nonterminating_failure(self):
        self.assertEqual(_terminating_decimal({"numerator": 423, "denominator": 5}), "84.6")
        self.assertEqual(_terminating_decimal({"numerator": 337, "denominator": 4}), "84.25")
        with self.assertRaisesRegex(ValueError, "terminating"):
            _terminating_decimal({"numerator": 1, "denominator": 3})

    def test_canonical_tree_exact_scope_extra_and_symlink_rejected(self):
        _, _, _, public = self.schedule()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "public-reviewer-index.json").write_text(json.dumps(public))
            for packet in public["packets"]:
                for row in packet["rows"]:
                    path = root / row["media_ref"]; path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"png")
            first = canonical_bundle_tree_sha256(root, public)
            second = canonical_bundle_tree_sha256(root, public)
            self.assertEqual(first, second)
            validate_canonical_bundle_tree(root, public, first)
            (root / "extra").write_text("x")
            with self.assertRaisesRegex(ValueError, "closed tree"):
                canonical_bundle_tree_sha256(root, public)
            (root / "extra").unlink()
            target = root / next(iter({r["media_ref"] for p in public["packets"] for r in p["rows"]}))
            target.unlink(); target.symlink_to(root / "public-reviewer-index.json")
            with self.assertRaisesRegex(ValueError, "symlinks"):
                canonical_bundle_tree_sha256(root, public)

    def test_renderer_sanitizes_48_rows_hashes_tree_and_is_atomic(self):
        proof, config, private, public = self.schedule()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            files = {}
            for name, value in (("private", private), ("public", public),
                                ("proof", proof), ("config", config)):
                path = root / f"{name}.json"
                if name == "config":
                    path.write_bytes((ROOT / "config/structural-chapter-blind-schedule-v1.json").read_bytes())
                else: path.write_text(json.dumps(value, sort_keys=True))
                files[name] = path
            salt = root / "salt"; salt.write_text("4" * 64 + "\n"); salt.chmod(0o600)
            media = root / "media.mkv"; media.write_bytes(b"synthetic")
            output = root / "bundle"
            proof_hash = digest(files["proof"].read_bytes())
            kwargs = dict(private_schedule_path=files["private"], private_schedule_sha256=digest(files["private"].read_bytes()), public_index_path=files["public"], public_index_sha256=digest(files["public"].read_bytes()), selection_proof_path=files["proof"], config_path=files["config"], presentation_salt_path=salt, render_media_path=media, render_media_sha256=config["selection"]["source_sha256"], output_directory=output, ffmpeg="fake")
            def fake_run(command, **unused):
                Path(command[-1]).write_bytes(png()); return mock.Mock(returncode=0)
            def fake_file_sha(path):
                return (config["selection"]["source_sha256"] if path == media
                        else digest(path.read_bytes()))
            with mock.patch("aegis360.structural_blind_renderer.PROOF_SHA256", proof_hash), mock.patch("aegis360.structural_blind_renderer.validate_exact_schedule"), mock.patch("aegis360.structural_blind_renderer.sha256_file", side_effect=fake_file_sha), mock.patch("subprocess.run", side_effect=fake_run) as run:
                result = render_structural_blind_bundle(**kwargs)
            self.assertEqual(run.call_count, 48); self.assertEqual(result["row_count"], 48)
            validate_canonical_bundle_tree(output, public, result["bundle_tree_sha256"])
            self.assertEqual((output / "public-reviewer-index.json").read_bytes(), files["public"].read_bytes())
            self.assertTrue(all(b"tEXt" not in p.read_bytes() for p in (output / "media").rglob("*.png")))
            wrong_source = dict(kwargs)
            wrong_source["output_directory"] = root / "wrong-source"
            wrong_source["render_media_sha256"] = digest(media.read_bytes())
            with mock.patch("aegis360.structural_blind_renderer.PROOF_SHA256", proof_hash), \
                 mock.patch("aegis360.structural_blind_renderer.validate_exact_schedule"), \
                 self.assertRaisesRegex(ValueError, "proof-selected source"):
                render_structural_blind_bundle(**wrong_source)
            with mock.patch("subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "output exists"):
                    render_structural_blind_bundle(**kwargs)
            run.assert_not_called()


if __name__ == "__main__": unittest.main()
