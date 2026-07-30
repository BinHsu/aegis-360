from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class YoloXCoreMLStreamBenchmarkContractTests(unittest.TestCase):
    def test_runner_is_single_stream_load_once_bounded_and_privacy_safe(self):
        script = (
            ROOT / "scripts/benchmark_yolox_coreml_stream.py"
        ).read_text()
        self.assertEqual(script.count("ct.models.MLModel("), 1)
        self.assertEqual(script.count("subprocess.Popen("), 1)
        self.assertIn('"ffmpeg_process_count": 1', script)
        self.assertIn('"model_load_count": 1', script)
        self.assertIn('"rawvideo_bgr24"', script)
        self.assertIn("FRAME_BYTES", script)
        self.assertIn("decode_yolox(", script)
        self.assertIn("confidence_threshold=.25", script)
        self.assertIn("nms_iou_threshold=.45", script)
        self.assertIn('"stream_residual_wall_seconds"', script)
        self.assertIn('"yolox_decode_nms_seconds"', script)
        self.assertIn("not an exact CPU-time decomposition", script)
        self.assertIn('"contains_pixels": False', script)
        self.assertIn('"contains_source_path": False', script)
        self.assertIn('"persists_frames": False', script)
        self.assertIn("refusing to overwrite output directory", script)
        self.assertNotIn("TemporaryDirectory", script)
        self.assertNotIn("imwrite", script)


if __name__ == "__main__":
    unittest.main()
