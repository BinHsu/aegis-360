import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_semantics import (  # noqa: E402
    ABSTENTION, bind_failure_abstention, bind_observation,
    build_operational_failure, derive_event_class, select_failure_reason,
    canonical_failure_bytes,
    validate_bound_observation, validate_operational_failure,
    validate_failure_bound_observation, validate_failure_shape,
    validate_raw_observation,
)


class SparseStorySemanticTests(unittest.TestCase):
    def setUp(self):
        self.hashes = dict(private_packet_sha256="1" * 64,
            adapter_projection_sha256="2" * 64, model_asset_sha256="3" * 64,
            prompt_schema_bundle_sha256="4" * 64)
        self.base = {"status": "observed", "early_state_coherence": "observed",
            "late_state_coherence": "observed", "activity_relation": "same",
            "setting_relation": "same", "anonymous_participant_configuration": "same",
            "transition_support": "supports", "viewpoint_change": "absent",
            "foreground_rearrangement": "absent", "exposure_or_palette_change": "absent",
            "capture_or_projection_artifact": "absent"}
        self.packet = "packet-" + "a" * 20

    def raw(self, value):
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    def test_ordered_truth_table_and_raw_preservation(self):
        artifact = copy.deepcopy(self.base); artifact["capture_or_projection_artifact"] = "present"; artifact["activity_relation"] = "changed"
        self.assertEqual(derive_event_class(artifact), "capture_artifact")
        story = copy.deepcopy(self.base); story["setting_relation"] = "changed"
        self.assertEqual(derive_event_class(story), "story_change")
        nuisance = copy.deepcopy(self.base); nuisance["anonymous_participant_configuration"] = "changed"; nuisance["viewpoint_change"] = "present"
        self.assertEqual(derive_event_class(nuisance), "no_semantic_change")
        participant = copy.deepcopy(self.base); participant["anonymous_participant_configuration"] = "changed"
        self.assertEqual(derive_event_class(participant), "abstain")
        bound = bind_observation(packet_id=self.packet, raw_output=self.raw(story), **self.hashes)
        self.assertEqual(bound["raw_observation"], story); self.assertEqual(bound["event_class"], "story_change")
        validate_bound_observation(bound, packet_id=self.packet, raw_output=self.raw(story), **self.hashes)

    def test_closed_raw_schema_and_canonical_abstention(self):
        validate_raw_observation(self.base); validate_raw_observation(ABSTENTION)
        for mutation in (lambda d: d.update(confidence=0.9), lambda d: d.pop("activity_relation"), lambda d: d.__setitem__("activity_relation", "maybe")):
            changed = copy.deepcopy(self.base); mutation(changed)
            with self.assertRaises(ValueError): validate_raw_observation(changed)
        bad = dict(ABSTENTION); bad["activity_relation"] = "same"
        with self.assertRaisesRegex(ValueError, "canonical"): validate_raw_observation(bad)
        ordinary_abstain = bind_observation(
            packet_id=self.packet, raw_output=self.raw(ABSTENTION), **self.hashes)
        self.assertIsNone(ordinary_abstain["inputs"]["operational_failure_sha256"])
        self.assertEqual(ordinary_abstain["event_class"], "abstain")

    def test_failure_reason_precedence_hash_and_failure_binding(self):
        forbidden = {**self.base, "confidence": 1}
        self.assertEqual(select_failure_reason(missing_anchor=True, invocation_failed=True, raw_output=b"bad"), "missing_anchor")
        self.assertEqual(select_failure_reason(missing_anchor=False, invocation_failed=True, raw_output=b"bad"), "invocation_failure")
        self.assertEqual(select_failure_reason(missing_anchor=False, invocation_failed=False, raw_output=b"{"), "malformed_json")
        self.assertEqual(select_failure_reason(missing_anchor=False, invocation_failed=False, raw_output=b"null"), "schema_violation")
        self.assertEqual(select_failure_reason(missing_anchor=False, invocation_failed=False, raw_output=self.raw(forbidden)), "forbidden_field")
        self.assertEqual(select_failure_reason(missing_anchor=False, invocation_failed=False, raw_output=b"{}"), "schema_violation")
        failure_inputs = dict(packet_id=self.packet, raw_output=b"", missing_anchor=True, invocation_failed=False, **self.hashes)
        failure = build_operational_failure(**failure_inputs)
        self.assertFalse(failure["raw_output_present"]); self.assertEqual(failure["raw_output_sha256"], hashlib.sha256(b"").hexdigest())
        validate_operational_failure(failure, **failure_inputs)
        failure_sha = hashlib.sha256(canonical_failure_bytes(failure)).hexdigest()
        evidence = bind_failure_abstention(failure=failure, raw_output=b"",
            missing_anchor=True, invocation_failed=False)
        self.assertEqual(evidence["raw_observation"], ABSTENTION); self.assertEqual(evidence["event_class"], "abstain")
        self.assertEqual(evidence["inputs"]["operational_failure_sha256"], failure_sha)
        validate_failure_bound_observation(evidence, failure=failure,
            raw_output=b"", missing_anchor=True, invocation_failed=False)
        self.assertNotIn("offending", json.dumps(failure)); self.assertNotIn("stderr", set(failure))
        tampered = copy.deepcopy(failure); tampered["reason"] = "schema_violation"
        with self.assertRaises(ValueError):
            bind_failure_abstention(failure=tampered, raw_output=b"",
                missing_anchor=True, invocation_failed=False)
        with self.assertRaises(ValueError):
            bind_failure_abstention(failure=failure, raw_output=b"null",
                missing_anchor=False, invocation_failed=False)
        impossible = copy.deepcopy(failure)
        impossible["raw_output_present"] = True
        with self.assertRaises(ValueError): validate_failure_shape(impossible)

    def test_success_does_not_create_failure_and_hash_tamper_fails(self):
        self.assertIsNone(select_failure_reason(missing_anchor=False, invocation_failed=False, raw_output=self.raw(self.base)))
        with self.assertRaisesRegex(ValueError, "successful"):
            build_operational_failure(packet_id=self.packet, raw_output=self.raw(self.base), missing_anchor=False, invocation_failed=False, **self.hashes)
        with self.assertRaises(ValueError):
            bind_observation(packet_id=self.packet, raw_output=b"NaN", **self.hashes)

    def test_strict_stdout_json_packet_and_authority(self):
        for raw in (b"\xff", b'{"status":"observed","status":"abstain"}',
                    b"NaN", b"Infinity", b"null", b"[]"):
            with self.assertRaises(ValueError):
                bind_observation(packet_id=self.packet, raw_output=raw, **self.hashes)
        with self.assertRaises(ValueError):
            bind_observation(packet_id="packet-01", raw_output=self.raw(self.base),
                             **self.hashes)
        bound = bind_observation(packet_id=self.packet, raw_output=self.raw(self.base),
                                 **self.hashes)
        changed = copy.deepcopy(bound); changed["authority"]["render"] = True
        with self.assertRaises(ValueError):
            validate_bound_observation(changed, packet_id=self.packet,
                raw_output=self.raw(self.base), **self.hashes)
        changed = copy.deepcopy(bound); changed["privacy"]["contains_source_id"] = True
        with self.assertRaises(ValueError):
            validate_bound_observation(changed, packet_id=self.packet,
                raw_output=self.raw(self.base), **self.hashes)

    def test_truth_table_story_nuisances_and_transition_variants(self):
        story = copy.deepcopy(self.base); story["activity_relation"] = "changed"
        for field in ("viewpoint_change", "foreground_rearrangement",
                      "exposure_or_palette_change", "capture_or_projection_artifact"):
            for value in ("present", "unclear"):
                case = copy.deepcopy(story); case[field] = value
                expected = "capture_artifact" if (field == "capture_or_projection_artifact"
                                                   and value == "present") else "abstain"
                self.assertEqual(derive_event_class(case), expected, (field, value))
        for transition in ("insufficient", "contradicts"):
            case = copy.deepcopy(story); case["transition_support"] = transition
            self.assertEqual(derive_event_class(case), "abstain")

    def test_truth_table_no_change_participant_viewpoint_foreground_matrix(self):
        for participant in ("same", "changed", "unclear"):
            for viewpoint in ("present", "absent", "unclear"):
                for foreground in ("present", "absent", "unclear"):
                    case = copy.deepcopy(self.base)
                    case["anonymous_participant_configuration"] = participant
                    case["viewpoint_change"] = viewpoint
                    case["foreground_rearrangement"] = foreground
                    expected = ("no_semantic_change" if participant == "same"
                        or (participant == "changed"
                            and "present" in (viewpoint, foreground)) else "abstain")
                    self.assertEqual(derive_event_class(case), expected,
                                     (participant, viewpoint, foreground))

    def test_malicious_types_are_value_errors_and_public_bind_cannot_take_failure(self):
        bad = copy.deepcopy(self.base); bad["activity_relation"] = []
        with self.assertRaises(ValueError): validate_raw_observation(bad)
        with self.assertRaises(ValueError):
            select_failure_reason(missing_anchor=False, invocation_failed=False,
                raw_output="not-bytes")
        failure = build_operational_failure(packet_id=self.packet, raw_output=b"",
            missing_anchor=True, invocation_failed=False, **self.hashes)
        failure["inputs"]["model_asset_sha256"] = 7
        with self.assertRaises(ValueError):
            bind_failure_abstention(failure=failure, raw_output=b"",
                missing_anchor=True, invocation_failed=False)
        with self.assertRaises(TypeError):
            bind_observation(packet_id=self.packet, raw_output=self.raw(ABSTENTION),
                operational_failure_sha256="6" * 64,
                **self.hashes)


if __name__ == "__main__": unittest.main()
