import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXMultiviewEventsContractTests(unittest.TestCase):
    def test_runner_is_load_once_serial_bounded_and_privacy_safe(self):
        script = (ROOT / "scripts/run_yolox_multiview_events.py").read_text()
        self.assertEqual(script.count("ct.models.MLModel("), 1)
        self.assertEqual(script.count("subprocess.Popen("), 1)
        self.assertIn('"model_load_count": 1', script)
        self.assertIn('"ffmpeg_streams_serial": True', script)
        self.assertIn('"bgr24"', script)
        self.assertIn("decode_yolox_numpy", script)
        self.assertIn("confidence_threshold=.25", script)
        self.assertIn("nms_iou_threshold=.45", script)
        self.assertIn("vision_seed_box", script)
        self.assertIn("build_semantic_event_artifact", script)
        self.assertIn("refusing to overwrite output directory", script)
        self.assertNotIn("imwrite", script)

    def test_repository_config_has_six_unique_bounded_viewports(self):
        config = json.loads(
            (ROOT / "config/semantic-multiview-six-v1.json").read_text()
        )
        self.assertEqual(
            config["schema_version"],
            "aegis360.semantic-multiview-config.v1",
        )
        self.assertEqual(len(config["viewports"]), 6)
        self.assertEqual(
            len({row["viewport_id"] for row in config["viewports"]}), 6
        )
        self.assertEqual(config["viewport_width"], 416)
        self.assertEqual(config["viewport_height"], 416)
        self.assertLessEqual(config["boundary_tolerance_pixels"], 1)


if __name__ == "__main__":
    unittest.main()
