import copy
import hashlib
import json
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
from aegis360.blind_chapter_review_renderer import (  # noqa: E402
    PNG_SIGNATURE, render_blind_chapter_review_bundle,
)
from aegis360.blind_chapter_review_schedule import (  # noqa: E402
    build_blind_chapter_review_schedule,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def png_chunk(kind, payload):
    body = kind + payload
    return (struct.pack(">I", len(payload)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xffffffff))


def fake_png(width, height):
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    pixels = b"".join(b"\x00" + b"\x11\x22\x33" * width for _ in range(height))
    return (PNG_SIGNATURE + png_chunk(b"IHDR", header)
            + png_chunk(b"tEXt", b"private_role=proposal absolute_time=30 yaw=90")
            + png_chunk(b"IDAT", zlib.compress(pixels)) + png_chunk(b"IEND", b""))


def proposal_document(policy_sha):
    center = 100
    origin = Fraction(7, 1000)
    source = origin + center
    metric = {"state_distance": 0.2, "before_dispersion": 0.01,
              "after_dispersion": 0.01, "dispersion_penalty": 0.02,
              "persistence_adjusted_score": 0.18}
    return {
        "schema_version": "aegis360.chapter-proposal-candidates.v1",
        "source_id": "fixture", "inputs": {
            "visual_state_features_sha256": "a" * 64,
            "chapter_proposal_config_sha256": policy_sha},
        "policy": {"config_id": "chapter-proposals-persistent-state-v1",
                   "eligible_center_count": 557, "score_median": 0.01,
                   "score_mad": 0.01, "mad_zero": False,
                   "emission_threshold": 0.08,
                   "threshold_comparison": "greater-than-or-equal",
                   "local_maximum_radius_seconds": 10,
                   "local_plateau_rule": "earliest",
                   "minimum_temporal_separation_seconds": 45,
                   "maximum_candidates": 6,
                   "selection_rule": "qualified-local-maxima-score-descending-with-temporal-separation",
                   "dominant_family_diversity_rule": "record-only-no-quota-no-backfill-family-order-resolves-dominant-score-ties",
                   "local_maxima_audit": [],
                   "local_maxima_disposition_counts": {
                       "below_threshold": 0, "minimum_separation": 0,
                       "maximum_candidate_cap": 0, "emitted": 1}},
        "candidates": [{"candidate_id": "chapter-proposal-01",
                        "center_proxy_time_seconds": center,
                        "center_source_time": {"numerator": source.numerator,
                                               "denominator": source.denominator},
                        "support_windows": {"before_proxy_seconds_half_open": [70, 90],
                                            "after_proxy_seconds_half_open": [110, 130],
                                            "samples_per_window": 20},
                        "uncertainty": {"kind": "symmetric-temporal-review-radius",
                                        "radius_seconds": 10},
                        "family_metrics": {name: dict(metric) for name in
                                           ("global", "spatial_luma", "rgb_histogram")},
                        "dominant_family": "global",
                        "persistence_adjusted_score": 0.18}],
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_identity": False},
        "authority": {"review_candidate_emitted": True, "story_boundary": False,
                      "candidate_selected": False, "production_eligible": False,
                      "render": False},
        "limitations": [
            "candidates are visual-state review proposals, not semantic chapter labels",
            "fixed support windows cannot propose within 30 seconds of either endpoint",
            "distribution-relative thresholding does not manufacture weak candidates"],
    }


class BlindChapterReviewRendererTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config_path = ROOT / "config/blind-chapter-review-schedule-v1.json"
        self.config = json.loads(self.config_path.read_bytes())
        self.policy_sha = "2" * 64
        self.protocol_sha = "3" * 64
        self.salt = "4" * 64
        self.salt_path = self.root / "salt"
        self.salt_path.write_text(self.salt + "\n")
        self.source = self.root / "source.mkv"
        self.source.write_bytes(b"frozen-source-fixture")
        self.source_sha = "1" * 64
        self.render_media_sha = sha(self.source.read_bytes())
        self.proposals = proposal_document(self.policy_sha)
        self.proposals_path = self.root / "proposals.json"
        self.proposals_path.write_text(json.dumps(self.proposals, sort_keys=True))
        self.proposals_sha = sha(self.proposals_path.read_bytes())
        private, public = build_blind_chapter_review_schedule(
            proposals=self.proposals, proposals_sha256=self.proposals_sha,
            source_sha256=self.source_sha, policy_sha256=self.policy_sha,
            protocol_sha256=self.protocol_sha, config=self.config,
            config_sha256=sha(self.config_path.read_bytes()),
            presentation_salt_hex=self.salt)
        self.private = private
        self.private_path = self.root / "private.json"
        self.public_path = self.root / "public.json"
        self.private_path.write_text(json.dumps(private, sort_keys=True))
        self.public_path.write_text(json.dumps(public, sort_keys=True))

    def tearDown(self):
        self.temporary.cleanup()

    def kwargs(self, output):
        return dict(private_schedule_path=self.private_path,
                    public_index_path=self.public_path,
                    proposals_path=self.proposals_path, config_path=self.config_path,
                    presentation_salt_path=self.salt_path,
                    render_media_path=self.source, output_directory=output,
                    proposals_sha256=self.proposals_sha,
                    source_sha256=self.source_sha, policy_sha256=self.policy_sha,
                    protocol_sha256=self.protocol_sha,
                    render_media_sha256=self.render_media_sha,
                    panel_width=4, panel_height=2, ffmpeg="fake-ffmpeg")

    @staticmethod
    def fake_run(command, **_kwargs):
        Path(command[-1]).write_bytes(fake_png(8, 4))
        return mock.Mock(returncode=0)

    def test_exact_render_public_refs_complete_and_metadata_stripped(self):
        output = self.root / "bundle"
        with mock.patch("subprocess.run", side_effect=self.fake_run) as run:
            result = render_blind_chapter_review_bundle(**self.kwargs(output))
        public = json.loads((output / "public-reviewer-index.json").read_bytes())
        refs = {row["media_ref"] for packet in public["packets"] for row in packet["rows"]}
        actual = {path.relative_to(output).as_posix()
                  for path in (output / "media").rglob("*.png")}
        self.assertEqual(refs, actual)
        self.assertEqual(result, {"packet_count": 4, "row_count": 24})
        self.assertEqual(run.call_count, 24)
        expected_proxy_times = [
            f"{row['absolute_proxy_time_seconds']:.9f}"
            for entry in self.private["entries"] for row in entry["rows"]]
        actual_seek_times = [call.args[0][call.args[0].index("-ss") + 1]
                             for call in run.call_args_list]
        self.assertEqual(actual_seek_times, expected_proxy_times)
        self.assertNotEqual(self.source_sha, self.render_media_sha)
        public_bytes = json.dumps(public["packets"], sort_keys=True).encode().lower()
        for forbidden in (b"absolute", b"proposal", b"control", b"sha256",
                          b"yaw", b"pitch", b"fov", b"cardinal"):
            self.assertNotIn(forbidden, public_bytes)
        for path in (output / "media").rglob("*.png"):
            data = path.read_bytes()
            self.assertNotIn(b"tEXt", data)
            self.assertNotIn(b"private_role", data)

    def test_schedule_tamper_and_render_media_hash_fail_before_render(self):
        public = json.loads(self.public_path.read_bytes())
        public["packets"][0]["rows"][0]["row_role"] = "absolute_time"
        self.public_path.write_text(json.dumps(public))
        output = self.root / "tampered"
        with mock.patch("subprocess.run") as run:
            with self.assertRaises(ValueError):
                render_blind_chapter_review_bundle(**self.kwargs(output))
        run.assert_not_called()
        self.assertFalse(output.exists())
        # Restore the schedule, then prove rendering media has an independent hash gate.
        self.public_path.write_text(json.dumps(build_blind_chapter_review_schedule(
            proposals=self.proposals, proposals_sha256=self.proposals_sha,
            source_sha256=self.source_sha, policy_sha256=self.policy_sha,
            protocol_sha256=self.protocol_sha, config=self.config,
            config_sha256=sha(self.config_path.read_bytes()),
            presentation_salt_hex=self.salt)[1], sort_keys=True))
        inputs = self.kwargs(self.root / "wrong-render-hash")
        inputs["render_media_sha256"] = "f" * 64
        with mock.patch("subprocess.run") as run:
            with self.assertRaisesRegex(ValueError, "render media"):
                render_blind_chapter_review_bundle(**inputs)
        run.assert_not_called()

    def test_atomic_failure_and_no_overwrite(self):
        output = self.root / "bundle"
        calls = 0

        def fail_second(command, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic renderer failure")
            return self.fake_run(command)

        with mock.patch("subprocess.run", side_effect=fail_second):
            with self.assertRaises(OSError):
                render_blind_chapter_review_bundle(**self.kwargs(output))
        self.assertFalse(output.exists())
        output.mkdir()
        marker = output / "owner-data"
        marker.write_text("keep")
        with mock.patch("subprocess.run") as run:
            with self.assertRaisesRegex(ValueError, "overwrite"):
                render_blind_chapter_review_bundle(**self.kwargs(output))
        run.assert_not_called()
        self.assertEqual(marker.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
