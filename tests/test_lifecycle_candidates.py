import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.lifecycle_candidates import lifecycle_candidate_frames
from aegis360.interest import evaluate_interest


def state(timestamp, phase, missing):
    return {
        "timestamp": timestamp,
        "phase": phase,
        "consecutive_missing": missing,
        "editorial_persistence_allowed": False,
        "identity_verified": False,
    }


class LifecycleCandidateTests(unittest.TestCase):
    def setUp(self):
        self.lifecycle = {
            "schema_version": "aegis360.refresh-lifecycle-trace.v1",
            "track_id": "bike-1",
            "states": [
                state(1, "active", 0),
                state(2, "missing_grace", 1),
                state(3, "terminated", 2),
            ],
        }
        self.tracking = {
            "trackId": "bike-1",
            "observations": [
                {
                    "timestampSeconds": timestamp,
                    "state": "tracked",
                    "yawRadians": .1,
                    "pitchRadians": -.2,
                }
                for timestamp in (1, 2, 3, 4)
            ],
        }

    def test_candidate_is_active_then_grace_then_removed_permanently(self):
        frames = lifecycle_candidate_frames(
            self.lifecycle,
            self.tracking,
            horizontal_fov=math.radians(100),
            candidate_type="bicycle",
        )
        subjects = [
            [item for item in frame.candidates if item.track_id]
            for frame in frames
        ]
        self.assertEqual([len(items) for items in subjects], [1, 1, 0, 0])
        self.assertTrue(subjects[0][0].observed)
        self.assertFalse(subjects[1][0].observed)
        self.assertEqual(subjects[1][0].missing_frames, 1)
        self.assertFalse(subjects[0][0].editorial_persistence_valid)
        scored = evaluate_interest(frames)
        persistence = next(
            signal
            for item in scored[0].candidates
            if item.candidate.track_id
            for signal in item.signals
            if signal.name == "persistence"
        )
        self.assertEqual(persistence.normalized, 0)
        self.assertEqual(
            [len(frame.candidates) for frame in frames], [2, 2, 1, 1]
        )

    def test_mismatched_ids_and_missing_preterminal_state_fail_closed(self):
        self.tracking["trackId"] = "other"
        with self.assertRaisesRegex(ValueError, "IDs"):
            lifecycle_candidate_frames(
                self.lifecycle, self.tracking, horizontal_fov=1,
                candidate_type="bicycle",
            )
        self.tracking["trackId"] = "bike-1"
        self.lifecycle["states"].pop(1)
        with self.assertRaisesRegex(ValueError, "timestamps"):
            lifecycle_candidate_frames(
                self.lifecycle, self.tracking, horizontal_fov=1,
                candidate_type="bicycle",
            )


if __name__ == "__main__":
    unittest.main()
