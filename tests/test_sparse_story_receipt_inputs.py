"""Private input lineage checks; deliberately no run receipt."""

import dataclasses
import hashlib
import json
import unittest
from unittest import mock

from tests import test_sparse_story_batch_policy as batch_helpers
from aegis360.sparse_story_projection import canonical_projection_bytes
from aegis360.sparse_story_receipt_inputs import _derive_private_receipt_inputs


class ReceiptInputLineageTests(unittest.TestCase):
    def setUp(self):
        self.fixture = batch_helpers.BatchPolicyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.candidate = self.fixture.candidate()
        live_patch = mock.patch("aegis360.sparse_story_receipt_inputs._require_live",
                                return_value=self.fixture.live)
        live_patch.start()
        self.addCleanup(live_patch.stop)

    def test_six_hashes_derive_from_validated_live_inputs(self):
        result = _derive_private_receipt_inputs(self.candidate)
        self.assertEqual(set(dataclasses.asdict(result)), {
            "adapter_projection_sha256", "sanitized_media_result_sha256",
            "runtime_manifest_sha256", "model_manifest_sha256",
            "prompt_schema_manifest_sha256", "runner_policy_sha256"})
        request = json.loads(self.candidate._request_bytes)
        self.assertEqual(result.adapter_projection_sha256, hashlib.sha256(
            canonical_projection_bytes(request["projection"])).hexdigest())
        self.assertEqual(result.sanitized_media_result_sha256, hashlib.sha256(
            self.fixture.args["media_result_bytes"]).hexdigest())
        self.assertEqual(result.runtime_manifest_sha256,
            self.fixture.live._adapter_binding._runtime.backend_identity()[2])
        self.assertEqual(result.model_manifest_sha256,
            self.candidate._proofs[1].backend_identity()[2])
        self.assertEqual(result.prompt_schema_manifest_sha256,
            self.candidate._proofs[2].backend_identity()[2])
        self.assertEqual(result.runner_policy_sha256, hashlib.sha256(
            self.candidate._runner_policy_bytes).hexdigest())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.runner_policy_sha256 = "0" * 64

    def test_changed_selected_leaf_request_policy_or_root_rejects(self):
        other = self.fixture.candidate()
        other._request_bytes += b" "
        with self.assertRaisesRegex(ValueError, "receipt input"):
            _derive_private_receipt_inputs(other)

        third = self.fixture.candidate()
        third._runner_policy_bytes += b" "
        with self.assertRaisesRegex(ValueError, "receipt input"):
            _derive_private_receipt_inputs(third)

        fourth = self.fixture.candidate()
        fourth._media_result_sha256 = "0" * 64
        with self.assertRaisesRegex(ValueError, "receipt input"):
            _derive_private_receipt_inputs(fourth)

        self.assertEqual(len(_derive_private_receipt_inputs(self.candidate).
                             sanitized_media_result_sha256), 64)
        leaf = next((self.fixture.args["bundle_root"] / "media").glob("*/*.png"))
        leaf.chmod(0o644)
        leaf.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            _derive_private_receipt_inputs(self.candidate)

    def test_named_root_replacement_rejects(self):
        root = self.fixture.args["model_root"]
        root.rename(self.fixture.base / "old-model")
        root.mkdir(mode=0o555)
        with self.assertRaises(ValueError):
            _derive_private_receipt_inputs(self.candidate)


if __name__ == "__main__":
    unittest.main()
