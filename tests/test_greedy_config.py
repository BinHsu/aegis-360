import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.greedy_config import (  # noqa: E402
    SCHEMA_VERSION,
    load_greedy_config,
    loads_greedy_config,
)


CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "greedy-first-slice-v1.toml"
)


class GreedyConfigTests(unittest.TestCase):
    def test_versioned_repository_config_loads_with_exact_editorial_weights(self):
        config = load_greedy_config(CONFIG_PATH)
        self.assertEqual(config.schema_version, SCHEMA_VERSION)
        self.assertEqual(
            dict(config.scoring.weights),
            {
                "presence": .35,
                "persistence": .30,
                "composition": .20,
                "forward_prior": .15,
            },
        )
        self.assertEqual(config.planner.minimum_dwell_seconds, 2.0)
        self.assertAlmostEqual(math.degrees(config.camera_min_angular_change), 2.0)

    def test_camera_threshold_has_inclusive_sparse_keyframe_semantics(self):
        config = load_greedy_config(CONFIG_PATH)
        self.assertFalse(config.camera_change_is_material(math.radians(1.99)))
        self.assertTrue(config.camera_change_is_material(math.radians(2.0)))
        self.assertEqual(
            config.trace_config()["camera"]["purpose"],
            "sparse_keyframe_threshold",
        )

    def test_detector_confidence_cannot_be_an_editorial_weight(self):
        content = CONFIG_PATH.read_text().replace(
            "presence = 0.35", "presence = 0.35\ndetector_confidence = 100"
        )
        with self.assertRaisesRegex(ValueError, "unknown weights.*detector_confidence"):
            loads_greedy_config(content)

    def test_missing_required_weight_is_rejected(self):
        content = CONFIG_PATH.read_text().replace("composition = 0.20\n", "")
        with self.assertRaisesRegex(ValueError, "missing editorial weight.*composition"):
            loads_greedy_config(content)

    def test_unknown_schema_and_fields_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "schema_version"):
            loads_greedy_config(
                CONFIG_PATH.read_text().replace(SCHEMA_VERSION, "future.v2")
            )
        with self.assertRaisesRegex(ValueError, "unknown hysteresis.*surprise"):
            loads_greedy_config(
                CONFIG_PATH.read_text().replace(
                    "switch_margin = 0.10", "switch_margin = 0.10\nsurprise = 1"
                )
            )

    def test_invalid_numeric_thresholds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "at most 180"):
            loads_greedy_config(
                CONFIG_PATH.read_text().replace(
                    "min_angular_change_degrees = 2.0",
                    "min_angular_change_degrees = 181",
                )
            )
        with self.assertRaisesRegex(ValueError, "switch_margin.*nonnegative"):
            loads_greedy_config(
                CONFIG_PATH.read_text().replace(
                    "switch_margin = 0.10", "switch_margin = -0.1"
                )
            )


if __name__ == "__main__":
    unittest.main()
