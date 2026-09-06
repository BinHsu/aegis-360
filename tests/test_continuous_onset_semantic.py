import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.context_views import build_context_view_grid
from aegis360.continuous_onset_candidates import build_continuous_onset_candidates
from aegis360.continuous_onset_semantic_packet import (
    build_continuous_onset_semantic_packet,
    validate_continuous_onset_semantic_packet,
)
from aegis360.continuous_onset_semantic_evidence import (
    build_continuous_onset_semantic_evidence,
    validate_continuous_onset_semantic_evidence,
)
from aegis360.frame_difference_samples import build_frame_difference_samples


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class ContinuousOnsetSemanticTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=385,
                                            duration_seconds=2)
        config = {"schema_version": "aegis360.frame-difference-acquisition-config.v1",
                  "config_id": "fixture", "pts_origin": "interval_local",
                  "metadata_key": "lavfi.signalstats.YAVG",
                  "normalization_divisor": 255.0}
        values = [10, 10, 10, 220, 230, 10, 10]
        metadata = "\n".join(
            f"frame:{i} pts:{i} pts_time:{i * .25}\nlavfi.signalstats.YAVG={value}"
            for i, value in enumerate(values))
        self.samples = build_frame_difference_samples(
            source_id="fixture", window=self.grid["window"], source_sha256="a" * 64,
            config=config, config_sha256=digest(config), metadata_text=metadata)
        policy = {"schema_version": "aegis360.continuous-onset-candidate-policy.v1",
                  "policy_id": "fixture", "baseline_window_samples": 3,
                  "high_threshold": .7, "release_threshold": .2,
                  "minimum_consecutive": 2,
                  "minimum_sample_cadence_seconds": .2,
                  "maximum_sample_cadence_seconds": .3,
                  "maximum_uncertainty_window_seconds": .3}
        self.onset = build_continuous_onset_candidates(
            self.samples, policy, samples_sha256=digest(self.samples),
            policy_sha256=digest(policy))
        self.packet = self.build_packet()

    def build_packet(self, onset=None):
        onset = self.onset if onset is None else onset
        return build_continuous_onset_semantic_packet(
            onset, self.samples, self.grid, candidate_id="continuous-onset:0000",
            onset_sha256=digest(onset), samples_sha256=digest(self.samples),
            grid_sha256=digest(self.grid))

    def config(self, classification="story_change", status="observed"):
        labels = (("within_chapter_cut", "gradual_transition",
                   "activity_transition", "primary")
                  if classification == "story_change" else ("unknown",) * 4)
        if status == "abstain":
            classification, labels = "unknown", ("unknown",) * 4
        return {"schema_version": "aegis360.continuous-onset-semantic-evidence-config.v1",
                "reviewer_type": "agent", "reviewer_id": "fixture-reviewer",
                "reviewer_asset_sha256": None, "status": status,
                "classification": classification, "structural_role": labels[0],
                "change_type": labels[1], "narrative_function": labels[2],
                "viewer_value": labels[3]}

    def test_packet_has_exact_five_rows_all_candidates_and_no_authority(self):
        self.assertEqual([row["temporal_role"] for row in self.packet["samples"]],
                         ["before", "lower_bound", "upper_bound", "support_end", "after"])
        ids = [item["candidate_id"] for item in self.grid["candidates"]]
        self.assertTrue(all(row["candidate_ids"] == ids for row in self.packet["samples"]))
        self.assertTrue(all(row["available"] for row in self.packet["samples"]))
        self.assertEqual([row["row_index"] for row in self.packet["samples"]],
                         [1, 2, 3, 4, 5])
        self.assertIsNone(self.packet["edge"])
        self.assertFalse(self.packet["privacy"]["contains_pixels"])
        validate_continuous_onset_semantic_packet(
            self.packet, self.onset, self.samples, self.grid,
            onset_sha256=digest(self.onset), samples_sha256=digest(self.samples),
            grid_sha256=digest(self.grid))

    def test_packet_rejects_hard_cut_missing_support_and_tamper(self):
        broken = copy.deepcopy(self.onset)
        broken["candidates"][0]["hard_cut_claimed"] = True
        with self.assertRaises(ValueError):
            self.build_packet(broken)
        broken = copy.deepcopy(self.onset)
        broken["candidates"][0]["support_interval"]["end_seconds"] = 386.9
        with self.assertRaises(ValueError):
            self.build_packet(broken)
        broken = copy.deepcopy(self.onset)
        broken["candidates"][0]["support_interval"]["supporting_sample_count"] = 3
        with self.assertRaises(ValueError):
            self.build_packet(broken)
        packet = copy.deepcopy(self.packet)
        packet["edge"] = {"from": "x"}
        with self.assertRaises(ValueError):
            validate_continuous_onset_semantic_packet(
                packet, self.onset, self.samples, self.grid,
                onset_sha256=digest(self.onset), samples_sha256=digest(self.samples),
                grid_sha256=digest(self.grid))

    def test_closed_semantic_labels_and_provenance_fail_closed(self):
        for classification in ("story_change", "capture_artifact", "no_semantic_change"):
            config = self.config(classification)
            value = build_continuous_onset_semantic_evidence(
                config, self.packet, config_sha256=digest(config),
                packet_sha256=digest(self.packet))
            self.assertFalse(value["planner_authority"]["production_eligible"])
            self.assertTrue(all(flag is False for flag in value["privacy"].values()))
            validate_continuous_onset_semantic_evidence(
                value, config, self.packet, config_sha256=digest(config),
                packet_sha256=digest(self.packet))
        config = self.config("capture_artifact")
        config["change_type"] = "motion_peak"
        with self.assertRaises(ValueError):
            build_continuous_onset_semantic_evidence(
                config, self.packet, config_sha256=digest(config),
                packet_sha256=digest(self.packet))

    def test_packet_exposes_explicit_null_after_at_window_edge(self):
        self.samples["samples"] = self.samples["samples"][:5]
        self.samples["window"]["duration_seconds"] = 1.0
        self.grid["window"]["duration_seconds"] = 1.0
        policy = self.onset["policy"]
        self.onset = build_continuous_onset_candidates(
            self.samples, policy, samples_sha256=digest(self.samples),
            policy_sha256=digest(policy))
        packet = self.build_packet()
        after = packet["samples"][-1]
        self.assertEqual(after["temporal_role"], "after")
        self.assertFalse(after["available"])
        self.assertIsNone(after["row_index"])
        self.assertIsNone(after["timestamp_seconds"])
        config = self.config(status="abstain")
        config["viewer_value"] = "low"
        with self.assertRaises(ValueError):
            build_continuous_onset_semantic_evidence(
                config, self.packet, config_sha256=digest(config),
                packet_sha256=digest(self.packet))

    def test_builder_and_binder_clis_are_atomic_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            onset_path, samples_path, grid_path = (root / "onset.json", root / "samples.json", root / "grid.json")
            for path, value in ((onset_path, self.onset), (samples_path, self.samples),
                                (grid_path, self.grid)):
                path.write_text(json.dumps(value, sort_keys=True))
            packet_path = root / "packet.json"
            packet_command = [sys.executable, str(ROOT / "scripts/build_continuous_onset_semantic_packet.py"),
                              str(onset_path), str(samples_path), str(grid_path),
                              "continuous-onset:0000", str(packet_path)]
            self.assertEqual(subprocess.run(packet_command).returncode, 0)
            self.assertNotEqual(subprocess.run(packet_command, capture_output=True).returncode, 0)
            config = self.config()
            config_path = root / "config.json"
            config_path.write_text(json.dumps(config, sort_keys=True))
            evidence_path = root / "evidence.json"
            bind_command = [sys.executable, str(ROOT / "scripts/bind_continuous_onset_semantic_evidence.py"),
                            str(config_path), str(packet_path), str(evidence_path)]
            self.assertEqual(subprocess.run(bind_command).returncode, 0)
            repeated = subprocess.run(bind_command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)


if __name__ == "__main__":
    unittest.main()
