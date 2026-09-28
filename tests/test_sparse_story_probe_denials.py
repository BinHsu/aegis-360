import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_media_tree import (  # noqa: E402
    publish_sanitized_media_gate, publish_selected_one_packet_media_gate,
)
from aegis360.sparse_story_probe_denials import (  # noqa: E402
    _OwnedOnePacketNeighbor, _retain_full_set_denials,
)
from tests import test_sparse_story_batch_policy as batch_tests  # noqa: E402
from tests import test_sparse_story_media_tree as media_tests  # noqa: E402
from tests import test_sparse_story_projection as projection_tests  # noqa: E402


class FullSetDenialTests(unittest.TestCase):
    def fixture(self):
        owner = batch_tests.BatchPolicyTests(
            "test_exact_policy_is_frozen_and_path_free_digest_only")
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        packets, hashes, index = projection_tests.SparseStoryProjectionTests().build(6)
        payloads = media_tests.SparseStoryMediaTreeTests().payloads(index)
        full = owner.base / "full-bundle"
        full_result = owner.base / "full-result.json"
        selected = owner.base / "selected-bundle"
        selected_result = owner.base / "selected-result.json"
        with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive",
                side_effect=media_tests.local_rename):
            publish_sanitized_media_gate(index=index, private_packets=packets,
                ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                payloads=payloads, bundle_destination=full,
                result_destination=full_result)
            _, one, chosen, chosen_hashes, chosen_payloads = (
                publish_selected_one_packet_media_gate(
                    result_bytes=full_result.read_bytes(), index=index,
                    private_packets=packets,
                    ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                    payloads=payloads, bundle=full, presentation_ordinal=6,
                    bundle_destination=selected,
                    result_destination=selected_result))
        candidate = owner.candidate(bundle_root=selected, index=one,
            private_packets=chosen, ordered_private_packet_sha256s=chosen_hashes,
            payloads=chosen_payloads,
            media_result_bytes=selected_result.read_bytes())
        return dict(candidate=candidate, result_bytes=full_result.read_bytes(),
            index=index, private_packets=packets,
            ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
            payloads=payloads, bundle=full, result_path=full_result)

    def test_proofs_bind_actual_neighbor_and_result(self):
        values = self.fixture()
        with _retain_full_set_denials(**values) as (neighbor, result):
            self.assertTrue(neighbor.path.is_relative_to(values["bundle"]))
            self.assertNotIn(values["candidate"]._roots["bundle_root"],
                str(neighbor.path))
            self.assertEqual(result.path, values["result_path"])
            neighbor.revalidate()
            result.revalidate()

    def test_changed_result_and_nonmember_candidate_reject(self):
        values = self.fixture()
        with self.assertRaisesRegex(ValueError, "denial source"):
            with _retain_full_set_denials(**(values | {
                    "result_bytes": values["result_bytes"] + b" "})):
                self.fail("mismatched full result was retained")
        candidate = values["candidate"]
        original = candidate._request_bytes
        try:
            changed = json.loads(original)
            changed["packet_id"] = "packet-" + "0" * 20
            candidate._request_bytes = json.dumps(changed, sort_keys=True,
                separators=(",", ":")).encode()
            with self.assertRaisesRegex(ValueError, "not in the full set"):
                with _retain_full_set_denials(**values):
                    self.fail("nonmember packet was retained")
        finally:
            candidate._request_bytes = original
        values["result_path"].chmod(0o644)
        values["result_path"].write_bytes(b"different result")
        with self.assertRaisesRegex(ValueError, "result leaf does not match"):
            with _retain_full_set_denials(**values):
                self.fail("changed result leaf was retained")


class OnePacketNeighborTests(unittest.TestCase):
    def fixture(self):
        owner = batch_tests.BatchPolicyTests(
            "test_exact_policy_is_frozen_and_path_free_digest_only")
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        return owner, owner.candidate()

    def test_owned_decoy_revalidates_and_cleans_only_after_reap(self):
        owner, candidate = self.fixture()
        decoy = _OwnedOnePacketNeighbor(candidate=candidate, parent=owner.base)
        decoy.revalidate()
        self.assertTrue(decoy.path.exists())
        decoy.finish_after_reap(0)
        self.assertFalse(decoy.root.exists())
        with self.assertRaisesRegex(ValueError, "closed"):
            decoy.revalidate()
        unreaped = _OwnedOnePacketNeighbor(candidate=candidate, parent=owner.base)
        with self.assertRaisesRegex(ValueError, "before reap"):
            unreaped.finish_after_reap(None)
        self.assertTrue(unreaped.root.exists())

    def test_changed_decoy_is_preserved_and_allowed_root_rejected(self):
        owner, candidate = self.fixture()
        decoy = _OwnedOnePacketNeighbor(candidate=candidate, parent=owner.base)
        decoy.path.write_bytes(b"replaced content")
        with self.assertRaises(ValueError): decoy.finish_after_reap(0)
        self.assertEqual(decoy.path.read_bytes(), b"replaced content")
        scratch = owner.args["scratch_root"]
        before = set(scratch.glob("aegis-neighbor-*"))
        with self.assertRaisesRegex(ValueError, "overlaps policy roots"):
            _OwnedOnePacketNeighbor(candidate=candidate, parent=scratch)
        self.assertEqual(set(scratch.glob("aegis-neighbor-*")), before)


if __name__ == "__main__": unittest.main()
