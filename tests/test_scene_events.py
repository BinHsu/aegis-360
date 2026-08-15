from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.scene_events import build_scene_events, parse_scene_metadata


class SceneEventsTests(unittest.TestCase):
    def test_parser_pairs_timestamps_and_scores(self):
        output = "frame:0 pts:10 pts_time:1.5\nlavfi.scene_score=0.500000\nframe:1 pts:20 pts_time:2.5\nlavfi.scene_score=0.750000\n"
        self.assertEqual(parse_scene_metadata(output), [
            {"timestamp_seconds": 1.5, "scene_score": 0.5},
            {"timestamp_seconds": 2.5, "scene_score": 0.75},
        ])

    def test_closed_artifact_rejects_below_threshold(self):
        with self.assertRaises(ValueError):
            build_scene_events(
                source_id="fixture", source_sha256="a" * 64, threshold=.6,
                sample_fps=2, proxy_width=320, ffmpeg_version="ffmpeg fixture",
                metadata_output="frame:0 pts:10 pts_time:1.5\nlavfi.scene_score=0.5\n",
            )


if __name__ == "__main__":
    unittest.main()
