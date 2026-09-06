import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.structural_chapter_labeled_contrast import (  # noqa: E402
    PACKET_SOURCE_ID, build_artifact, evaluation_metrics, frame_descriptor, run_episode_audit,
    sample_plan, validate_artifact, validate_config,
)


class StructuralContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_bytes = (ROOT / "config/structural-chapter-labeled-contrast-v1.json").read_bytes()
        cls.config = json.loads(cls.config_bytes)
        cls.fixture_bytes = (ROOT / "benchmarks/structural-episode-fixtures-v1.json").read_bytes()
        cls.fixtures = json.loads(cls.fixture_bytes)

    def test_frozen_config_and_grid_mapping(self):
        validate_config(self.config)
        self.assertEqual(PACKET_SOURCE_ID, self.config["source"]["id"] + ".webm")
        plan = sample_plan(self.config)
        self.assertEqual([r["frame_index"] for r in plan["event:multi:0005"]], [98, 99, 100, 101, 110, 111, 112, 113])
        self.assertEqual(len({r["frame_index"] for rows in plan.values() for r in rows}), 30)
        self.assertTrue(all(len({r["frame_index"] for r in rows}) == 8
                            for rows in plan.values()))
        tampered = copy.deepcopy(self.config); tampered["descriptor"]["rounding"]["digits"] = 7
        with self.assertRaises(ValueError): validate_config(tampered)
        extra = copy.deepcopy(self.config); extra["local_path"] = "/tmp/source"
        with self.assertRaises(ValueError): validate_config(extra)

    def test_sobel_wrap_reflect_orientation_and_shift(self):
        constant = bytes([30]) * (160 * 80)
        mag, ori = frame_descriptor(constant)
        self.assertEqual(mag, [0.0] * 32); self.assertEqual(ori, [[0.0] * 8] * 32)
        vertical_edge = bytes((255 if x < 20 else 0) for y in range(80) for x in range(160))
        metrics = evaluation_metrics([vertical_edge] * 4 + [vertical_edge[20:] + vertical_edge[:20]] * 4)
        self.assertTrue(0 <= metrics["selected_horizontal_tile_shift"] <= 7)
        self.assertTrue(all(isinstance(metrics[k], float) for k in ("score", "state_distance", "before_dispersion")))

    def test_episode_fixture_exact_results(self):
        result = run_episode_audit(self.fixtures)
        self.assertEqual(len(result), 8)
        self.assertEqual(result[0]["pairs"], [["e0", "x0"]])
        self.assertEqual(result[-1]["pairs"], [["e0", "x1"]])
        bad = copy.deepcopy(self.fixtures); bad["cases"][0]["expected_pairs"] = []
        with self.assertRaisesRegex(ValueError, "expected result"): run_episode_audit(bad)

    def test_artifact_exact_privacy_authority_and_missing_sample(self):
        plan = sample_plan(self.config); indices = {r["frame_index"] for rows in plan.values() for r in rows}
        frames = {i: bytes([i % 256]) * (160 * 80) for i in indices}
        source_hash = self.config["source"]["sha256"]
        kwargs = dict(config=self.config, config_sha256=hashlib.sha256(self.config_bytes).hexdigest(), fixture_sha256=hashlib.sha256(self.fixture_bytes).hexdigest(), source_sha256_before=source_hash, source_sha256_after=source_hash, frame_count=max(indices) + 2, selected_frames=frames, episode_results=run_episode_audit(self.fixtures))
        artifact = build_artifact(**kwargs); validate_artifact(artifact, **kwargs)
        payload = json.dumps(artifact)
        self.assertNotIn("/Volumes/", payload); self.assertFalse(any(artifact["authority"].values()))
        mutated = copy.deepcopy(artifact); mutated["gate"]["secondary_authority"] = "gate"
        with self.assertRaises(ValueError): validate_artifact(mutated, **kwargs)
        missing = dict(kwargs, selected_frames={k: v for k, v in frames.items() if k != min(indices)})
        with self.assertRaisesRegex(ValueError, "missing"): build_artifact(**missing)


if __name__ == "__main__": unittest.main()
