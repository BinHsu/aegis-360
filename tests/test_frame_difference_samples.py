import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.frame_difference_samples import (
    build_frame_difference_samples, parse_frame_difference_metadata,
    validate_frame_difference_samples,
)
from aegis360.continuous_onset_candidates import build_continuous_onset_candidates


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class FrameDifferenceSamplesTests(unittest.TestCase):
    def setUp(self):
        self.window = {"start_seconds": 380.0, "duration_seconds": 10.0}
        self.config = {
            "schema_version": "aegis360.frame-difference-acquisition-config.v1",
            "config_id": "ffmpeg-signalstats-yavg-v1",
            "pts_origin": "interval_local",
            "metadata_key": "lavfi.signalstats.YAVG",
            "normalization_divisor": 255.0,
        }
        self.metadata = "\n".join([
            "frame:0 pts:0 pts_time:0.0", "lavfi.signalstats.YAVG=0",
            "frame:1 pts:1 pts_time:2.5", "lavfi.signalstats.YAVG=127.5",
            "frame:2 pts:2 pts_time:10.0", "lavfi.signalstats.YAVG=255",
        ])

    def build(self, **overrides):
        arguments = {
            "source_id": "skiing:t380-t390", "window": self.window,
            "source_sha256": "a" * 64, "config": self.config,
            "config_sha256": digest(self.config), "metadata_text": self.metadata,
        }
        arguments.update(overrides)
        return build_frame_difference_samples(**arguments)

    def test_parses_order_and_maps_local_pts_to_absolute_window(self):
        result = self.build()
        self.assertEqual([row["pts_seconds"] for row in result["samples"]],
                         [380.0, 382.5, 390.0])
        self.assertEqual([row["normalized_difference"] for row in result["samples"]],
                         [0.0, 0.5, 1.0])
        self.assertFalse(result["privacy"]["contains_pixels"])
        self.assertFalse(result["privacy"]["contains_source_path"])
        self.assertNotIn("source_path", result["inputs"])

    def test_missing_or_malformed_pairs_fail(self):
        cases = [
            "frame:0 pts:0 pts_time:0",
            "lavfi.signalstats.YAVG=1",
            "frame:broken\nlavfi.signalstats.YAVG=1",
            "frame:0 pts:0 pts_time:0\nframe:1 pts:1 pts_time:1\nlavfi.signalstats.YAVG=1",
            "frame:0 pts:0 pts_time:0\nlavfi.signalstats.YAVG=broken",
        ]
        for metadata in cases:
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                self.build(metadata_text=metadata)

    def test_nonfinite_bool_and_ranges_fail(self):
        for value in (math.nan, math.inf, True, -1.0, 256.0):
            if isinstance(value, bool):
                window = {"start_seconds": value, "duration_seconds": 10.0}
                with self.assertRaises(ValueError):
                    self.build(window=window)
            else:
                metadata = f"frame:0 pts:0 pts_time:0\nlavfi.signalstats.YAVG={value}"
                with self.assertRaises(ValueError):
                    self.build(metadata_text=metadata)
        with self.assertRaises(ValueError):
            self.build(window={"start_seconds": 0, "duration_seconds": True})

    def test_duplicate_out_of_order_and_outside_pts_fail(self):
        for points in ((1, 1), (2, 1), (0, 10.1), (-1, 0)):
            metadata = "\n".join(
                f"frame:{index} pts:{index} pts_time:{point}\nlavfi.signalstats.YAVG=1"
                for index, point in enumerate(points)
            )
            with self.subTest(points=points), self.assertRaises(ValueError):
                self.build(metadata_text=metadata)

    def test_checksum_config_and_tamper_fail_closed(self):
        with self.assertRaises(ValueError):
            self.build(config_sha256="bad")
        broken = copy.deepcopy(self.config)
        broken["normalization_divisor"] = 1.0
        with self.assertRaises(ValueError):
            self.build(config=broken, config_sha256=digest(broken))
        result = self.build()
        validate_frame_difference_samples(
            result, source_id="skiing:t380-t390", window=self.window,
            source_sha256="a" * 64, config=self.config,
            config_sha256=digest(self.config), metadata_text=self.metadata,
        )
        result["samples"][0]["normalized_difference"] = 0.25
        with self.assertRaises(ValueError):
            validate_frame_difference_samples(
                result, source_id="skiing:t380-t390", window=self.window,
                source_sha256="a" * 64, config=self.config,
                config_sha256=digest(self.config), metadata_text=self.metadata,
            )

    def test_artifact_feeds_continuous_onset_without_field_adapter(self):
        values = [25.5, 25.5, 25.5, 102.0, 127.5, 25.5]
        self.metadata = "\n".join(
            f"frame:{index} pts:{index} pts_time:{index * 0.25}\n"
            f"lavfi.signalstats.YAVG={value}"
            for index, value in enumerate(values)
        )
        artifact = self.build()
        policy = {
            "schema_version": "aegis360.continuous-onset-candidate-policy.v1",
            "policy_id": "fixture", "baseline_window_samples": 3,
            "high_threshold": 0.4, "release_threshold": 0.2,
            "minimum_consecutive": 2,
            "minimum_sample_cadence_seconds": 0.2,
            "maximum_sample_cadence_seconds": 0.3,
            "maximum_uncertainty_window_seconds": 0.3,
        }
        result = build_continuous_onset_candidates(
            artifact, policy, samples_sha256=digest(artifact),
            policy_sha256=digest(policy),
        )
        self.assertEqual(result["candidates"][0]["uncertainty_interval"],
                         {"start_seconds": 380.5, "end_seconds": 380.75})
        self.assertFalse(result["planner_authority"]["story_boundary_emitted"])


if __name__ == "__main__":
    unittest.main()
