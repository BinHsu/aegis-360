import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.reaction_intervals import build_reaction_intervals
from aegis360.sound_events import LABELS, LIMITATIONS


def fixture(scores):
    rows = []
    for index, (applause, clapping) in enumerate(scores):
        values = {"music": .5, "applause": applause, "clapping": clapping, "cheering": .1}
        rows.append({"start_seconds": index * 1.5, "duration_seconds": 3,
                     "classifications": [
                         {"label": label, "confidence": values[label]} for label in LABELS
                     ]})
    return {
        "schema_version": "aegis360.apple-sound-events.v1", "source_id": "fixture",
        "window": {"start_seconds": 0, "duration_seconds": 12,
                   "analysis_channel_count": 1, "analysis_sample_rate_hz": 44100},
        "classifier": {"framework": "Apple SoundAnalysis",
                       "identifier": "SNClassifierIdentifierVersion1",
                       "allowed_labels": list(LABELS), "overlap_factor": .5},
        "windows": rows,
        "privacy": {"contains_source_path": False, "contains_audio": False,
                    "contains_transcript": False},
        "limitations": list(LIMITATIONS),
    }


class ReactionIntervalTests(unittest.TestCase):
    def test_concurrent_overlapping_windows_merge(self):
        result = build_reaction_intervals(fixture([
            (.7, .8), (.6, .7), (.1, .8), (.8, .1), (.8, .8), (.9, .9),
        ]))
        self.assertEqual(len(result["intervals"]), 2)
        self.assertEqual(result["intervals"][0]["supporting_window_count"], 2)
        self.assertEqual(result["intervals"][0]["start_seconds"], 0)
        self.assertEqual(result["intervals"][0]["end_seconds"], 4.5)
        self.assertEqual(result["policy"]["status"], "poc_hypothesis_not_editorial_ground_truth")

    def test_single_window_and_single_label_fail_closed(self):
        result = build_reaction_intervals(fixture([(.9, .9), (.9, .1), (.1, .9)]))
        self.assertEqual(result["intervals"], [])

    def test_thresholds_are_bounded(self):
        with self.assertRaises(ValueError):
            build_reaction_intervals(fixture([]), applause_threshold=1.1)


if __name__ == "__main__":
    unittest.main()
