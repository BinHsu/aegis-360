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
from aegis360.structural_blind_schedule import (  # noqa: E402
    CONFIG_SHA256, PROOF_SHA256, build_structural_blind_schedule,
    validate_exact_schedule, validate_projection, validate_public_index,
    validate_schedule_config,
)


class StructuralBlindScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config_bytes = (ROOT / "config/structural-chapter-blind-schedule-v1.json").read_bytes()
        cls.config = json.loads(cls.config_bytes)
        cls.salt = "4" * 64

    def proof(self):
        universe = []; selected = []
        for i in range(26):
            time = Fraction(20 + i * 7, 3)
            base = {"event_id": f"event:multi:{i:04d}",
                    "signal_id": f"event:scene-change:{i:04d}",
                    "source_time": {"numerator": time.numerator,
                                    "denominator": time.denominator},
                    "packet_sha256": hashlib.sha256(f"packet-{i}".encode()).hexdigest(),
                    "selection_digest": hashlib.sha256(f"selection-{i}".encode()).hexdigest()}
            row = dict(base)
            if i < 8:
                row.update(disposition="selected", selection_rank=i + 1)
                selected.append({"selection_rank": i + 1, **base})
            else:
                row["disposition"] = "after_cap"
            universe.append(row)
        return {"schema_version": "aegis360.structural-chapter-blind-selection-proof.v1",
            "source_id": "old_ghost_road_360",
            "inputs": {"config_sha256": "c4a1f411e26de8061c46f49e7db43474b4aeb75839d7d7f140cc38bd5df2e6cb",
                       "timeline_sha256": "f" * 64,
                       "context_view_grid_sha256": "e" * 64},
            "selection_policy": {"universe_count": 26, "packet_cap": 8,
                                 "minimum_separation_seconds": 8,
                                 "development_exclusion_seconds": 8,
                                 "development_exclusion_comparison": "strictly-less-than"},
            "universe": universe, "selected": selected,
            "authority": {"semantic_label": False, "story_boundary": False,
                          "camera_choice": False, "render": False},
            "privacy": {"contains_source_path": False, "contains_pixels": False,
                        "contains_audio": False, "contains_labels": False},
            "limitations": []}

    def inputs(self):
        return dict(selection_proof=self.proof(),
                    selection_proof_sha256=PROOF_SHA256, config=self.config,
                    config_sha256=CONFIG_SHA256,
                    presentation_salt_hex=self.salt)

    def test_closed_config_private_mapping_and_public_projection(self):
        validate_schedule_config(self.config)
        private, public = build_structural_blind_schedule(**self.inputs())
        self.assertEqual(len(private["entries"]), 8)
        self.assertEqual(len(public["packets"]), 8)
        self.assertEqual([row["row_role"] for row in public["packets"][0]["rows"]],
                         self.config["public_projection"]["row_roles"])
        first = private["entries"][0]
        center = Fraction(first["absolute_center_time"]["numerator"],
                          first["absolute_center_time"]["denominator"])
        offset = Fraction(first["rows"][0]["relative_offset_seconds"]["numerator"],
                          first["rows"][0]["relative_offset_seconds"]["denominator"])
        absolute = Fraction(first["rows"][0]["absolute_source_time"]["numerator"],
                            first["rows"][0]["absolute_source_time"]["denominator"])
        self.assertEqual(center + offset, absolute)
        validate_projection(private, public)
        validate_exact_schedule(private, public, **self.inputs())
        encoded = json.dumps(public, sort_keys=True)
        for forbidden in self.config["public_projection"]["forbidden_fields"]:
            self.assertNotIn(f'"{forbidden}"', encoded)

    def test_salt_changes_order_ids_and_collision_fails(self):
        first = build_structural_blind_schedule(**self.inputs())
        second_inputs = self.inputs(); second_inputs["presentation_salt_hex"] = "5" * 64
        second = build_structural_blind_schedule(**second_inputs)
        self.assertNotEqual(first[1]["bundle_id"], second[1]["bundle_id"])
        self.assertNotEqual([x["packet_id"] for x in first[1]["packets"]],
                            [x["packet_id"] for x in second[1]["packets"]])
        with mock.patch("aegis360.structural_blind_schedule._mac", return_value="a" * 64):
            with self.assertRaisesRegex(ValueError, "collision"):
                build_structural_blind_schedule(**self.inputs())

    def test_proof_and_public_tamper_fail_exactly(self):
        inputs = self.inputs(); private, public = build_structural_blind_schedule(**inputs)
        bad_proof = copy.deepcopy(inputs["selection_proof"])
        bad_proof["selected"][0]["source_time"]["denominator"] *= 2
        with self.assertRaises(ValueError):
            build_structural_blind_schedule(**{**inputs, "selection_proof": bad_proof})
        leaked = copy.deepcopy(public); leaked["packets"][0]["event_id"] = "event:multi:0000"
        with self.assertRaises(ValueError): validate_public_index(leaked, self.config)
        reordered = copy.deepcopy(public); reordered["packets"].reverse()
        with self.assertRaises(ValueError): validate_projection(private, reordered)
        changed = copy.deepcopy(private); changed["entries"][0]["order_hmac_sha256"] = "0" * 64
        with self.assertRaises(ValueError): validate_exact_schedule(changed, public, **inputs)

    def test_config_tamper_and_cli_path_redaction_no_stage(self):
        bad = copy.deepcopy(self.config); bad["render"]["panel_width"] = 481
        with self.assertRaises(ValueError): validate_schedule_config(bad)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); secret = root / "secret-name"
            secret.write_text("{}")
            output = root / "schedule"
            command = [sys.executable, str(ROOT / "scripts/build_structural_blind_schedule.py"),
                       str(secret), str(secret), str(output),
                       "--presentation-salt-file", str(secret)]
            result = subprocess.run(command, capture_output=True, text=True,
                                    env=dict(os.environ))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(str(root), result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".schedule.*")), [])


if __name__ == "__main__": unittest.main()
