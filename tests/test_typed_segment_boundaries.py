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

from aegis360.typed_segment_boundaries import (build_typed_segment_boundaries,
                                               validate_typed_segment_boundaries)
from tests.test_continuous_onset_semantic import ContinuousOnsetSemanticTests
from aegis360.continuous_onset_semantic_evidence import build_continuous_onset_semantic_evidence
from aegis360.continuous_onset_semantic_packet import build_continuous_onset_semantic_packet


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class TypedSegmentBoundaryTests(unittest.TestCase):
    def setUp(self):
        fixture = ContinuousOnsetSemanticTests()
        fixture.setUp()
        self.onset, self.samples, self.grid, self.packet = (
            fixture.onset, fixture.samples, fixture.grid, fixture.packet)
        self.config = fixture.config()
        self.evidence = build_continuous_onset_semantic_evidence(
            self.config, self.packet, config_sha256=digest(self.config),
            packet_sha256=digest(self.packet))
        self.policy = json.loads((ROOT / "config/typed-segment-boundary-policy-v1.json").read_text())

    def build(self, packets=None, evidences=None, onset=None):
        onset = self.onset if onset is None else onset
        packets = [self.packet] if packets is None else packets
        evidences = [self.evidence] if evidences is None else evidences
        return build_typed_segment_boundaries(
            onset, self.samples, self.grid, packets, evidences, self.policy,
            onset_sha256=digest(onset), samples_sha256=digest(self.samples),
            grid_sha256=digest(self.grid),
            packet_sha256s=[digest(item) for item in packets],
            evidence_sha256s=[digest(item) for item in evidences],
            policy_sha256=digest(self.policy))

    def test_story_change_authorizes_exact_first_sustained_high_only(self):
        result = self.build()
        row = result["boundaries"][0]
        self.assertEqual(row["disposition"], "authorized")
        self.assertEqual(row["effective_timestamp_seconds"], 385.75)
        self.assertEqual(result["boundary_authority"]["scope"], "authorized_rows_only")
        self.assertTrue(result["boundary_authority"]["artifact_validated"])
        self.assertFalse(result["boundary_authority"]["candidate_selected"])
        validate_typed_segment_boundaries(
            result, self.onset, self.samples, self.grid, [self.packet],
            [self.evidence], self.policy, onset_sha256=digest(self.onset),
            samples_sha256=digest(self.samples), grid_sha256=digest(self.grid),
            packet_sha256s=[digest(self.packet)],
            evidence_sha256s=[digest(self.evidence)], policy_sha256=digest(self.policy))

    def test_abstain_and_non_story_are_null(self):
        for classification, disposition in (("capture_artifact", "rejected"),
                                             ("no_semantic_change", "rejected"),
                                             ("unknown", "abstained")):
            evidence = copy.deepcopy(self.evidence)
            evidence["evidence"].update({
                "status": "abstain" if classification == "unknown" else "observed",
                "classification": classification, "structural_role": "unknown",
                "change_type": "unknown",
                "narrative_function": "unknown", "viewer_value": "unknown"})
            row = self.build(evidences=[evidence])["boundaries"][0]
            self.assertEqual(row["disposition"], disposition)
            self.assertIsNone(row["effective_timestamp_seconds"])

    def test_missing_duplicate_mismatch_and_tamper_fail_closed(self):
        for packets, evidences in (([], []),
                                   ([self.packet, self.packet],
                                    [self.evidence, self.evidence])):
            with self.assertRaises(ValueError):
                self.build(packets=packets, evidences=evidences)
        evidence = copy.deepcopy(self.evidence)
        evidence["candidate_id"] = "continuous-onset:other"
        with self.assertRaises(ValueError):
            self.build(evidences=[evidence])
        onset_two = copy.deepcopy(self.onset)
        second = copy.deepcopy(onset_two["candidates"][0])
        second["candidate_id"] = "continuous-onset:0001"
        onset_two["candidates"].append(second)
        packet_two = copy.deepcopy(self.packet)
        packet_two["candidate_id"] = second["candidate_id"]
        evidence_two = copy.deepcopy(self.evidence)
        evidence_two["candidate_id"] = second["candidate_id"]
        with self.assertRaises(ValueError):
            self.build(onset=onset_two, packets=[packet_two, self.packet],
                       evidences=[evidence_two, self.evidence])
        onset = copy.deepcopy(self.onset)
        onset["candidates"][0]["support_interval"]["start_seconds"] = 386.0
        with self.assertRaises(ValueError):
            self.build(onset=onset)
        result = self.build()
        result["boundaries"][0]["effective_timestamp_seconds"] = 386.0
        with self.assertRaises(ValueError):
            validate_typed_segment_boundaries(
                result, self.onset, self.samples, self.grid, [self.packet],
                [self.evidence], self.policy, onset_sha256=digest(self.onset),
                samples_sha256=digest(self.samples), grid_sha256=digest(self.grid),
                packet_sha256s=[digest(self.packet)],
                evidence_sha256s=[digest(self.evidence)], policy_sha256=digest(self.policy))

    def test_cli_is_atomic_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = {"onset": self.onset, "samples": self.samples,
                      "grid": self.grid, "policy": self.policy,
                      "packet": self.packet, "evidence": self.evidence}
            paths = {}
            for name, value in values.items():
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(value, sort_keys=True))
            output = root / "boundaries.json"
            command = [sys.executable,
                       str(ROOT / "scripts/build_typed_segment_boundaries.py"),
                       str(paths["onset"]), str(paths["samples"]),
                       str(paths["grid"]), str(paths["policy"]), str(output),
                       "--packet", str(paths["packet"]),
                       "--evidence", str(paths["evidence"])]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(output.read_text())["boundaries"][0]["disposition"],
                             "authorized")
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("refusing to overwrite", repeated.stderr)

    def test_cli_accepts_zero_candidates_without_review_flags(self):
        onset = copy.deepcopy(self.onset)
        onset["candidates"] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {}
            for name, value in (("onset", onset), ("samples", self.samples),
                                ("grid", self.grid), ("policy", self.policy)):
                paths[name] = root / f"{name}.json"
                paths[name].write_text(json.dumps(value, sort_keys=True))
            output = root / "boundaries.json"
            result = subprocess.run([
                sys.executable,
                str(ROOT / "scripts/build_typed_segment_boundaries.py"),
                str(paths["onset"]), str(paths["samples"]),
                str(paths["grid"]), str(paths["policy"]), str(output),
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            artifact = json.loads(output.read_text())
            self.assertEqual(artifact["boundaries"], [])
            self.assertEqual(
                artifact["boundary_authority"]["authorized_boundary_count"], 0)


if __name__ == "__main__":
    unittest.main()
