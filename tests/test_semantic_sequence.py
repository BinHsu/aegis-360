import math
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_sequence import merge_lifecycle_candidate_sequences


def lifecycle(track_id, states):
    return {
        "schema_version": "aegis360.refresh-lifecycle-trace.v1",
        "track_id": track_id,
        "states": [
            {
                "timestamp": timestamp,
                "phase": phase,
                "consecutive_missing": missing,
                "editorial_persistence_allowed": False,
                "identity_verified": False,
            }
            for timestamp, phase, missing in states
        ],
    }


def tracking(track_id, timestamps, yaw):
    return {
        "trackId": track_id,
        "observations": [
            {
                "timestampSeconds": timestamp,
                "state": "tracked",
                "yawRadians": yaw,
                "pitchRadians": 0.0,
            }
            for timestamp in timestamps
        ],
    }


class SemanticSequenceTests(unittest.TestCase):
    def test_merges_overlapping_tracks_and_removes_each_at_termination(self):
        frames = merge_lifecycle_candidate_sequences((
            (
                lifecycle("bike-1", ((0, "active", 0), (1, "terminated", 1))),
                tracking("bike-1", (0, 1, 2), math.radians(45)),
                "bicycle",
            ),
            (
                lifecycle("person-1", ((1, "active", 0), (2, "active", 0))),
                tracking("person-1", (1, 2), math.radians(-60)),
                "person",
            ),
        ), horizontal_fov=math.radians(100))
        self.assertEqual([frame.timestamp for frame in frames], [0, 1, 2])
        ids = [[candidate.candidate_id for candidate in frame.candidates] for frame in frames]
        self.assertEqual(ids[0], ["context:forward", "lifecycle:bike-1"])
        self.assertEqual(ids[1], ["context:forward", "lifecycle:person-1"])
        self.assertEqual(ids[2], ["context:forward", "lifecycle:person-1"])

    def test_duplicate_track_ids_and_empty_input_fail_closed(self):
        item = (
            lifecycle("bike-1", ((0, "active", 0),)),
            tracking("bike-1", (0,), 0),
            "bicycle",
        )
        with self.assertRaisesRegex(ValueError, "unique"):
            merge_lifecycle_candidate_sequences(
                (item, item), horizontal_fov=1,
            )
        with self.assertRaisesRegex(ValueError, "at least one"):
            merge_lifecycle_candidate_sequences((), horizontal_fov=1)


if __name__ == "__main__":
    unittest.main()
