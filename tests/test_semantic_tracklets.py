import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.perception import (
    AdapterProvenance, FrameSample, PerceptionResult, SphericalCandidateEvidence,
)
from aegis360.semantic_tracklets import build_semantic_tracklet_diagnostic


ADAPTER = AdapterProvenance("fixture", "1", "none", "spherical")


def candidate(name, yaw=0):
    return SphericalCandidateEvidence(
        name, None, math.radians(yaw), 0, math.radians(10), "person", (),
        (f"fixture:{name}",),
    )


def frame(index, *candidates):
    return PerceptionResult(
        FrameSample("fixture", index * .25, index, 100, 100),
        ADAPTER, tuple(candidates),
    )


class SemanticTrackletTests(unittest.TestCase):
    def test_two_confirmations_acquire_without_identity(self):
        report = build_semantic_tracklet_diagnostic((
            frame(0, candidate("a", 0)), frame(1, candidate("b", 1)),
            frame(2, candidate("c", 2)),
        ))
        self.assertEqual(len(report["acquisitions"]), 1)
        self.assertEqual(report["acquisitions"][0]["acquired_at"], .25)
        self.assertFalse(report["acquisitions"][0]["identity_verified"])
        self.assertFalse(report["policy"]["uses_detector_confidence"])

    def test_multiple_compatible_observations_are_ambiguous_not_nearest(self):
        report = build_semantic_tracklet_diagnostic((
            frame(0, candidate("seed", 0)),
            frame(1, candidate("left", -1), candidate("right", 1)),
        ))
        self.assertEqual(report["acquisitions"], [])
        self.assertEqual(report["samples"][1]["ambiguous_hypothesis_count"], 1)

    def test_termination_then_reacquisition_uses_fresh_id(self):
        report = build_semantic_tracklet_diagnostic((
            frame(0, candidate("a")), frame(1, candidate("b")),
            frame(2), frame(3), frame(4),
            frame(5, candidate("c")), frame(6, candidate("d")),
        ))
        self.assertEqual(
            [row["track_id"] for row in report["acquisitions"]],
            ["semantic-track:000001", "semantic-track:000002"],
        )
        self.assertEqual(report["terminations"][0]["track_id"], "semantic-track:000001")

    def test_timestamps_must_increase(self):
        with self.assertRaisesRegex(ValueError, "increase"):
            build_semantic_tracklet_diagnostic((frame(0), frame(0)))


if __name__ == "__main__":
    unittest.main()
