"""Private pre-spawn bundle mutation evidence; no case result or aggregate."""

import hashlib
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from tests import test_sparse_story_media_tree as media_helpers
from tests import test_sparse_story_batch_policy as batch_helpers
from tests.test_sparse_story_media_tree import local_rename
from aegis360.sparse_story_coordinator_mutation import (
    _EMPTY_SUPPORT_SHA, _publish_owned_selected_bundle_for_mutation,
)
from aegis360.sparse_story_media_tree import publish_sanitized_bundle


class BundleMutationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = batch_helpers.BatchPolicyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        helper = media_helpers.SparseStoryMediaTreeTests()
        packets, hashes, index = media_helpers.projection_helpers.SparseStoryProjectionTests().build(6)
        payloads = helper.payloads(index)
        full = self.fixture.base / "full-bundle"
        selected = self.fixture.base / "selected-bundle"
        result_path = self.fixture.base / "selected-result.json"
        with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive",
                        side_effect=local_rename):
            full_result = publish_sanitized_bundle(index=index,
                private_packets=packets, ordered_private_packet_sha256s=hashes,
                salt_hex="5" * 64, payloads=payloads, destination=full)
            self.owner, published = _publish_owned_selected_bundle_for_mutation(
                result_bytes=full_result, index=index, private_packets=packets,
                ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                payloads=payloads, bundle=full, presentation_ordinal=6,
                bundle_destination=selected, result_destination=result_path)
        _, one, chosen, chosen_hashes, chosen_payloads = published
        self.candidate = self.fixture.candidate(bundle_root=selected, index=one,
            private_packets=chosen, ordered_private_packet_sha256s=chosen_hashes,
            payloads=chosen_payloads, media_result_bytes=result_path.read_bytes())
        self.row = {"case_id": "bundle_mutation", "expected_result": "trust_invalid",
            "stimulus": {"argv": [self.owner._relative],
                "stdin_sha256": hashlib.sha256(b"").hexdigest(),
                "support_manifest_sha256": _EMPTY_SUPPORT_SHA}}
        self.leaf = selected / self.owner._relative

    def test_owned_selected_leaf_invalidates_trust_before_spawn(self):
        before = self.leaf.read_bytes()
        invoked = []
        observed = self.owner.observe_once(candidate=self.candidate,
            frozen_row=self.row, spawn=lambda: invoked.append(True))
        self.assertEqual(observed, "trust_invalid")
        self.assertEqual(invoked, [])
        self.assertEqual(self.leaf.read_bytes()[0], before[0] ^ 1)
        self.assertEqual(self.leaf.read_bytes()[1:], before[1:])
        self.assertTrue(self.leaf.exists())  # Never remove a changed input.
        with self.assertRaises(ValueError): self.candidate.invocation_binding_sha256()

    def test_wrong_frozen_row_or_changed_neighbor_blocks_mutation(self):
        wrong = json.loads(json.dumps(self.row))
        wrong["stimulus"]["argv"] = ["unowned.png"]
        before = self.leaf.read_bytes()
        with self.assertRaisesRegex(ValueError, "frozen"):
            self.owner.observe_once(candidate=self.candidate,
                frozen_row=wrong, spawn=lambda: self.fail("spawned"))
        self.assertEqual(self.leaf.read_bytes(), before)
        neighbor = self.owner._root / "unowned"
        self.owner._root.chmod(0o755)
        neighbor.write_bytes(b"preserve")
        self.owner._root.chmod(0o555)
        with self.assertRaises(ValueError):
            self.owner.observe_once(candidate=self.candidate,
                frozen_row=self.row, spawn=lambda: self.fail("spawned"))
        self.assertEqual(neighbor.read_bytes(), b"preserve")
        self.assertEqual(self.leaf.read_bytes(), before)

    def test_cached_trust_validator_cannot_assign_enum_by_case_name(self):
        baseline = self.candidate.invocation_binding_sha256()
        with mock.patch.object(self.candidate, "invocation_binding_sha256",
                               return_value=baseline):
            with self.assertRaisesRegex(ValueError, "accepted by retained trust"):
                self.owner.observe_once(candidate=self.candidate,
                    frozen_row=self.row, spawn=lambda: self.fail("spawned"))
        self.assertTrue(self.leaf.exists())


if __name__ == "__main__":
    unittest.main()
