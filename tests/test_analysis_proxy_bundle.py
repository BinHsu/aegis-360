import copy
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

from aegis360.analysis_proxy_bundle import (  # noqa: E402
    build_analysis_proxy_bundle,
    validate_analysis_proxy_bundle,
)


class AnalysisProxyBundleTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(
            (ROOT / "config/analysis-proxy-bundle-v1.json").read_text()
        )
        self.bundle_inputs = {
            "source_id": "fixture",
            "source_sha256": "a" * 64,
            "config": self.config,
            "config_sha256": "b" * 64,
            "proxy_sha256": "c" * 64,
            "source_timing": {
                "first_pts": 9000,
                "time_base_numerator": 1,
                "time_base_denominator": 90000,
            },
            "source_interval": {
                "start": {"numerator": 5, "denominator": 2},
                "duration": {"numerator": 60, "denominator": 1},
            },
            "probe": {
                "stream_count": 1,
                "stream_types": ["video"],
                "codec_name": "ffv1",
                "width": 960,
                "height": 480,
                "pixel_format": "yuv420p",
                "frame_rate": "10/1",
                "time_base": "1/1000",
                "start_pts": 0,
                "start_time_seconds": 0.0,
                "duration_seconds": 60.0,
                "sample_aspect_ratio": "1:1",
                "format_name": "matroska,webm",
                "color_range": "unknown",
                "color_space": "unknown",
                "color_transfer": "unknown",
                "color_primaries": "unknown",
            },
            "runtime": {"elapsed_seconds": 2.0, "output_bytes": 100},
        }

    def test_manifest_timing_privacy_and_unknown_color(self):
        manifest = build_analysis_proxy_bundle(**self.bundle_inputs)
        self.assertEqual(
            manifest["timing"]["proxy_zero_affine_mapping"]["source_origin"],
            {"numerator": 13, "denominator": 5},
        )
        self.assertEqual(
            manifest["source_interval"]["duration"],
            {"numerator": 60, "denominator": 1},
        )
        self.assertTrue(manifest["privacy"]["external_proxy_contains_pixels"])
        self.assertFalse(manifest["performance_claims"]["peak_rss_measured"])
        self.assertFalse(manifest["privacy"]["manifest_contains_source_path"])
        validate_analysis_proxy_bundle(manifest, **self.bundle_inputs)

        unreduced = copy.deepcopy(self.bundle_inputs["source_interval"])
        unreduced["start"] = {"numerator": 10, "denominator": 4}
        normalized = build_analysis_proxy_bundle(
            **dict(self.bundle_inputs, source_interval=unreduced)
        )
        self.assertEqual(
            normalized["source_interval"]["start"],
            {"numerator": 5, "denominator": 2},
        )

    def test_tamper_and_contract_fail_closed(self):
        manifest = build_analysis_proxy_bundle(**self.bundle_inputs)
        manifest["proxy"]["codec"] = "h264"
        with self.assertRaises(ValueError):
            validate_analysis_proxy_bundle(manifest, **self.bundle_inputs)

        config = copy.deepcopy(self.config)
        config["filter_order"].reverse()
        with self.assertRaises(ValueError):
            build_analysis_proxy_bundle(**dict(self.bundle_inputs, config=config))

        invalid_intervals = (
            {
                "start": {"numerator": -1, "denominator": 1},
                "duration": None,
            },
            {
                "start": {"numerator": 0, "denominator": 1},
                "duration": {"numerator": 0, "denominator": 1},
            },
        )
        for interval in invalid_intervals:
            with self.assertRaises(ValueError):
                build_analysis_proxy_bundle(
                    **dict(self.bundle_inputs, source_interval=interval)
                )

        invalid_probe = dict(
            self.bundle_inputs["probe"], stream_types=["video", "audio"]
        )
        with self.assertRaises(ValueError):
            build_analysis_proxy_bundle(
                **dict(self.bundle_inputs, probe=invalid_probe)
            )
        short_probe = dict(self.bundle_inputs["probe"], duration_seconds=59.0)
        with self.assertRaises(ValueError):
            build_analysis_proxy_bundle(**dict(self.bundle_inputs, probe=short_probe))

        for unsafe_id in (
            "/private/source.webm",
            "~/source.webm",
            "folder/source.webm",
        ):
            with self.assertRaisesRegex(ValueError, "path-free"):
                build_analysis_proxy_bundle(
                    **dict(self.bundle_inputs, source_id=unsafe_id)
                )

    def test_runner_bounded_atomic_validation_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "in.mkv"
            source.write_bytes(b"source")
            output = root / "bundle"
            argument_log = root / "argv.json"

            ffmpeg = root / "ffmpeg"
            ffmpeg.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import os
                    import pathlib
                    import sys

                    pathlib.Path(os.environ["ARGV_LOG"]).write_text(
                        json.dumps(sys.argv[1:])
                    )
                    if os.environ.get("FAIL_PROXY"):
                        raise SystemExit(7)
                    pathlib.Path(sys.argv[-1]).write_bytes(b"proxy")
                    """
                )
            )
            ffmpeg.chmod(0o755)

            ffprobe = root / "ffprobe"
            ffprobe.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env python3
                    import json
                    import os
                    import sys

                    path = sys.argv[-1]
                    proxy = path.endswith("analysis-proxy.mkv")
                    bad = os.environ.get("BAD_PROXY")
                    stream = {
                        "codec_type": "video",
                        "codec_name": "ffv1" if proxy else "vp9",
                        "width": 320 if proxy and bad else 960,
                        "height": 480,
                        "pix_fmt": "yuv420p",
                        "r_frame_rate": "10/1",
                        "time_base": "1/1000" if proxy else "1/90000",
                        "start_pts": 0 if proxy else 9000,
                        "start_time": "0",
                        "sample_aspect_ratio": "1:1",
                    }
                    if not proxy:
                        stream["duration"] = "60"
                    streams = [stream]
                    if proxy and os.environ.get("AUDIO_PROXY"):
                        streams.append({"codec_type": "audio"})
                    requested_format_duration = any(
                        "format=format_name,duration" in argument
                        for argument in sys.argv[1:]
                    )
                    format_probe = {"format_name": "matroska,webm"}
                    if requested_format_duration:
                        format_probe["duration"] = "60"
                    print(json.dumps({
                        "streams": streams,
                        "format": format_probe,
                    }))
                    """
                )
            )
            ffprobe.chmod(0o755)

            environment = dict(
                os.environ,
                PATH=f"{root}:{os.environ['PATH']}",
                ARGV_LOG=str(argument_log),
            )
            base_command = [
                sys.executable,
                str(ROOT / "scripts/build_analysis_proxy_bundle.py"),
                str(source),
                "fixture",
                str(ROOT / "config/analysis-proxy-bundle-v1.json"),
            ]
            command = base_command + [
                str(output),
                "--start-seconds",
                "2.5",
                "--duration-seconds",
                "60",
            ]
            first = subprocess.run(
                command, env=environment, capture_output=True, text=True
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(list(root.glob(".bundle.*")), [])

            arguments = json.loads(argument_log.read_text())
            self.assertLess(arguments.index("-i"), arguments.index("-ss"))
            self.assertEqual(arguments[arguments.index("-ss") + 1], "2.5")
            self.assertEqual(arguments[arguments.index("-t") + 1], "60")
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(
                manifest["timing"]["proxy_zero_affine_mapping"]["source_origin"],
                {"numerator": 13, "denominator": 5},
            )

            second = subprocess.run(
                command, env=environment, capture_output=True, text=True
            )
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)

            failure_cases = (
                ("ffmpeg-failed", "FAIL_PROXY"),
                ("validation-failed", "BAD_PROXY"),
                ("audio-failed", "AUDIO_PROXY"),
            )
            for name, environment_key in failure_cases:
                failed_output = root / name
                case_environment = dict(environment)
                case_environment[environment_key] = "1"
                result = subprocess.run(
                    base_command
                    + [
                        str(failed_output),
                        "--start-seconds",
                        "0",
                        "--duration-seconds",
                        "60",
                    ],
                    env=case_environment,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(failed_output.exists())
                self.assertEqual(list(root.glob(f".{name}.*")), [])

    def test_runner_rejects_unpaired_and_nonfinite_intervals(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "in"
            source.write_bytes(b"x")
            base_command = [
                sys.executable,
                str(ROOT / "scripts/build_analysis_proxy_bundle.py"),
                str(source),
                "fixture",
                str(ROOT / "config/analysis-proxy-bundle-v1.json"),
                str(root / "out"),
            ]
            invalid_arguments = (
                ["--start-seconds", "1"],
                ["--duration-seconds", "1"],
                ["--start-seconds", "-1", "--duration-seconds", "1"],
                ["--start-seconds", "0", "--duration-seconds", "0"],
                ["--start-seconds", "nan", "--duration-seconds", "1"],
            )
            for extra_arguments in invalid_arguments:
                result = subprocess.run(
                    base_command + extra_arguments,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
