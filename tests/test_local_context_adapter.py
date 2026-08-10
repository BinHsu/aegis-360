from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.local_context_adapter import build_local_context_document


def proposal():
    return {
        "schema_version": "aegis360.window-group-proposal.v1",
        "window": {"source_id": "fixture", "window_id": "w1", "start_seconds": 0, "duration_seconds": 1},
        "candidates": [
            {"candidate_id": "person-slot:1", "candidate_type": "person", "member_candidate_ids": []},
            {"candidate_id": "person-slot:2", "candidate_type": "person", "member_candidate_ids": []},
            {"candidate_id": "group:window:1", "candidate_type": "group", "member_candidate_ids": ["person-slot:1", "person-slot:2"]},
            {"candidate_id": "forward:context", "candidate_type": "context", "member_candidate_ids": []},
        ],
    }


def decision(**updates):
    value = {
        "context_class": "conversation", "subject_scope": "group",
        "selected_candidate_id": "group:window:1",
        "evidence_flags": {
            "multiple_people_visible": "present", "face_visible": "present",
            "mouth_motion_visible": "unknown", "reciprocal_orientation": "unknown",
            "speech_audio_present": "unknown",
        },
    }
    value.update(updates)
    return value


class LocalContextAdapterTests(unittest.TestCase):
    def test_binds_model_checksum_and_geometry_owned_selection(self):
        result = build_local_context_document(
            proposal(), decision(), adapter_id="fixture-adapter",
            model_id="fixture-model", model_sha256="a" * 64,
        )
        self.assertEqual(result["provenance"]["reviewer_kind"], "local_vlm")
        self.assertEqual(result["decision"]["selected_candidate_id"], "group:window:1")
        self.assertEqual(result["candidates"], proposal()["candidates"])

    def test_uncertain_is_allowed_without_selection(self):
        result = build_local_context_document(
            proposal(), decision(context_class="uncertain", subject_scope="uncertain", selected_candidate_id=None),
            adapter_id="fixture-adapter", model_id="fixture-model", model_sha256="b" * 64,
        )
        self.assertIsNone(result["decision"]["selected_candidate_id"])

    def test_free_text_geometry_and_unknown_candidate_fail_closed(self):
        for invalid in (
            dict(decision(), explanation="people talking"),
            dict(decision(), yaw_degrees=54),
            decision(selected_candidate_id="invented"),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    build_local_context_document(
                        proposal(), invalid, adapter_id="fixture-adapter",
                        model_id="fixture-model", model_sha256="c" * 64,
                    )

    def test_cli_verifies_asset_and_refuses_overwrite(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            proposal_path = work / "proposal.json"
            decision_path = work / "decision.json"
            model_path = work / "model.bin"
            output_path = work / "context.json"
            proposal_path.write_text(json.dumps(proposal()), encoding="utf-8")
            decision_path.write_text(json.dumps(decision()), encoding="utf-8")
            model_path.write_bytes(b"offline fixture model")
            checksum = hashlib.sha256(model_path.read_bytes()).hexdigest()
            command = [
                sys.executable, str(root / "scripts/import_local_vlm_scene_context.py"),
                str(proposal_path), str(decision_path), str(model_path), str(output_path),
                "--adapter-id", "fixture-adapter", "--model-id", "fixture-model",
                "--expected-model-sha256", checksum,
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertFalse(json.loads(output_path.read_text())["privacy"]["contains_source_path"])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    unittest.main()
