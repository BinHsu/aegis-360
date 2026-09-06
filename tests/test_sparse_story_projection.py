import copy
import hashlib
import hmac
import json
import math
import sys
import unittest
from fractions import Fraction
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_projection import (  # noqa: E402
    build_adapter_index, canonical_index_bytes, canonical_private_packet_bytes,
    canonical_projection_bytes, index_sha256, private_packet_sha256,
    projection_sha256, validate_adapter_index, validate_private_packet,
)


def rational(value): return {"numerator": value.numerator, "denominator": value.denominator}


def packet(index=0, manifest="1" * 64, role="proposal"):
    center = Fraction(40 + index * 40)
    offsets = (Fraction(-15), Fraction(-3), Fraction(-1, 4), Fraction(1, 4), Fraction(3), Fraction(15))
    roles = ("early_far", "early_near", "transition_before", "transition_after", "late_near", "late_far")
    views = [{"candidate_id": f"candidate:{i}", "yaw_degrees": float((0, 90, -180, -90)[i]), "pitch_degrees": 0.0, "horizontal_fov_degrees": 110.0} for i in range(4)]
    selection = ({"role": "proposal", "original_event_id": f"event:{index}", "original_signal_ids": [f"signal:{index}"]} if role == "proposal" else {"role": "control", "original_event_id": None, "original_signal_ids": []})
    return {"schema_version": "aegis360.sparse-story-private-packet.v1", "source_id": "source:fixture",
        "selection": selection, "inputs": {"execution_manifest_sha256": manifest,
        "source_sha256": "2" * 64, "event_timeline_sha256": "3" * 64,
        "context_view_grid_sha256": "4" * 64}, "center_source_time": rational(center),
        "rows": [{"row_number": n, "row_role": name, "absolute_source_time": rational(center + offset), "cardinal_views": copy.deepcopy(views)} for n, (name, offset) in enumerate(zip(roles, offsets), 1)],
        "privacy": {"contains_source_path": False, "contains_pixels": False, "contains_audio": False, "contains_expected_class": False, "contains_reviewer_result": False},
        "authority": {"lineage_input": True, "semantic_observation": False, "exact_boundary": False, "chapter_map": False, "camera": False, "reorder": False, "render": False}}


