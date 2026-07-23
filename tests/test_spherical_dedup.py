import json
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.perception import (  # noqa: E402
    AdapterProvenance, FrameSample, PerceptionResult, SignalEvidence,
    SphericalCandidateEvidence,
)
from aegis360.spherical_dedup import (  # noqa: E402
    SphericalDedupConfig, deduplicate_spherical_candidates,
    vision_gate_json_to_perception,
)

ADAPTER = AdapterProvenance("fixture", "1", "none", "viewports")
SAMPLE = FrameSample("fixture:frame", 1.0, 3, 1024, 512)


def candidate(candidate_id, kind, yaw, extent=10, confidence=0.5):
    return SphericalCandidateEvidence(
        candidate_id, None, math.radians(yaw), 0.0, math.radians(extent), kind,
        (SignalEvidence("detector_confidence", confidence, confidence, candidate_id),),
        (f"viewport:{candidate_id}",),
    )


class SphericalDedupTests(unittest.TestCase):
    def test_seam_adjacent_duplicates_merge_and_retain_all_sources(self):
        result = PerceptionResult(
            SAMPLE, ADAPTER,
            (candidate("west", "human", -179), candidate("east", "human", 179)),
        )
        deduped = deduplicate_spherical_candidates(result)
        self.assertEqual(len(deduped.result.candidates), 1)
        cluster = deduped.clusters[0]
        self.assertEqual([item.candidate_id for item in cluster.members], ["east", "west"])
        self.assertTrue(abs(abs(cluster.candidate.yaw) - math.pi) < 1e-9)
        self.assertIn("duplicate-source:east", cluster.candidate.observation_provenance)
        self.assertIn("viewport:west", cluster.candidate.observation_provenance)
        self.assertEqual(cluster.candidate.signals, ())

    def test_different_kinds_never_merge(self):
        result = PerceptionResult(
            SAMPLE, ADAPTER,
            (candidate("a", "human", 0), candidate("b", "attention_saliency", 0)),
        )
        self.assertEqual(len(deduplicate_spherical_candidates(result).clusters), 2)

    def test_distance_boundary_is_inclusive_and_order_independent(self):
        config = SphericalDedupConfig(
            max_center_distance=math.radians(5),
            extent_overlap_scale=1, minimum_extent_gate=0,
        )
        exact = candidate("z", "human", 5, extent=10)
        origin = candidate("a", "human", 0, extent=10)
        first = deduplicate_spherical_candidates(
            PerceptionResult(SAMPLE, ADAPTER, (exact, origin)), config
        )
        second = deduplicate_spherical_candidates(
            PerceptionResult(SAMPLE, ADAPTER, (origin, exact)), config
        )
        self.assertEqual(len(first.clusters), 1)
        self.assertEqual(first.result.candidates, second.result.candidates)
        outside = candidate("z", "human", 5.0001, extent=10)
        separated = deduplicate_spherical_candidates(
            PerceptionResult(SAMPLE, ADAPTER, (origin, outside)), config
        )
        self.assertEqual(len(separated.clusters), 2)

    def test_empty_and_missing_vision_inputs(self):
        empty = {
            "schemaVersion": 1,
            "provenance": {
                "adapterId": "apple", "adapterVersion": "1",
                "backendId": "vision", "projectionStrategy": "viewports",
                "weightsSha256": None,
            },
            "frames": [],
        }
        self.assertEqual(vision_gate_json_to_perception(empty, width=10, height=10), ())
        missing = dict(empty)
        missing.pop("frames")
        with self.assertRaisesRegex(ValueError, "frames"):
            vision_gate_json_to_perception(missing, width=10, height=10)

    def test_vision_viewports_combine_and_preserve_confidence_as_evidence(self):
        row = {
            "id": "front:human:0", "kind": "human", "confidence": 0.7,
            "yawRadians": 0.1, "pitchRadians": 0.0,
            "horizontalFovRadians": 0.2, "viewportId": "front",
            "boundingBox": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.4},
        }
        document = {
            "schemaVersion": 1,
            "provenance": {
                "adapterId": "apple", "adapterVersion": "1",
                "backendId": "vision", "projectionStrategy": "viewports",
                "weightsSha256": None,
            },
            "frames": [
                {"sourceId": "job:safe", "frameIndex": 2,
                 "timestampSeconds": 1.5, "candidates": [row]},
                {"sourceId": "job:safe", "frameIndex": 2,
                 "timestampSeconds": 1.5,
                 "candidates": [{**row, "id": "right:human:0",
                                 "viewportId": "right", "yawRadians": 0.11,
                                 "confidence": 0.2}]},
            ],
        }
        results = vision_gate_json_to_perception(json.dumps(document), width=1024, height=512)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0].candidates), 2)
        self.assertEqual(results[0].candidates[1].signals[0].normalized, 0.2)
        deduped = deduplicate_spherical_candidates(results[0])
        self.assertEqual(len(deduped.clusters), 1)
        self.assertEqual(len(deduped.clusters[0].members), 2)


if __name__ == "__main__":
    unittest.main()
