import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.chapter_proposal_candidates import (  # noqa: E402
    build_chapter_proposal_candidates,
    validate_chapter_proposal_document,
)
from aegis360.visual_state_features import LIMITATIONS as FEATURE_LIMITATIONS  # noqa: E402


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def feature_state(kind: str) -> dict[str, object]:
    states = {
        "base": {
            "global_luma_mean": 0.2,
            "global_luma_stddev": 0.1,
            "edge_strength": 0.1,
            "spatial_luma_grid": [0.2] * 8,
            "rgb_histogram": [[1.0, 0.0, 0.0, 0.0]] * 3,
        },
        "global": {
            "global_luma_mean": 0.8,
            "global_luma_stddev": 0.7,
            "edge_strength": 0.7,
            "spatial_luma_grid": [0.2] * 8,
            "rgb_histogram": [[1.0, 0.0, 0.0, 0.0]] * 3,
        },
        "spatial": {
            "global_luma_mean": 0.8,
            "global_luma_stddev": 0.7,
            "edge_strength": 0.7,
            "spatial_luma_grid": [0.9, 0.9, 0.1, 0.1] * 2,
            "rgb_histogram": [[1.0, 0.0, 0.0, 0.0]] * 3,
        },
        "histogram": {
            "global_luma_mean": 0.8,
            "global_luma_stddev": 0.7,
            "edge_strength": 0.7,
            "spatial_luma_grid": [0.9, 0.9, 0.1, 0.1] * 2,
            "rgb_histogram": [[0.0, 0.0, 0.0, 1.0]] * 3,
        },
        "spike": {
            "global_luma_mean": 1.0,
            "global_luma_stddev": 1.0,
            "edge_strength": 1.0,
            "spatial_luma_grid": [1.0] * 8,
            "rgb_histogram": [[0.0, 0.0, 0.0, 1.0]] * 3,
        },
    }
    return copy.deepcopy(states[kind])


def visual_state_document(kinds: list[str]) -> dict[str, object]:
    samples = []
    zero_change = {
        "global_luma_delta": 0.0,
        "spatial_luma_l1": 0.0,
        "rgb_histogram_distance": 0.0,
        "edge_strength_delta": 0.0,
    }
    for index, kind in enumerate(kinds):
        samples.append(
            {
                "sample_index": index,
                "proxy_pts": index * 10,
                "proxy_time_seconds": float(index),
                "source_time": {"numerator": index, "denominator": 1},
                "features": feature_state(kind),
                "long_baseline_change": {
                    "from_5s": None if index < 5 else dict(zero_change),
                    "from_15s": None if index < 15 else dict(zero_change),
                },
            }
        )
    return {
        "schema_version": "aegis360.visual-state-features.v1",
        "source_id": "synthetic",
        "inputs": {
            "source_sha256": "a" * 64,
            "analysis_proxy_sha256": "b" * 64,
            "analysis_proxy_config_sha256": "c" * 64,
            "visual_state_config_sha256": "d" * 64,
        },
        "acquisition": {
            "config_id": "visual-state-1fps-96x48-grid4x2-v1",
            "sample_fps": 1,
            "frame_width": 96,
            "frame_height": 48,
            "frame_pixel_format": "rgb24",
            "filter_order": ["fps", "scale", "format_rgb24"],
            "sample_count": len(samples),
            "expected_count_rule": "floor(proxy_duration_seconds*1fps+0.5)",
            "bounded_history_frames": 16,
        },
        "timing": {
            "proxy_pts_time_base": {"numerator": 1, "denominator": 10},
            "sample_cadence_proxy_pts": 10,
            "source_origin": {"numerator": 0, "denominator": 1},
            "rule": "source_seconds=source_origin+proxy_pts*(1/10)",
        },
        "samples": samples,
        "privacy": {
            "contains_source_path": False,
            "contains_proxy_path": False,
            "contains_pixels": False,
            "contains_audio": False,
            "contains_identity": False,
        },
        "authority": {
            "semantic_labels": False,
            "event_proposals": False,
            "story_boundaries": False,
            "camera_commands": False,
            "render_commands": False,
        },
        "limitations": list(FEATURE_LIMITATIONS),
    }


