import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_runner_contract import *  # noqa: E402,F403
from tests import test_sparse_story_projection as projection_helpers  # noqa: E402


H = lambda value: value * 64


class SparseStoryRunnerContractTests(unittest.TestCase):
    def setUp(self):
        packets, hashes, index = projection_helpers.SparseStoryProjectionTests().build(1)
        self.projection = index["packets"][0]["projection"]
        self.packet_id = self.projection["packet_id"]

    def entry(self, path, mode=0o444, size=1, digest="1"):
        return {"relative_path": path, "mode": mode, "size": size, "sha256": H(digest)}

    def test_asset_manifest_exact_modes_paths_order_and_empty_support(self):
        runtime = build_asset_manifest_shape(asset_kind="runtime", entrypoint="bin/adapter",
            entries=[self.entry("bin/adapter", 0o555), self.entry("lib/model.dat", digest="2")])
        validate_asset_manifest_shape(runtime); self.assertEqual(runtime, __import__("json").loads(canonical_bytes(runtime)))
        self.assertEqual(canonical_asset_manifest_shape_bytes(runtime), canonical_bytes(runtime))
        with self.assertRaises(AuthorityUnavailable): canonical_asset_manifest_bytes(runtime)
        support = build_asset_manifest_shape(asset_kind="synthetic_support", entries=[])
        self.assertEqual(support["root_tree_sha256"], hashlib.sha256(b"").hexdigest())
        for entries in ([self.entry("../escape")],
                        [self.entry("z"), self.entry("a")],
                        [self.entry("run", 0o555)]):
            with self.assertRaises(ValueError):
                build_asset_manifest_shape(asset_kind="model", entries=entries)
        changed = copy.deepcopy(runtime); changed["entries"][0]["size"] = True
        with self.assertRaises(ValueError): validate_asset_manifest_shape(changed)

    def test_frozen_policy_and_capability_matrix(self):
        policy = build_runner_policy(backend_manifest_sha256=H("a"))
        validate_runner_policy(policy, backend_manifest_sha256=H("a"))
        self.assertEqual(policy["environment_template"], ENVIRONMENT)
        self.assertEqual((policy["timeout_ns"], policy["termination_grace_ns"]),
                         (120000000000, 2000000000))
        capability = {"schema_version": CAPABILITY_SCHEMA,
            "backend_manifest_sha256": H("a"), "compiled_policy_sha256": H("b"),
            "runner_policy_sha256": sha256(policy),
            "matrix": {key: True for key in MATRIX_KEYS}}
        validate_capability_receipt_shape(capability)
        self.assertEqual(canonical_capability_receipt_shape_bytes(capability), canonical_bytes(capability))
        with self.assertRaises(AuthorityUnavailable): canonical_capability_receipt_bytes(capability)
        with self.assertRaises(AuthorityUnavailable):
            derive_capability_receipt(matrix={key: True for key in MATRIX_KEYS})
        with self.assertRaises(AuthorityUnavailable): validate_capability_receipt(capability)
        bad = dict(capability["matrix"]); bad["denied_ipv4"] = False
        changed = copy.deepcopy(capability); changed["matrix"] = bad
        with self.assertRaises(ValueError): validate_capability_receipt_shape(changed)

    def test_request_exact_six_projection_order_and_handles(self):
        prompt = build_asset_manifest_shape(asset_kind="prompt_schema", entries=[
            self.entry("prompt.txt"), self.entry("raw-observation-schema.json", digest="2")])
        model = build_asset_manifest_shape(asset_kind="model", entries=[self.entry("weights.bin")])
        request = build_adapter_request_shape(packet_id=self.packet_id,
            projection=self.projection, prompt_schema_manifest=prompt,
            prompt_schema_root_path="/private/tmp/prompt", model_manifest=model,
            model_root_path="/private/tmp/model")
        validate_adapter_request_shape(request)
        self.assertEqual(canonical_adapter_request_shape_bytes(request), canonical_bytes(request))
        with self.assertRaises(AuthorityUnavailable): canonical_adapter_request_bytes(request)
        self.assertEqual([row["path"] for row in request["media"]],
                         [row["media_ref"] for row in self.projection["rows"]])
        changed = copy.deepcopy(self.projection); changed["rows"] = changed["rows"][:-1]
        with self.assertRaises(ValueError): build_adapter_request_shape(packet_id=self.packet_id,
            projection=changed, prompt_schema_manifest=prompt,
            prompt_schema_root_path="/p", model_manifest=model, model_root_path="/m")
        changed = copy.deepcopy(request); changed["projection"]["rows"][0]["row_number"] = True
        with self.assertRaises(ValueError): validate_adapter_request_shape(changed)

    def test_run_receipt_hashes_exact_stdout_and_closed_authority(self):
        receipt = {"schema_version": RECEIPT_SCHEMA, "packet_id": self.packet_id,
            "inputs": {key: H(str(number)) for number, key in enumerate((
                "adapter_projection_sha256", "sanitized_media_result_sha256",
                "runtime_manifest_sha256", "model_manifest_sha256",
                "prompt_schema_manifest_sha256", "runner_policy_sha256"), 1)},
            "execution": {"invocation_count": 1, "stdout_present": True,
                "stdout_sha256": hashlib.sha256(b"\xff\0").hexdigest(),
                "invocation_failed": False}, "privacy": dict(PRIVACY),
            "authority": dict(RECEIPT_AUTHORITY)}
        validate_run_receipt_shape(receipt)
        self.assertEqual(canonical_run_receipt_shape_bytes(receipt), canonical_bytes(receipt))
        with self.assertRaises(AuthorityUnavailable): canonical_run_receipt_bytes(receipt)
        self.assertEqual(set(receipt["inputs"]), {"adapter_projection_sha256",
            "sanitized_media_result_sha256", "runtime_manifest_sha256",
            "model_manifest_sha256", "prompt_schema_manifest_sha256", "runner_policy_sha256"})
        changed = copy.deepcopy(receipt); changed["execution"]["invocation_count"] = 0
        with self.assertRaises(ValueError): validate_run_receipt_shape(changed)
        with self.assertRaises(AuthorityUnavailable):
            derive_run_receipt(invocation_failed=False, hashes=receipt["inputs"])
        with self.assertRaises(AuthorityUnavailable): validate_run_receipt(receipt)

    def cases(self):
        return [{"case_id": case_id, "expected_result": expected,
                 "stimulus": {"argv": ["$HOME;echo", "$(id)"],
                    "stdin_sha256": H("a"), "support_manifest_sha256": H("b")}}
                for case_id, expected in CASE_SPECS]

    def test_case_manifest_result_order_and_repeatability(self):
        manifest = build_case_manifest(synthetic_adapter_manifest_sha256=H("7"),
            cases=self.cases(), repeat_packet_id=self.packet_id)
        validate_case_manifest(manifest, synthetic_adapter_manifest_sha256=H("7"),
            cases=self.cases(), repeat_packet_id=self.packet_id)
        observed = [expected for _, expected in CASE_SPECS]
        result = {"schema_version": CASE_RESULT_SCHEMA,
            "case_manifest_sha256": sha256(manifest),
            "cases": [{"case_id": row["case_id"], "expected_result": row["expected_result"],
                "observed_result": value, "passed": value == row["expected_result"]}
                for row, value in zip(manifest["cases"], observed)],
            "repeatability": {"packet_id": self.packet_id,
                "first_stdout_sha256": H("8"), "second_stdout_sha256": H("8"),
                "equal": True}}
        validate_case_result_shape(result, case_manifest=manifest)
        self.assertEqual(canonical_case_result_shape_bytes(result, case_manifest=manifest),
                         canonical_bytes(result))
        with self.assertRaises(AuthorityUnavailable):
            canonical_case_result_bytes(result, case_manifest=manifest)
        self.assertTrue(all(row["passed"] for row in result["cases"]))
        with self.assertRaises(AuthorityUnavailable):
            derive_case_result(observed_results=observed)
        with self.assertRaises(AuthorityUnavailable):
            validate_case_result(result, case_manifest=manifest)
        with self.assertRaises(AuthorityUnavailable):
            derive_synthetic_run_result(case_manifest=manifest,
                case_result=result, trust_valid=True)
        changed = self.cases(); changed[0], changed[1] = changed[1], changed[0]
        with self.assertRaises(ValueError): build_case_manifest(
            synthetic_adapter_manifest_sha256=H("7"), cases=changed,
            repeat_packet_id=self.packet_id)

    def aggregate_shape(self, packet_rows, outcome="pass"):
        return {"schema_version": RUN_RESULT_SCHEMA, "run_kind": "synthetic_gate",
            "inputs": {"schedule_sha256": H("1"), "backend_manifest_sha256": H("2"),
                "runner_policy_sha256": H("3"), "compiled_policy_sha256": H("4"),
                "capability_receipt_sha256": H("5"),
                "synthetic_adapter_manifest_sha256": H("6"),
                "synthetic_case_manifest_sha256": H("7"),
                "synthetic_case_result_sha256": H("8"), "failure_stage": "none"},
            "packets": packet_rows, "runner_outcome": outcome,
            "privacy": dict(PRIVACY), "authority": dict(RESULT_AUTHORITY)}

    def test_aggregate_exact_rows_precedence_and_validation(self):
        rows = [{"packet_id": self.packet_id, "invocation_count": 1,
                 "receipt_sha256": H("9"), "evidence_sha256": H("a")}]
        aggregate = self.aggregate_shape(rows)
        validate_run_result_shape(aggregate)
        self.assertEqual(canonical_run_result_shape_bytes(aggregate), canonical_bytes(aggregate))
        with self.assertRaises(AuthorityUnavailable): canonical_run_result_bytes(aggregate)
        for function in (build_run_result, validate_run_result,
                         derive_run_result, derive_runner_outcome):
            with self.assertRaises(AuthorityUnavailable):
                function(trust_valid=True, runner_outcome="pass",
                         packets=rows, hashes=aggregate["inputs"])
        bad = copy.deepcopy(rows); bad[0]["evidence_sha256"] = None
        with self.assertRaises(ValueError): validate_run_result_shape(self.aggregate_shape(bad))
        zero = [{"packet_id": self.packet_id, "invocation_count": 0,
                 "receipt_sha256": None, "evidence_sha256": None}]
        early = self.aggregate_shape(zero, "invalid")
        early["inputs"].update(compiled_policy_sha256=None,
            capability_receipt_sha256=None, synthetic_adapter_manifest_sha256=None,
            synthetic_case_manifest_sha256=None, synthetic_case_result_sha256=None,
            failure_stage="preflight")
        validate_run_result_shape(early)


if __name__ == "__main__": unittest.main()
