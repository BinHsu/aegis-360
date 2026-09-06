import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import aegis360.structural_blind_coordinator as coordinator  # noqa: E402
import aegis360.structural_blind_review as review_module  # noqa: E402
from aegis360.structural_blind_renderer import canonical_bundle_tree_sha256  # noqa: E402
from aegis360.structural_blind_review import build_structural_blind_review  # noqa: E402


def dump(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")


def observation(packet, kind):
    if kind == "story_change":
        fields = ("observed", "observed", "persistent", "supports", "absent")
    else:
        fields = ("observed", "observed", "not_persistent", "supports", "absent")
    return dict(zip(("early_persistence", "late_persistence", "persistent_difference",
                     "transition_support", "artifact_evidence"), fields),
                packet_id=packet, classification=kind)


class StructuralBlindCoordinatorTests(unittest.TestCase):
    def fixture(self, root):
        root.mkdir(parents=True, exist_ok=True)
        config_path = root / "config.json"
        config_path.write_bytes((ROOT / "config/structural-chapter-blind-schedule-v1.json").read_bytes())
        proof = {"synthetic": True}; proof_path = root / "proof.json"; dump(proof_path, proof)
        proof_sha = hashlib.sha256(proof_path.read_bytes()).hexdigest()
        packets = [f"packet-{index:020x}" for index in range(1, 9)]
        entries = [{"packet_id": packet, "selection_rank": index,
                    "event_id": f"event:multi:{index:04d}",
                    "signal_id": f"event:scene-change:{index:04d}"}
                   for index, packet in enumerate(packets, 1)]
        private = {"entries": entries}; private_path = root / "private.json"; dump(private_path, private)
        public = {"packets": [{"packet_id": packet,
                  "rows": [{"media_ref": f"media/{packet}/row-{row:02d}.png"}
                           for row in range(1, 7)]} for packet in packets]}
        public_path = root / "public.json"; dump(public_path, public)
        bundle = root / "bundle"; bundle.mkdir()
        (bundle / "public-reviewer-index.json").write_bytes(public_path.read_bytes())
        for packet in public["packets"]:
            for row in packet["rows"]:
                path = bundle / row["media_ref"]; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(row["media_ref"].encode())
        tree_sha = canonical_bundle_tree_sha256(bundle, public)
        public_sha = hashlib.sha256(public_path.read_bytes()).hexdigest()
        classes = ["story_change"] * 3 + ["no_semantic_change"] * 5
        responses = [observation(packet, kind) for packet, kind in zip(packets, classes)]
        reviews = []
        for number in (1, 2):
            artifact = build_structural_blind_review(public_packet_ids=packets,
                public_index_sha256=public_sha, bundle_tree_sha256=tree_sha,
                schedule_config_sha256=coordinator.CONFIG_SHA256,
                reviewer_slot_id=f"reviewer-{number:020x}", responses=responses)
            path = root / f"review-{number}.json"; dump(path, artifact); reviews.append(path)
        scores = {"schema_version": coordinator.SCORE_SCHEMA,
            "inputs": {"score_contract_sha256": coordinator.SCORE_CONTRACT_SHA256,
                       "selection_proof_sha256": proof_sha},
            "scores": [{"selection_rank": row["selection_rank"],
                        "event_id": row["event_id"], "signal_id": row["signal_id"],
                        "score": 1 - index / 10} for index, row in enumerate(entries, 1)],
            "privacy": {"contains_semantic_label": False, "contains_expected_class": False,
                        "contains_source_path": False},
            "authority": {"structural_score": True, "semantic_boundary": False,
                          "camera": False, "render": False}}
        score_path = root / "scores.json"; dump(score_path, scores)
        attestation = {"schema_version": coordinator.ATTESTATION_SCHEMA,
            "reviewer_slot_ids": [f"reviewer-{1:020x}", f"reviewer-{2:020x}"],
            "distinct_principals": True, "privacy": {"contains_principal_identity": False},
            "authority": {"reviewer_separation": True, "semantic_boundary": False,
                          "camera": False, "render": False}}
        attestation_path = root / "attestation.json"; dump(attestation_path, attestation)
        salt_path = root / "salt"; salt_path.write_text("4" * 64 + "\n"); salt_path.chmod(0o600)
        paths = dict(config_path=config_path, proof_path=proof_path,
            private_schedule_path=private_path, public_index_path=public_path,
            bundle_directory=bundle, salt_path=salt_path, review_a_path=reviews[0],
            review_b_path=reviews[1], score_path=score_path, attestation_path=attestation_path)
        return paths, proof_sha

    def evaluate(self, paths, proof_sha):
        with mock.patch.object(coordinator, "PROOF_SHA256", proof_sha), \
             mock.patch.object(review_module, "SELECTION_PROOF_SHA256", proof_sha), \
             mock.patch.object(coordinator, "validate_exact_schedule"):
            return coordinator.coordinate_structural_blind_evaluation(**paths)

    def test_raw_hash_join_attestation_and_atomic_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths, proof_sha = self.fixture(Path(temporary))
            result = self.evaluate(paths, proof_sha)
            self.assertEqual(result["evaluation"]["gate"]["outcome"], "replicated")
            self.assertEqual(result["evaluation"]["inputs"]["review_a_sha256"],
                             hashlib.sha256(paths["review_a_path"].read_bytes()).hexdigest())
            output = Path(temporary) / "result.json"
            coordinator.write_json_no_overwrite(output, result)
            original = output.read_bytes()
            with self.assertRaises(ValueError):
                coordinator.write_json_no_overwrite(output, result)
            self.assertEqual(output.read_bytes(), original)

    def test_tamper_leak_bundle_and_strict_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); paths, proof_sha = self.fixture(root)
            bad = json.loads(paths["attestation_path"].read_text())
            bad["principal_name"] = "public identity"
            dump(paths["attestation_path"], bad)
            with self.assertRaisesRegex(ValueError, "attestation"):
                self.evaluate(paths, proof_sha)
            paths, proof_sha = self.fixture(root / "second")
            (paths["bundle_directory"] / "public-reviewer-index.json").write_text("{}\n")
            with self.assertRaisesRegex(ValueError, "differs"):
                self.evaluate(paths, proof_sha)
            paths, proof_sha = self.fixture(root / "third")
            paths["score_path"].write_text('{"x":1,"x":2}\n')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                self.evaluate(paths, proof_sha)

    def test_cli_errors_are_path_free_and_publish_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); secret = root / "secret-input.json"
            secret.write_text("{}\n")
            salt = root / "salt"; salt.write_text("4" * 64 + "\n"); salt.chmod(0o600)
            output = root / "result.json"
            command = [sys.executable,
                str(ROOT / "scripts/evaluate_structural_blind_reviews.py"),
                str(secret), str(secret), str(secret), str(secret), str(root), str(salt),
                str(secret), str(secret), str(secret), str(secret), str(output)]
            result = subprocess.run(command, capture_output=True, text=True,
                                    env=dict(os.environ))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(str(root), result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".result.json.*")), [])


if __name__ == "__main__":
    unittest.main()
