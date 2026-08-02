import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.semantic_events import build_semantic_event_artifact
from aegis360.semantic_spherical import (
    build_semantic_spherical_artifact, semantic_events_to_spherical_results,
)
from aegis360.spherical_dedup import deduplicate_spherical_candidates


def viewport(viewport_id, yaw):
    return {
        "viewport_id": viewport_id,
        "yaw_radians": math.radians(yaw),
        "pitch_radians": 0,
        "horizontal_fov_radians": math.radians(100),
        "width_pixels": 416,
        "height_pixels": 416,
    }


def detection(source_index, x):
    return {
        "class_name": "person", "score": .7, "source_index": source_index,
        "box_top_left_normalized": [x, .4, .1, .2],
    }


class SemanticSphericalTests(unittest.TestCase):
    def test_overlapping_views_project_and_merge_without_identity(self):
        document = build_semantic_event_artifact(
            source_id="fixture", model_id="model",
            viewports=(viewport("front", 0), viewport("right", 90)),
            events=(
                {"timestamp_seconds": 1, "viewport_id": "front",
                 "detections": [detection(0, .85)]},
                {"timestamp_seconds": 1, "viewport_id": "right",
                 "detections": [detection(0, .05)]},
            ),
        )
        results = semantic_events_to_spherical_results(document)
        self.assertEqual(len(results), 1)
        self.assertEqual(len(results[0].candidates), 2)
        self.assertTrue(all(item.track_id is None for item in results[0].candidates))
        deduped = deduplicate_spherical_candidates(results[0])
        self.assertEqual(len(deduped.clusters), 1)
        self.assertEqual(len(deduped.clusters[0].members), 2)
        self.assertEqual(deduped.clusters[0].candidate.signals, ())
        artifact = build_semantic_spherical_artifact(document)
        self.assertEqual(artifact["summary"]["raw_observation_count"], 2)
        self.assertEqual(artifact["summary"]["merged_cluster_count"], 1)
        self.assertEqual(artifact["summary"]["largest_cluster_size"], 2)
        self.assertFalse(artifact["samples"][0]["clusters"][0]["identity_verified"])

    def test_seam_views_merge_and_provenance_is_path_free(self):
        document = build_semantic_event_artifact(
            source_id="fixture", model_id="model",
            viewports=(viewport("east", 179), viewport("west", -179)),
            events=(
                {"timestamp_seconds": 0, "viewport_id": "east",
                 "detections": [detection(1, .45)]},
                {"timestamp_seconds": 0, "viewport_id": "west",
                 "detections": [detection(2, .45)]},
            ),
        )
        deduped = deduplicate_spherical_candidates(
            semantic_events_to_spherical_results(document)[0]
        )
        self.assertEqual(len(deduped.clusters), 1)
        provenance = "".join(deduped.clusters[0].candidate.observation_provenance)
        self.assertNotIn("/Users/", provenance)
        self.assertTrue(abs(abs(deduped.clusters[0].candidate.yaw) - math.pi) < .03)

    def test_old_schema_and_corrupt_event_fail_closed(self):
        base = build_semantic_event_artifact(
            source_id="fixture", model_id="model", viewports=(viewport("front", 0),),
            events=({"timestamp_seconds": 0, "viewport_id": "front",
                     "detections": [detection(0, .2)]},),
        )
        old = dict(base, schema_version="aegis360.semantic-detector-events.v1")
        with self.assertRaisesRegex(ValueError, "schema"):
            semantic_events_to_spherical_results(old)
        bad = dict(base)
        bad["events"] = [dict(base["events"][0], viewport_id="missing")]
        with self.assertRaisesRegex(ValueError, "viewport"):
            semantic_events_to_spherical_results(bad)


if __name__ == "__main__":
    unittest.main()