class ChapterProposalCandidateTests(unittest.TestCase):
    def setUp(self):
        self.config_bytes = (
            ROOT / "config/chapter-proposal-candidates-v1.json"
        ).read_bytes()
        self.config = json.loads(self.config_bytes)

    def build(self, kinds):
        features = visual_state_document(kinds)
        payload = json.dumps(features, sort_keys=True).encode()
        inputs = {
            "visual_state_features": features,
            "visual_state_features_sha256": sha(payload),
            "config": self.config,
            "config_sha256": sha(self.config_bytes),
        }
        return build_chapter_proposal_candidates(**inputs), inputs

    def test_constant_emits_no_candidate(self):
        document, inputs = self.build(["base"] * 150)
        self.assertEqual(document["candidates"], [])
        self.assertFalse(document["authority"]["review_candidate_emitted"])
        self.assertTrue(document["policy"]["mad_zero"])
        self.assertEqual(document["privacy"], {
            "contains_source_path": False,
            "contains_pixels": False,
            "contains_audio": False,
            "contains_identity": False,
        })
        audit = document["policy"]["local_maxima_audit"]
        self.assertTrue(audit)
        self.assertTrue(all(row["disposition"] == "below_threshold"
                            for row in audit))
        self.assertEqual(
            document["policy"]["local_maxima_disposition_counts"]["emitted"], 0)
        validate_chapter_proposal_document(document, **inputs)

    def test_one_persistent_step_emits_one_near_transition(self):
        document, _ = self.build(["base"] * 70 + ["global"] * 80)
        self.assertEqual(len(document["candidates"]), 1)
        candidate = document["candidates"][0]
        self.assertLessEqual(abs(candidate["center_proxy_time_seconds"] - 70), 10)
        self.assertEqual(candidate["dominant_family"], "global")
        metrics = candidate["family_metrics"]["global"]
        self.assertEqual(metrics["state_distance"], 0.6)
        self.assertEqual(metrics["before_dispersion"], 0)
        self.assertEqual(metrics["after_dispersion"], 0)
        self.assertTrue(document["authority"]["review_candidate_emitted"])
        self.assertFalse(document["authority"]["story_boundary"])
        self.assertFalse(document["authority"]["candidate_selected"])
        self.assertFalse(document["authority"]["production_eligible"])
        self.assertFalse(document["authority"]["render"])
        emitted_audit = [row for row in document["policy"]["local_maxima_audit"]
                         if row["disposition"] == "emitted"]
        self.assertEqual(len(emitted_audit), 1)
        self.assertIn("dispersion_penalty",
                      emitted_audit[0]["family_metrics"]["global"])

    def test_transient_spike_emits_no_candidate(self):
        kinds = ["base"] * 150
        kinds[70] = "spike"
        document, _ = self.build(kinds)
        self.assertEqual(document["candidates"], [])

    def test_two_separated_family_different_steps_are_ordered(self):
        kinds = ["base"] * 70 + ["global"] * 90 + ["spatial"] * 90
        document, _ = self.build(kinds)
        self.assertEqual(len(document["candidates"]), 2)
        self.assertEqual(
            [row["dominant_family"] for row in document["candidates"]],
            ["global", "spatial_luma"],
        )
        timestamps = [
            row["center_proxy_time_seconds"] for row in document["candidates"]
        ]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_local_maxima_dispositions_cover_separation_cap_and_no_backfill(self):
        close_kinds = []
        close_state = "base"
        for index in range(185):
            if index in (70, 105):
                close_state = "global" if close_state == "base" else "base"
            close_kinds.append(close_state)
        close_document, _ = self.build(close_kinds)
        close_counts = close_document["policy"]["local_maxima_disposition_counts"]
        self.assertEqual(close_counts["minimum_separation"], 1)
        self.assertEqual(close_counts["emitted"], 1)

        capped_kinds = []
        capped_state = "base"
        transitions = (70, 140, 210, 280, 350, 420, 490)
        for index in range(570):
            if index in transitions:
                capped_state = "global" if capped_state == "base" else "base"
            capped_kinds.append(capped_state)
        capped_document, _ = self.build(capped_kinds)
        capped_counts = capped_document["policy"]["local_maxima_disposition_counts"]
        self.assertEqual(capped_counts["maximum_candidate_cap"], 1)
        self.assertEqual(capped_counts["emitted"], 6)
        self.assertEqual(len(capped_document["candidates"]), 6)
        self.assertEqual(
            sum(capped_counts.values()),
            len(capped_document["policy"]["local_maxima_audit"]),
        )

    def test_malformed_tamper_extra_hash_cadence_and_policy_fail_closed(self):
        document, inputs = self.build(["base"] * 70 + ["global"] * 80)
        tampered = copy.deepcopy(document)
        tampered["authority"]["story_boundary"] = True
        with self.assertRaises(ValueError):
            validate_chapter_proposal_document(tampered, **inputs)

        extra = copy.deepcopy(inputs["visual_state_features"])
        extra["source_path"] = "/tmp/forbidden"
        with self.assertRaises(ValueError):
            build_chapter_proposal_candidates(
                **dict(inputs, visual_state_features=extra)
            )
        duplicate = copy.deepcopy(inputs["visual_state_features"])
        duplicate["samples"][40]["proxy_time_seconds"] = 39.0
        with self.assertRaises(ValueError):
            build_chapter_proposal_candidates(
                **dict(inputs, visual_state_features=duplicate)
            )
        missing = copy.deepcopy(inputs["visual_state_features"])
        del missing["samples"][40]
        missing["acquisition"]["sample_count"] -= 1
        with self.assertRaises(ValueError):
            build_chapter_proposal_candidates(
                **dict(inputs, visual_state_features=missing)
            )
        with self.assertRaises(ValueError):
            build_chapter_proposal_candidates(
                **dict(inputs, visual_state_features_sha256="bad")
            )
        drifted = copy.deepcopy(self.config)
        drifted["maximum_candidates"] = 7
        with self.assertRaises(ValueError):
            build_chapter_proposal_candidates(**dict(inputs, config=drifted))
        type_drifted = copy.deepcopy(self.config)
        type_drifted["maximum_candidates"] = True
        with self.assertRaises(ValueError):
            build_chapter_proposal_candidates(**dict(inputs, config=type_drifted))

    def test_cli_is_atomic_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            features = visual_state_document(["base"] * 70 + ["global"] * 80)
            feature_path = root / "features.json"
            feature_path.write_text(json.dumps(features, sort_keys=True))
            output = root / "proposals.json"
            command = [
                sys.executable,
                str(ROOT / "scripts/build_chapter_proposal_candidates.py"),
                str(feature_path),
                str(ROOT / "config/chapter-proposal-candidates-v1.json"),
                str(output),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(len(json.loads(output.read_text())["candidates"]), 1)
            self.assertEqual(list(root.glob(".proposals.json.*")), [])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)

    def test_cli_cleans_owned_temporary_file_when_link_fails(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            features = visual_state_document(["base"] * 150)
            feature_path = root / "features.json"
            feature_path.write_text(json.dumps(features, sort_keys=True))
            output = root / "proposals.json"
            script_path = ROOT / "scripts/build_chapter_proposal_candidates.py"
            spec = importlib.util.spec_from_file_location("proposal_cli", script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            arguments = [
                str(script_path), str(feature_path),
                str(ROOT / "config/chapter-proposal-candidates-v1.json"),
                str(output),
            ]
            with mock.patch.object(sys, "argv", arguments), mock.patch.object(
                module.os, "link", side_effect=OSError("synthetic link failure")
            ):
                with self.assertRaisesRegex(OSError, "synthetic link failure"):
                    module.main()
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".proposals.json.*")), [])


if __name__ == "__main__":
    unittest.main()
