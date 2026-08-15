import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sound_events import LABELS, LIMITATIONS, validate_sound_events


def fixture():
    return {
        "schema_version": "aegis360.apple-sound-events.v1",
        "source_id": "fixture",
        "window": {"start_seconds": 10, "duration_seconds": 2,
                   "analysis_channel_count": 1, "analysis_sample_rate_hz": 44100},
        "classifier": {"framework": "Apple SoundAnalysis",
                       "identifier": "SNClassifierIdentifierVersion1",
                       "allowed_labels": list(LABELS), "overlap_factor": 0.5},
        "windows": [{"start_seconds": 10, "duration_seconds": 1,
                     "classifications": [
                         {"label": label, "confidence": .25} for label in LABELS
                     ]}],
        "privacy": {"contains_source_path": False, "contains_audio": False,
                    "contains_transcript": False},
        "limitations": list(LIMITATIONS),
    }


class SoundEventTests(unittest.TestCase):
    def test_closed_path_free_artifact(self):
        validate_sound_events(fixture())

    def test_rejects_unknown_label_or_path(self):
        for mutation in ("label", "path"):
            value = copy.deepcopy(fixture())
            if mutation == "label":
                value["windows"][0]["classifications"][0]["label"] = "speech"
            else:
                value["source_path"] = "/private/source.wav"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_sound_events(value)

    def test_rejects_out_of_window_or_nonfinite_confidence(self):
        for mutation in ("window", "confidence"):
            value = copy.deepcopy(fixture())
            if mutation == "window":
                value["windows"][0]["start_seconds"] = 12
            else:
                value["windows"][0]["classifications"][0]["confidence"] = float("nan")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_sound_events(value)


if __name__ == "__main__":
    unittest.main()
