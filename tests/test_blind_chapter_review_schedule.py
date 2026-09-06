import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.blind_chapter_review_schedule import (  # noqa: E402
    HARD_NEGATIVES, build_blind_chapter_review_schedule,
    validate_private_schedule, validate_public_reviewer_index,
    validate_schedule_projection, validate_exact_blind_chapter_review_schedule,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metrics():
    row = {"state_distance": 0.2, "before_dispersion": 0.01,
           "after_dispersion": 0.01, "dispersion_penalty": 0.02,
           "persistence_adjusted_score": 0.18}
    return {name: dict(row) for name in ("global", "spatial_luma", "rgb_histogram")}


def proposals(centers, policy_sha):
    origin = Fraction(7, 1000)
    candidates = []
    for index, center in enumerate(centers, start=1):
        source = origin + center
        candidates.append({
            "candidate_id": f"chapter-proposal-{index:02d}",
            "center_proxy_time_seconds": center,
            "center_source_time": {"numerator": source.numerator,
                                   "denominator": source.denominator},
            "support_windows": {"before_proxy_seconds_half_open": [center - 30, center - 10],
                                "after_proxy_seconds_half_open": [center + 10, center + 30],
                                "samples_per_window": 20},
            "uncertainty": {"kind": "symmetric-temporal-review-radius",
                            "radius_seconds": 10},
            "family_metrics": metrics(), "dominant_family": "global",
            "persistence_adjusted_score": 0.18,
        })
    policy = {
        "config_id": "chapter-proposals-persistent-state-v1",
        "eligible_center_count": 557, "score_median": 0.01,
        "score_mad": 0.01, "mad_zero": False, "emission_threshold": 0.08,
        "threshold_comparison": "greater-than-or-equal",
        "local_maximum_radius_seconds": 10, "local_plateau_rule": "earliest",
        "minimum_temporal_separation_seconds": 45, "maximum_candidates": 6,
        "selection_rule": "qualified-local-maxima-score-descending-with-temporal-separation",
        "dominant_family_diversity_rule": "record-only-no-quota-no-backfill-family-order-resolves-dominant-score-ties",
        "local_maxima_audit": [],
        "local_maxima_disposition_counts": {"below_threshold": 0,
                                             "minimum_separation": 0,
                                             "maximum_candidate_cap": 0,
                                             "emitted": len(centers)},
    }
    return {
        "schema_version": "aegis360.chapter-proposal-candidates.v1",
        "source_id": "skiing-fixture",
        "inputs": {"visual_state_features_sha256": "a" * 64,
                   "chapter_proposal_config_sha256": policy_sha},
        "policy": policy, "candidates": candidates,
        "privacy": {"contains_source_path": False, "contains_pixels": False,
                    "contains_audio": False, "contains_identity": False},
        "authority": {"review_candidate_emitted": bool(candidates),
                      "story_boundary": False, "candidate_selected": False,
                      "production_eligible": False, "render": False},
        "limitations": [
            "candidates are visual-state review proposals, not semantic chapter labels",
            "fixed support windows cannot propose within 30 seconds of either endpoint",
            "distribution-relative thresholding does not manufacture weak candidates"],
    }


class BlindChapterReviewScheduleTests(unittest.TestCase):
    def setUp(self):
        self.config_bytes = (ROOT / "config/blind-chapter-review-schedule-v1.json").read_bytes()
        self.config = json.loads(self.config_bytes)
        self.hashes = {"source_sha256": "1" * 64, "policy_sha256": "2" * 64,
                       "protocol_sha256": "3" * 64,
                       "config_sha256": sha(self.config_bytes)}
        self.salt = "4" * 64

    def build(self, centers=(30, 80, 130)):
        proposal = proposals(list(centers), self.hashes["policy_sha256"])
        proposal_bytes = json.dumps(proposal, sort_keys=True).encode()
        private, public = build_blind_chapter_review_schedule(
            proposals=proposal, proposals_sha256=sha(proposal_bytes),
            config=self.config, presentation_salt_hex=self.salt, **self.hashes)
        return proposal, private, public

    def exact_inputs(self, proposal):
        proposal_bytes = json.dumps(proposal, sort_keys=True).encode()
        return {"proposals": proposal, "proposals_sha256": sha(proposal_bytes),
                "config": self.config, "presentation_salt_hex": self.salt,
                **self.hashes}

    def test_controls_separation_private_mapping_and_public_blindness(self):
        _, private, public = self.build()
        controls = [row["absolute_proxy_time_seconds"] for row in private["entries"]
                    if row["private_role"] == "control"]
        proposals_at = [30, 80, 130]
        self.assertEqual(len(controls), 3)
        for index, control in enumerate(controls):
            self.assertTrue(all(abs(control - proposal) >= 45 for proposal in proposals_at))
            self.assertTrue(all(abs(control - other) >= 45 for other in controls[:index]))
            self.assertTrue(all(abs(control - negative) >= 30 for negative in HARD_NEGATIVES))
        validate_private_schedule(private)
        validate_public_reviewer_index(public)
        validate_schedule_projection(private, public)
        validate_exact_blind_chapter_review_schedule(
            private, public, **self.exact_inputs(proposals(proposals_at,
                                                           self.hashes["policy_sha256"])))
        encoded = json.dumps(public["packets"], sort_keys=True)
        for forbidden in ("absolute", "proposal", "control", "sha256", "yaw",
                          "pitch", "fov", "context:cardinal", "score", "status"):
            self.assertNotIn(forbidden, encoded.lower())
        self.assertNotIn(self.hashes["source_sha256"], encoded)
        self.assertEqual([row["row_role"] for row in public["packets"][0]["rows"]],
                         ["early_far", "early_near", "transition_before",
                          "transition_after", "late_near", "late_far"])

    def test_deterministic_salted_order_and_collision_fail_closed(self):
        _, first_private, first_public = self.build()
        _, second_private, second_public = self.build()
        self.assertEqual(first_private, second_private)
        self.assertEqual(first_public, second_public)
        self.salt = "5" * 64
        _, _, other_public = self.build()
        self.assertNotEqual(first_public["bundle_id"], other_public["bundle_id"])
        self.assertNotEqual([p["packet_id"] for p in first_public["packets"]],
                            [p["packet_id"] for p in other_public["packets"]])
        with mock.patch("aegis360.blind_chapter_review_schedule._hmac",
                        return_value="f" * 64):
            with self.assertRaisesRegex(ValueError, "collision"):
                self.build()

    def test_insufficient_controls_hash_tamper_and_public_leaks_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "three separated controls"):
            self.build((30, 120, 210, 300, 390, 480))
        proposal, _, _ = self.build()
        with self.assertRaisesRegex(ValueError, "proof hashes"):
            build_blind_chapter_review_schedule(
                proposals=proposal, proposals_sha256="bad",
                config=self.config, presentation_salt_hex=self.salt, **self.hashes)
        _, private, public = self.build()
        mutations = []
        for key, value in (("absolute_time", 120), ("source_sha256", "a" * 64),
                           ("yaw_degrees", 90), ("private_role", "proposal"),
                           ("score", 0.9), ("status", "expected")):
            changed = copy.deepcopy(public)
            changed["packets"][0][key] = value
            mutations.append(changed)
        changed = copy.deepcopy(public)
        changed["packets"][0]["rows"][0]["media_ref"] = "/private/leak.png"
        mutations.append(changed)
        changed = copy.deepcopy(public)
        changed["packets"][0]["rows"][0]["views"][0]["view_id"] = "context:cardinal:0"
        mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(ValueError):
                validate_public_reviewer_index(changed)
        changed = copy.deepcopy(public)
        changed["packets"].reverse()
        with self.assertRaises(ValueError):
            validate_schedule_projection(private, changed)

    def test_exact_rebuild_rejects_cryptographic_and_order_tamper(self):
        proposal, private, public = self.build()
        mutations = []
        changed_private = copy.deepcopy(private)
        changed_private["entries"][0]["presentation_hmac_sha256"] = "0" * 64
        mutations.append((changed_private, public))
        changed_private = copy.deepcopy(private)
        changed_public = copy.deepcopy(public)
        replacement = "packet-" + "f" * 20
        changed_private["entries"][0]["packet_id"] = replacement
        changed_public["packets"][0]["packet_id"] = replacement
        for row in changed_private["entries"][0]["rows"]:
            row["media_ref"] = row["media_ref"].replace(
                private["entries"][0]["packet_id"], replacement)
        for row in changed_public["packets"][0]["rows"]:
            row["media_ref"] = row["media_ref"].replace(
                public["packets"][0]["packet_id"], replacement)
        mutations.append((changed_private, changed_public))
        changed_public = copy.deepcopy(public)
        changed_public["bundle_id"] = "review-" + "e" * 20
        mutations.append((private, changed_public))
        changed_private = copy.deepcopy(private)
        changed_public = copy.deepcopy(public)
        changed_private["entries"][0], changed_private["entries"][1] = (
            changed_private["entries"][1], changed_private["entries"][0])
        changed_public["packets"][0], changed_public["packets"][1] = (
            changed_public["packets"][1], changed_public["packets"][0])
        for index in (0, 1):
            changed_private["entries"][index]["presentation_ordinal"] = index + 1
            changed_public["packets"][index]["presentation_ordinal"] = index + 1
        mutations.append((changed_private, changed_public))
        exact = self.exact_inputs(proposal)
        for changed_private, changed_public in mutations:
            with self.assertRaises(ValueError):
                validate_exact_blind_chapter_review_schedule(
                    changed_private, changed_public, **exact)

    def test_cli_hash_gate_atomic_two_file_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            proposal = proposals([30, 80, 130], self.hashes["policy_sha256"])
            proposal_path = root / "proposals.json"
            proposal_path.write_text(json.dumps(proposal, sort_keys=True))
            proposal_hash = sha(proposal_path.read_bytes())
            salt_file = root / "presentation.salt"
            salt_file.write_text(self.salt + "\n")
            output = root / "schedule"
            command = [sys.executable,
                       str(ROOT / "scripts/build_blind_chapter_review_schedule.py"),
                       str(proposal_path),
                       str(ROOT / "config/blind-chapter-review-schedule-v1.json"),
                       str(output), "--proposals-sha256", proposal_hash,
                       "--source-sha256", self.hashes["source_sha256"],
                       "--policy-sha256", self.hashes["policy_sha256"],
                       "--protocol-sha256", self.hashes["protocol_sha256"],
                       "--presentation-salt-file", str(salt_file)]
            self.assertNotIn("--presentation-salt-hex", command)
            self.assertNotIn(self.salt, command)
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(sorted(path.name for path in output.iterdir()),
                             ["private-schedule.json", "public-reviewer-index.json"])
            again = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            bad_output = root / "bad"
            bad = command.copy()
            bad[bad.index(str(output))] = str(bad_output)
            bad[bad.index(proposal_hash)] = "a" * 64
            failed = subprocess.run(bad, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertFalse(bad_output.exists())
            malformed_salt = root / "bad.salt"
            malformed_secret = "A" * 64
            malformed_salt.write_text(malformed_secret + "\n")
            malformed_output = root / "malformed-salt"
            malformed = command.copy()
            malformed[malformed.index(str(output))] = str(malformed_output)
            malformed[malformed.index(str(salt_file))] = str(malformed_salt)
            failed = subprocess.run(malformed, capture_output=True, text=True)
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("exactly one lowercase 64-hex line", failed.stderr)
            self.assertNotIn(malformed_secret, failed.stderr)
            self.assertFalse(malformed_output.exists())


if __name__ == "__main__":
    unittest.main()
