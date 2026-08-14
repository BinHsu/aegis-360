import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan_window_group_proposal.py"
CONFIG = ROOT / "config" / "greedy-group-context-v1.toml"


def proposal():
    return {
        "schema_version": "aegis360.window-group-proposal.v1",
        "window": {
            "source_id": "fixture", "window_id": "t0-1s",
            "start_seconds": 0.0, "duration_seconds": 1.0,
            "sample_timestamps_seconds": [0.0, 0.25, 0.5, 0.75],
        },
        "candidates": [
            {"candidate_id": "person-slot:1", "candidate_type": "person", "member_candidate_ids": []},
            {"candidate_id": "person-slot:2", "candidate_type": "person", "member_candidate_ids": []},
            {"candidate_id": "group:window:1", "candidate_type": "group", "member_candidate_ids": ["person-slot:1", "person-slot:2"]},
            {"candidate_id": "context:forward", "candidate_type": "context", "member_candidate_ids": []},
        ],
        "geometry": {
            "yaw": 0.5, "pitch": -0.2, "horizontal_fov": 1.9,
            "required_horizontal_fov": 1.2, "observed_sample_count": 2,
            "total_sample_count": 4, "observation_ratio": 0.5,
            "minimum_observed_member_count": 2,
            "maximum_observed_member_count": 2,
            "fully_contains_observed_groups": True,
            "association_provenance": "simultaneous_group_geometry_nonidentity",
        },
    }


def abstention_context(value):
    return {
        "schema_version": "aegis360.scene-context.v2",
        "window": {
            key: value["window"][key]
            for key in ("source_id", "window_id", "start_seconds", "duration_seconds")
        },
        "candidates": value["candidates"],
        "provenance": {
            "reviewer_kind": "human", "adapter_id": "fixture-human",
            "model_id": None, "model_sha256": None,
        },
        "decision": {
            "context_class": "uncertain", "subject_scope": "uncertain",
            "selected_candidate_id": None,
            "evidence_flags": {
                "multiple_people_visible": "unknown", "face_visible": "unknown",
                "mouth_motion_visible": "unknown", "reciprocal_orientation": "unknown",
                "speech_audio_present": "unknown",
            },
        },
        "privacy": {
            "contains_source_path": False, "contains_pixels": False,
            "contains_names": False, "contains_embeddings": False,
        },
        "limitations": [
            "context classification does not establish identity or active speaker"
        ],
    }


class PlanWindowGroupProposalContractTests(unittest.TestCase):
    def test_context_must_reproduce_proposal_and_plan_stays_nonidentity(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("validate_scene_context(context_document)", text)
        self.assertIn("context candidates do not reproduce the proposal", text)
        self.assertIn('"identity_verified": False', text)
        self.assertIn('"editorial_persistence_allowed": False', text)
        self.assertIn('"render_contract": "shot_static_v360_only"', text)
        self.assertIn('"deterministic_context_fallback"', text)
        self.assertIn('"review_selected_group"', text)
        self.assertNotIn("source_media", text)

    def test_abstention_plans_context_only_and_records_resolution(self):
        value = proposal()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proposal_path = root / "proposal.json"
            context_path = root / "context.json"
            output = root / "plan"
            proposal_path.write_text(json.dumps(value), encoding="utf-8")
            context_path.write_text(
                json.dumps(abstention_context(value)), encoding="utf-8",
            )
            subprocess.run(
                [sys.executable, str(SCRIPT), str(proposal_path),
                 str(context_path), str(CONFIG), str(output)],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            trace = json.loads((output / "trace.json").read_text(encoding="utf-8"))
            gate = json.loads((output / "planning-gate.json").read_text(encoding="utf-8"))

        self.assertIsNone(trace["input_contract"]["selected_candidate_id"])
        self.assertEqual(
            trace["input_contract"]["selection_resolution"],
            "deterministic_context_fallback",
        )
        self.assertEqual(
            {row["selected_candidate_id"] for row in trace["decisions"]},
            {"context:forward"},
        )
        self.assertEqual(gate["selected_candidate_counts"], {"context:forward": 4})
        self.assertFalse(gate["passed_pose_differentiation"])


if __name__ == "__main__":
    unittest.main()
