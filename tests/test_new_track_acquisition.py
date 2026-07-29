import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.new_track_acquisition import (
    AcquisitionPolicy, evaluate_new_track_acquisition,
)


def trace(outcomes):
    return {
        "schema_version": "aegis360.detector-refresh-trace.v1",
        "events": [
            {
                "timestamp": index,
                "track_id": "old-track",
                "outcome": outcome,
            }
            for index, outcome in enumerate(outcomes, 1)
        ],
    }


class NewTrackAcquisitionTests(unittest.TestCase):
    def test_isolated_detection_does_not_acquire(self):
        result = evaluate_new_track_acquisition(
            trace((
                "no_compatible_detection",
                "compatible_not_identity_verified",
                "no_compatible_detection",
            )),
            terminated_at=0,
            new_track_id="new-track",
        )
        self.assertIsNone(result["new_track_id"])
        self.assertIsNone(result["acquired_at"])

    def test_two_consecutive_detections_acquire_fresh_nonidentity_track(self):
        result = evaluate_new_track_acquisition(
            trace((
                "compatible_not_identity_verified",
                "compatible_not_identity_verified",
            )),
            terminated_at=0,
            new_track_id="new-track",
        )
        self.assertEqual(result["new_track_id"], "new-track")
        self.assertEqual(result["acquired_at"], 2)
        self.assertFalse(result["policy"]["identity_verified"])
        self.assertFalse(result["policy"]["editorial_persistence_allowed"])
        with self.assertRaisesRegex(ValueError, "reuse"):
            evaluate_new_track_acquisition(
                trace(("compatible_not_identity_verified",) * 2),
                terminated_at=0,
                new_track_id="old-track",
            )

    def test_policy_is_bounded_and_ambiguity_resets_confirmation(self):
        with self.assertRaises(ValueError):
            AcquisitionPolicy(consecutive_compatible=1)
        result = evaluate_new_track_acquisition(
            trace((
                "compatible_not_identity_verified",
                "ambiguous_multiple_compatible",
                "compatible_not_identity_verified",
                "compatible_not_identity_verified",
            )),
            terminated_at=0,
            new_track_id="fresh",
        )
        self.assertEqual(result["acquired_at"], 4)

    def test_time_span_and_maximum_gap_are_cadence_safe(self):
        rapid = trace((
            "compatible_not_identity_verified",
            "compatible_not_identity_verified",
        ))
        rapid["events"][0]["timestamp"] = 1.0
        rapid["events"][1]["timestamp"] = 1.1
        result = evaluate_new_track_acquisition(
            rapid, terminated_at=0, new_track_id="rapid",
        )
        self.assertIsNone(result["acquired_at"])

        sparse = trace((
            "compatible_not_identity_verified",
            "compatible_not_identity_verified",
        ))
        sparse["events"][0]["timestamp"] = 1.0
        sparse["events"][1]["timestamp"] = 2.1
        result = evaluate_new_track_acquisition(
            sparse, terminated_at=0, new_track_id="sparse",
        )
        self.assertIsNone(result["acquired_at"])

        for label, second_timestamp in (("four-fps", 1.25), ("two-fps", 1.5)):
            with self.subTest(cadence=label):
                bounded = trace((
                    "compatible_not_identity_verified",
                    "compatible_not_identity_verified",
                ))
                bounded["events"][0]["timestamp"] = 1.0
                bounded["events"][1]["timestamp"] = second_timestamp
                result = evaluate_new_track_acquisition(
                    bounded,
                    terminated_at=0,
                    new_track_id=label,
                )
                self.assertEqual(result["acquired_at"], second_timestamp)


if __name__ == "__main__":
    unittest.main()
