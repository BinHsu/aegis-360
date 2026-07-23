import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.perception import (  # noqa: E402
    AdapterProvenance,
    FrameSample,
    PerceptionAdapter,
    PerceptionResult,
    ScoringConfig,
    SignalEvidence,
    SphericalCandidateEvidence,
    to_greedy_observation,
)


PROVENANCE = AdapterProvenance(
    adapter_id="synthetic",
    adapter_version="1",
    backend_id="fixture-no-model",
    projection_strategy="synthetic-directions",
)


def candidate(yaw, signals=(), candidate_id="track:t1"):
    return SphericalCandidateEvidence(
        candidate_id=candidate_id,
        track_id="t1",
        yaw=math.radians(yaw),
        pitch=0.0,
        h_fov=math.radians(90),
        candidate_type="subject",
        signals=tuple(signals),
        observation_provenance=("synthetic-marker:m1",),
    )


class SyntheticAdapter:
    provenance = PROVENANCE

    def analyze(self, sample):
        return PerceptionResult(sample, self.provenance, (candidate(0),))


class PerceptionContractTests(unittest.TestCase):
    def test_synthetic_object_satisfies_runtime_protocol(self):
        adapter = SyntheticAdapter()
        self.assertIsInstance(adapter, PerceptionAdapter)
        result = adapter.analyze(FrameSample("job:fixture", 0.0, 0, 1024, 512))
        self.assertEqual(result.adapter.backend_id, "fixture-no-model")

    def test_seam_crossing_keeps_track_and_candidate_identity(self):
        before = candidate(179)
        after = candidate(-179)
        self.assertEqual(before.track_id, after.track_id)
        self.assertEqual(before.candidate_id, after.candidate_id)
        self.assertNotEqual(before.yaw, after.yaw)

    def test_missing_signal_is_explicit_and_maps_to_configured_fallback(self):
        missing = SignalEvidence(
            "motion_change", None, None, "synthetic:flow", "flow unavailable"
        )
        result = PerceptionResult(
            FrameSample("job:fixture", 1.0, 1, 1024, 512),
            PROVENANCE,
            (candidate(0, (missing,)),),
        )
        observation = to_greedy_observation(
            result,
            ScoringConfig((("motion_change", 0.25), ("novelty", 0.5))),
        )
        components = observation.candidates[0].components
        self.assertEqual([item.normalized for item in components], [0.0, 0.0])
        self.assertTrue(all(item.raw is None for item in components))
        self.assertIn("flow unavailable", components[0].provenance)
        self.assertIn("not_reported", components[1].provenance)

    def test_scoring_is_separate_from_adapter_evidence(self):
        evidence = SignalEvidence("presence", 0.8, 0.8, "synthetic:marker")
        result = PerceptionResult(
            FrameSample("job:fixture", 0.0, 0, 1024, 512),
            PROVENANCE,
            (candidate(0, (evidence,)),),
        )
        low = to_greedy_observation(result, ScoringConfig((("presence", 0.1),)))
        high = to_greedy_observation(result, ScoringConfig((("presence", 2.0),)))
        self.assertAlmostEqual(low.candidates[0].utility, 0.08)
        self.assertAlmostEqual(high.candidates[0].utility, 1.6)
        self.assertEqual(result.candidates[0].signals[0].normalized, 0.8)

    def test_rejects_invalid_normalized_values_and_ambiguous_missing(self):
        with self.assertRaises(ValueError):
            SignalEvidence("presence", 1.2, 1.2, "fixture")
        with self.assertRaises(ValueError):
            SignalEvidence("presence", None, None, "fixture")
        with self.assertRaises(ValueError):
            SignalEvidence("presence", 0.2, None, "fixture", "missing")

    def test_rejects_paths_bad_geometry_and_duplicate_candidate_ids(self):
        with self.assertRaises(ValueError):
            FrameSample("/private/video.mp4", 0, 0, 10, 10)
        with self.assertRaises(ValueError):
            candidate(181)
        duplicate = candidate(0)
        with self.assertRaises(ValueError):
            PerceptionResult(
                FrameSample("job:x", 0, 0, 10, 10),
                PROVENANCE,
                (duplicate, duplicate),
            )

    def test_validates_weight_and_weights_checksum(self):
        with self.assertRaises(ValueError):
            ScoringConfig((("presence", math.inf),))
        with self.assertRaises(ValueError):
            AdapterProvenance("x", "1", "backend", "erp", "not-a-digest")


if __name__ == "__main__":
    unittest.main()