class SparseStoryProjectionTests(unittest.TestCase):
    def build(self, count=6):
        packets = [packet(i, role="control" if i % 2 else "proposal") for i in range(count)]
        hashes = [private_packet_sha256(value) for value in packets]
        return packets, hashes, build_adapter_index(private_packets=packets, ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)

    def test_private_canonical_hash_and_structure(self):
        value = packet(); validate_private_packet(value)
        self.assertEqual(private_packet_sha256(value), hashlib.sha256(canonical_private_packet_bytes(value)).hexdigest())
        for mutate in (lambda p: p["rows"].reverse(), lambda p: p["rows"].pop(), lambda p: p["rows"].append(copy.deepcopy(p["rows"][0])), lambda p: p["rows"][0].__setitem__("extra", 1), lambda p: p["rows"][0].__setitem__("absolute_source_time", {"numerator": 1, "denominator": 3}), lambda p: p["rows"][0]["cardinal_views"][0].__setitem__("yaw_degrees", math.nan), lambda p: p["privacy"].__setitem__("contains_pixels", True), lambda p: p["authority"].__setitem__("render", True)):
            changed = copy.deepcopy(value); mutate(changed)
            with self.assertRaises(ValueError): validate_private_packet(changed)
        invalid = []
        for mutate in (
            lambda p: p["rows"][0].__setitem__("row_number", True),
            lambda p: p["selection"].__setitem__("original_signal_ids", ["signal:x", "signal:x"]),
            lambda p: p["selection"].__setitem__("original_signal_ids", [7]),
            lambda p: p["selection"].__setitem__("original_event_id", "unsafe id"),
            lambda p: p["rows"][0]["cardinal_views"][1].__setitem__("candidate_id", "candidate:0"),
            lambda p: p["rows"][0]["cardinal_views"][0].__setitem__("candidate_id", 7),
            lambda p: p.__setitem__("center_source_time", {"numerator": 2, "denominator": 2}),
            lambda p: p.__setitem__("center_source_time", {"numerator": -1, "denominator": 1}),
            lambda p: p.__setitem__("center_source_time", {"numerator": True, "denominator": 1}),
            lambda p: p["rows"][0]["cardinal_views"][0].__setitem__("yaw_degrees", math.inf),
            lambda p: p["rows"][0]["cardinal_views"][0].__setitem__("yaw_degrees", 180),
            lambda p: p["rows"][0]["cardinal_views"][0].__setitem__("horizontal_fov_degrees", 181),
        ):
            changed = copy.deepcopy(value); mutate(changed); invalid.append(changed)
        for changed in invalid:
            with self.assertRaises(ValueError): validate_private_packet(changed)
        control = packet(role="control"); validate_private_packet(control)
        self.assertIsNone(control["selection"]["original_event_id"])
        self.assertEqual(control["selection"]["original_signal_ids"], [])
        bad_control = copy.deepcopy(control); bad_control["selection"]["original_event_id"] = "event:x"
        with self.assertRaises(ValueError): validate_private_packet(bad_control)

    def test_set_sizes_hash_order_manifest_and_exact_projection(self):
        for count in (1, 6, 24):
            packets, hashes, index = self.build(count)
            validate_adapter_index(index, private_packets=packets, ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)
            self.assertEqual(index["packet_count"], count)
            self.assertEqual(index_sha256(index), hashlib.sha256(canonical_index_bytes(index)).hexdigest())
            for ordinal, item in enumerate(index["packets"], 1):
                self.assertEqual(item["presentation_ordinal"], ordinal)
                projection = item["projection"]
                self.assertEqual(projection_sha256(projection), hashlib.sha256(canonical_projection_bytes(projection)).hexdigest())
                self.assertEqual([r["views"] for r in projection["rows"]], [["view-1", "view-2", "view-3", "view-4"]] * 6)
                self.assertEqual(set(projection), {"schema_version", "packet_id",
                    "rows", "privacy", "authority"})
        packets, hashes, _ = self.build()
        for bad_packets, bad_hashes in ((packets[:-1], hashes), (packets + [packet(9)], hashes), (packets, hashes[::-1])):
            with self.assertRaises(ValueError): build_adapter_index(private_packets=bad_packets, ordered_private_packet_sha256s=bad_hashes, salt_hex="5" * 64)
        changed = copy.deepcopy(packets); changed[-1]["inputs"]["execution_manifest_sha256"] = "9" * 64
        changed_hashes = [private_packet_sha256(p) for p in changed]
        with self.assertRaisesRegex(ValueError, "manifest"): build_adapter_index(private_packets=changed, ordered_private_packet_sha256s=changed_hashes, salt_hex="5" * 64)

    def test_public_mutation_unsafe_types_salt_and_collision_fail(self):
        packets, hashes, index = self.build()
        mutations = []
        for change in (lambda x: x["packets"].reverse(), lambda x: x["packets"].pop(), lambda x: x.__setitem__("extra", 1), lambda x: x["packets"][0]["projection"]["rows"][0].__setitem__("media_ref", "../x"), lambda x: x["packets"][0]["projection"]["privacy"].__setitem__("contains_source_id", True)):
            changed = copy.deepcopy(index); change(changed); mutations.append(changed)
        for changed in mutations:
            with self.assertRaises(ValueError): validate_adapter_index(changed, private_packets=packets, ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)
        for salt in ("A" * 64, "5" * 63, 5):
            with self.assertRaises(ValueError): build_adapter_index(private_packets=packets, ordered_private_packet_sha256s=hashes, salt_hex=salt)
        with mock.patch("aegis360.sparse_story_projection._hmac", return_value="a" * 64):
            with self.assertRaisesRegex(ValueError, "collision"): build_adapter_index(private_packets=packets, ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)

    def test_hmac_vector_changed_salt_and_canonical_nonjson(self):
        packets = [packet(role="control")]; hashes = [private_packet_sha256(packets[0])]
        first = build_adapter_index(private_packets=packets,
            ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)
        manifest = packets[0]["inputs"]["execution_manifest_sha256"]
        expected = hmac.new(bytes.fromhex("5" * 64),
            f"id|successor-packet-v1|{manifest}|{hashes[0]}".encode(),
            hashlib.sha256).hexdigest()
        self.assertEqual(first["packets"][0]["projection"]["packet_id"],
                         "packet-" + expected[:20])
        second = build_adapter_index(private_packets=packets,
            ordered_private_packet_sha256s=hashes, salt_hex="6" * 64)
        self.assertNotEqual(first, second)
        with mock.patch("aegis360.sparse_story_projection._hmac", return_value="a" * 64):
            with self.assertRaisesRegex(ValueError, "collision"):
                build_adapter_index(private_packets=packets,
                    ordered_private_packet_sha256s=hashes, salt_hex="5" * 64)
        nonjson = packet(); nonjson["extra"] = {1, 2}
        with self.assertRaises(ValueError): canonical_private_packet_bytes(nonjson)


if __name__ == "__main__": unittest.main()
