import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.visual_state_features import (  # noqa: E402
    build_visual_state_features, expected_sample_count,
    validate_proxy_bundle_for_features,
    validate_visual_state_feature_document,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class VisualStateFeatureTests(unittest.TestCase):
    def setUp(self):
        self.config_bytes = (ROOT / "config/visual-state-features-v1.json").read_bytes()
        self.config = json.loads(self.config_bytes)
        self.proxy_config_bytes = (ROOT / "config/analysis-proxy-bundle-v1.json").read_bytes()
        self.proxy_hash = "c" * 64
        self.bundle = {
            "schema_version": "aegis360.analysis-proxy-bundle.v1",
            "source_id": "fixture",
            "inputs": {"source_sha256": "a" * 64,
                       "config_sha256": digest(self.proxy_config_bytes),
                       "proxy_sha256": self.proxy_hash},
            "source_interval": {"start": {"numerator": 0, "denominator": 1},
                                "duration": {"numerator": 16, "denominator": 1}},
            "proxy": {"external_file": "analysis-proxy.mkv", "contains_pixels": True,
                      "codec": "ffv1", "container": "matroska", "width": 960,
                      "height": 480, "pixel_format": "yuv420p", "frame_rate": "10/1",
                      "sample_aspect_ratio": "1:1", "video_only": True},
            "timing": {"proxy_zero_affine_mapping": {
                "proxy_time_base": {"numerator": 1, "denominator": 10},
                "source_origin": {"numerator": 13, "denominator": 5},
                "rule": "source_seconds=source_origin+proxy_pts*(1/10)"},
                "maximum_selection_error_seconds": 0.05},
            "probe": {"stream_count": 1, "stream_types": ["video"],
                      "codec_name": "ffv1", "width": 960, "height": 480,
                      "pixel_format": "yuv420p", "frame_rate": "10/1",
                      "time_base": "1/1000", "start_pts": 0,
                      "start_time_seconds": 0.0, "duration_seconds": 16.0,
                      "sample_aspect_ratio": "1:1", "format_name": "matroska,webm",
                      "color_range": "unknown", "color_space": "unknown",
                      "color_transfer": "unknown", "color_primaries": "unknown"},
            "runtime": {},
            "privacy": {"manifest_contains_source_path": False,
                        "manifest_contains_pixels": False,
                        "external_proxy_contains_pixels": True},
            "performance_claims": {}, "limitations": [],
        }

    def frame(self, value):
        return bytes([value, value, value]) * (96 * 48)

    def test_ffmpeg_near_rounded_sample_count_boundaries(self):
        self.assertEqual(expected_sample_count(16.4), 16)
        self.assertEqual(expected_sample_count(16.6), 17)

    def build(self, frames):
        return build_visual_state_features(
            bundle=self.bundle, proxy_sha256=self.proxy_hash,
            proxy_config_sha256=digest(self.proxy_config_bytes), config=self.config,
            config_sha256=digest(self.config_bytes), frames=iter(frames),
            frame_count=16)

    def test_constant_state_is_zero_and_path_pixel_free(self):
        artifact = self.build([self.frame(64)] * 16)
        self.assertEqual(len(artifact["samples"]), 16)
        self.assertEqual(artifact["samples"][0]["source_time"],
                         {"numerator": 13, "denominator": 5})
        self.assertEqual(artifact["samples"][15]["proxy_pts"], 150)
        for sample in artifact["samples"][15:]:
            for change in sample["long_baseline_change"].values():
                self.assertTrue(all(value == 0 for value in change.values()))
        payload = json.dumps(artifact)
        validate_visual_state_feature_document(artifact)
        self.assertNotIn("/private/", payload)
        self.assertNotIn("/Volumes/", payload)
        self.assertNotIn("pixels", json.dumps(artifact["samples"]))
        self.assertEqual(artifact["authority"]["story_boundaries"], False)

    def test_persistent_gradual_shift_and_transient_spike_remain_descriptors(self):
        gradual = self.build([self.frame(20 + index * 10) for index in range(16)])
        changes = [row["long_baseline_change"]["from_5s"]
                   for row in gradual["samples"][5:]]
        self.assertTrue(all(row["global_luma_delta"] > 0.15 for row in changes))
        transient_frames = [self.frame(20)] * 16
        transient_frames[8] = self.frame(240)
        transient = self.build(transient_frames)
        self.assertGreater(transient["samples"][8]["long_baseline_change"]["from_5s"]
                           ["global_luma_delta"], 0.8)
        self.assertEqual(transient["samples"][9]["features"]["global_luma_mean"],
                         transient["samples"][0]["features"]["global_luma_mean"])
        self.assertFalse(any(transient["authority"].values()))
        tampered = copy.deepcopy(transient)
        tampered["samples"][2]["proxy_pts"] = 30
        with self.assertRaisesRegex(ValueError, "non-monotonic"):
            validate_visual_state_feature_document(tampered)

    def test_tamper_count_partial_and_extra_path_fail_closed(self):
        tampered = copy.deepcopy(self.bundle)
        tampered["inputs"]["proxy_sha256"] = "d" * 64
        with self.assertRaises(ValueError):
            validate_proxy_bundle_for_features(
                tampered, proxy_sha256=self.proxy_hash,
                proxy_config_sha256=digest(self.proxy_config_bytes))
        with_path = copy.deepcopy(self.bundle)
        with_path["probe"]["source_path"] = "/private/source.mkv"
        with self.assertRaises(ValueError):
            validate_proxy_bundle_for_features(
                with_path, proxy_sha256=self.proxy_hash,
                proxy_config_sha256=digest(self.proxy_config_bytes))
        with self.assertRaisesRegex(ValueError, "ended before"):
            self.build([self.frame(1)] * 15)
        with self.assertRaisesRegex(ValueError, "extra"):
            self.build([self.frame(1)] * 17)
        broken = [self.frame(1)] * 15 + [b"short"]
        with self.assertRaisesRegex(ValueError, "byte count"):
            self.build(broken)

    def test_closed_document_and_canonical_proxy_fields_reject_tamper(self):
        artifact = self.build([self.frame(64)] * 16)
        document_mutations = []
        extra_acquisition = copy.deepcopy(artifact)
        extra_acquisition["acquisition"]["path"] = "/tmp/proxy"
        document_mutations.append(extra_acquisition)
        bad_dimensions = copy.deepcopy(artifact)
        bad_dimensions["acquisition"]["frame_width"] = 95
        document_mutations.append(bad_dimensions)
        extra_timing = copy.deepcopy(artifact)
        extra_timing["timing"]["local_path"] = "/tmp"
        document_mutations.append(extra_timing)
        bad_limitations = copy.deepcopy(artifact)
        bad_limitations["limitations"].append("added claim")
        document_mutations.append(bad_limitations)
        bad_histogram = copy.deepcopy(artifact)
        bad_histogram["samples"][0]["features"]["rgb_histogram"][0][0] = 0.1
        document_mutations.append(bad_histogram)
        for mutated in document_mutations:
            with self.assertRaises(ValueError):
                validate_visual_state_feature_document(mutated)

        proxy_mutations = []
        for key, value in (
            ("stream_count", 2), ("stream_types", ["video", "audio"]),
            ("time_base", "1/10"), ("sample_aspect_ratio", "2:1"),
            ("format_name", "matroska"), ("duration_seconds", None),
        ):
            mutated = copy.deepcopy(self.bundle)
            mutated["probe"][key] = value
            proxy_mutations.append(mutated)
        bad_interval = copy.deepcopy(self.bundle)
        bad_interval["source_interval"]["start"]["denominator"] = 0
        proxy_mutations.append(bad_interval)
        extra_interval = copy.deepcopy(self.bundle)
        extra_interval["source_interval"]["source_path"] = "/tmp/source"
        proxy_mutations.append(extra_interval)
        for mutated in proxy_mutations:
            with self.assertRaises(ValueError):
                validate_proxy_bundle_for_features(
                    mutated, proxy_sha256=self.proxy_hash,
                    proxy_config_sha256=digest(self.proxy_config_bytes))

    def test_fake_ffmpeg_runner_is_streaming_atomic_and_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            bundle_dir = root / "bundle"
            bundle_dir.mkdir()
            proxy = bundle_dir / "analysis-proxy.mkv"
            proxy.write_bytes(b"proxy")
            bundle = copy.deepcopy(self.bundle)
            bundle["inputs"]["proxy_sha256"] = digest(b"proxy")
            (bundle_dir / "manifest.json").write_text(json.dumps(bundle))
            ffmpeg = root / "ffmpeg"
            ffmpeg.write_text(textwrap.dedent("""\
                #!/usr/bin/env python3
                import os, sys
                count = int(os.environ.get("FRAME_COUNT", "16"))
                payload = bytes([64, 64, 64]) * (96 * 48)
                for _ in range(count):
                    sys.stdout.buffer.write(payload)
                if os.environ.get("PARTIAL"):
                    sys.stdout.buffer.write(b"x")
                raise SystemExit(int(os.environ.get("FFMPEG_RC", "0")))
            """))
            ffmpeg.chmod(0o755)
            output = root / "out.json"
            command = [sys.executable, str(ROOT / "scripts/build_visual_state_features.py"),
                       str(bundle_dir), str(ROOT / "config/analysis-proxy-bundle-v1.json"),
                       str(ROOT / "config/visual-state-features-v1.json"), str(output)]
            env = dict(os.environ, PATH=f"{root}:{os.environ['PATH']}")
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["acquisition"]
                             ["bounded_history_frames"], 16)
            self.assertEqual(list(root.glob(".out.json.*")), [])
            second = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)
            for key, value in (("FRAME_COUNT", "15"), ("FRAME_COUNT", "17"),
                               ("PARTIAL", "1"), ("FFMPEG_RC", "3")):
                failed = root / f"{key}.json"
                case_command = command[:-1] + [str(failed)]
                case_env = dict(env, **{key: value})
                got = subprocess.run(case_command, env=case_env,
                                     capture_output=True, text=True)
                self.assertNotEqual(got.returncode, 0)
                self.assertFalse(failed.exists())

            missing_duration = copy.deepcopy(bundle)
            missing_duration["probe"]["duration_seconds"] = None
            (bundle_dir / "manifest.json").write_text(json.dumps(missing_duration))
            missing_output = root / "missing-duration.json"
            got = subprocess.run(command[:-1] + [str(missing_output)], env=env,
                                 capture_output=True, text=True)
            self.assertNotEqual(got.returncode, 0)
            self.assertIn("proxy duration must be finite", got.stderr)
            self.assertNotIn("Traceback", got.stderr)
            self.assertFalse(missing_output.exists())


if __name__ == "__main__":
    unittest.main()
