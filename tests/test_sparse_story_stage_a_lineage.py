"""Synthetic lineage: supplied frozen evidence, not real Stage A authority."""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.context_views import build_context_view_grid  # noqa: E402
from aegis360.multi_signal_timeline import build_multi_signal_timeline  # noqa: E402
from aegis360.sparse_story_projection import (  # noqa: E402
    private_packet_sha256, validate_private_packet)
from aegis360.sparse_story_stage_a_lineage import (  # noqa: E402
    CENTERS, MANIFEST_SCHEMA, SOURCE_SLOTS,
    build_stage_a_private_packets, validate_stage_a_private_packets)


def digest(value):
    return hashlib.sha256(json.dumps(value, allow_nan=False, ensure_ascii=True,
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rational(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def raw(value):
    return json.dumps(value, ensure_ascii=True, indent=2).encode("utf-8") + b"\n"


def evidence():
    ids = ("old-ghost-synthetic", "skiing-synthetic")
    sources = [{"source_id": source_id, "source_sha256": str(i + 1) * 64,
                "duration": rational(CENTERS[-1] + 30)}
               for i, source_id in enumerate(ids)]
    grids = [build_context_view_grid(source_id=source_id,
        start_seconds=0, duration_seconds=500) for source_id in ids]
    timelines = []
    for slot, source_id in enumerate(ids):
        candidates = []
        for case, (case_slot, center) in enumerate(zip(SOURCE_SLOTS, CENTERS)):
            if case_slot == slot and case in (0, 2):
                moment = float(center)
                candidates.append({"event_id": f"signal:scene:{case:04d}",
                    "timestamp_seconds": moment, "scene_score": 0.5})
        scenes = {"schema_version": "aegis360.scene-change-candidates.v1",
                  "source_id": source_id, "candidates": candidates}
        timelines.append(build_multi_signal_timeline(grids[slot], scenes,
            grid_sha256=hashlib.sha256(raw(grids[slot])).hexdigest(),
            scene_candidates_sha256=digest(scenes)))
    manifest = {"schema_version": MANIFEST_SCHEMA,
        "sources": [{"source_id": source_id,
            "source_sha256": source["source_sha256"],
            "event_timeline_sha256": hashlib.sha256(raw(timeline)).hexdigest(),
            "context_view_grid_sha256": hashlib.sha256(raw(grid)).hexdigest()}
            for source_id, source, timeline, grid in zip(ids, sources, timelines, grids)],
        "selections": []}
    for case, (slot, center) in enumerate(zip(SOURCE_SLOTS, CENTERS)):
        role = "proposal" if case in (0, 2) else "control"
        manifest["selections"].append({"source_id": ids[slot], "role": role,
            "original_event_id": "event:multi:0000" if role == "proposal" else None,
            "original_signal_ids": [f"signal:scene:{case:04d}"] if role == "proposal" else [],
            "center_source_time": rational(center)})
    return {"execution_manifest": manifest, "execution_manifest_bytes": raw(manifest),
            "sources": sources, "timelines": timelines,
            "timeline_bytes": [raw(timeline) for timeline in timelines],
            "grids": grids, "grid_bytes": [raw(grid) for grid in grids]}


class StageALineageTests(unittest.TestCase):
    def test_exact_six_packet_rebuild_and_hash_order(self):
        frozen = evidence()
        packets, hashes = build_stage_a_private_packets(**frozen)
        self.assertEqual(len(packets), 6)
        self.assertEqual(hashes, [private_packet_sha256(packet) for packet in packets])
        self.assertEqual([packet["selection"]["role"] for packet in packets],
                         [row["role"] for row in frozen["execution_manifest"]["selections"]])
        self.assertEqual([packet["source_id"] for packet in packets],
                         [frozen["sources"][slot]["source_id"] for slot in SOURCE_SLOTS])
        validate_stage_a_private_packets(private_packets=packets,
            ordered_private_packet_sha256s=hashes, **frozen)

    def test_shape_valid_mutation_fails_lineage(self):
        frozen = evidence()
        packets, hashes = build_stage_a_private_packets(**frozen)
        changed = copy.deepcopy(packets)
        changed[0]["selection"]["original_signal_ids"] = ["signal:wrong"]
        validate_private_packet(changed[0])  # Old shape-only gate accepted it.
        changed_hashes = [private_packet_sha256(packet) for packet in changed]
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            validate_stage_a_private_packets(private_packets=changed,
                ordered_private_packet_sha256s=changed_hashes, **frozen)
        changed = copy.deepcopy(packets)
        for row in changed[0]["rows"]:
            row["cardinal_views"][0], row["cardinal_views"][1] = (
                row["cardinal_views"][1], row["cardinal_views"][0])
        validate_private_packet(changed[0])
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            validate_stage_a_private_packets(private_packets=changed,
                ordered_private_packet_sha256s=[private_packet_sha256(p) for p in changed],
                **frozen)

    def test_changed_frozen_evidence_and_order_fail(self):
        frozen = evidence()
        packets, hashes = build_stage_a_private_packets(**frozen)
        mutations = []
        changed = copy.deepcopy(frozen); changed["execution_manifest"]["selections"].reverse(); mutations.append(changed)
        changed = copy.deepcopy(frozen); changed["execution_manifest"]["sources"][0]["event_timeline_sha256"] = "f" * 64; mutations.append(changed)
        changed = copy.deepcopy(frozen); changed["grids"][0]["candidates"][0]["yaw_degrees"] = 10.0; mutations.append(changed)
        changed = copy.deepcopy(frozen); changed["timelines"][0]["events"][0]["signals"][0]["signal_id"] = "signal:changed"; mutations.append(changed)
        changed = copy.deepcopy(frozen); changed["execution_manifest"]["selections"][0]["center_source_time"] = rational(CENTERS[0] + 1); mutations.append(changed)
        changed = copy.deepcopy(frozen); changed["execution_manifest"]["selections"][0]["original_event_id"] = "event:wrong"; mutations.append(changed)
        changed = copy.deepcopy(frozen); changed["execution_manifest"]["selections"][0]["original_signal_ids"] = [{}]; mutations.append(changed)
        for changed in mutations:
            with self.subTest(change=changed):
                with self.assertRaises(ValueError):
                    build_stage_a_private_packets(**changed)
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            validate_stage_a_private_packets(private_packets=packets[::-1],
                ordered_private_packet_sha256s=hashes[::-1], **frozen)

    def test_raw_bytes_are_hash_authority_and_duplicate_keys_fail(self):
        frozen = evidence()
        packets, _ = build_stage_a_private_packets(**frozen)
        compact = json.dumps(frozen["timelines"][0], sort_keys=True,
            separators=(",", ":")).encode()
        frozen["timeline_bytes"][0] = compact
        with self.assertRaisesRegex(ValueError, "frozen manifest"):
            build_stage_a_private_packets(**frozen)
        frozen["execution_manifest"]["sources"][0]["event_timeline_sha256"] = (
            hashlib.sha256(compact).hexdigest())
        frozen["execution_manifest_bytes"] = raw(frozen["execution_manifest"])
        changed_packets, _ = build_stage_a_private_packets(**frozen)
        self.assertNotEqual(packets[0]["inputs"]["event_timeline_sha256"],
                            changed_packets[0]["inputs"]["event_timeline_sha256"])
        frozen["grid_bytes"][0] = b'{"source_id":"x","source_id":"y"}'
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_stage_a_private_packets(**frozen)

    def test_selected_signal_subset_and_control_with_timeline_event(self):
        frozen = evidence()
        # Two close scene signals merge into one event; selecting one is valid.
        scenes = {"schema_version": "aegis360.scene-change-candidates.v1",
            "source_id": frozen["sources"][0]["source_id"],
            "candidates": [
                {"event_id": "signal:scene:0000", "timestamp_seconds": 205.6,
                 "scene_score": 0.5},
                {"event_id": "signal:scene:extra", "timestamp_seconds": 205.8,
                 "scene_score": 0.5}]}
        frozen["timelines"][0] = build_multi_signal_timeline(
            frozen["grids"][0], scenes,
            grid_sha256=hashlib.sha256(frozen["grid_bytes"][0]).hexdigest(),
            scene_candidates_sha256=digest(scenes))
        self.assertEqual(len(frozen["timelines"][0]["events"][0]["signals"]), 2)
        frozen["timeline_bytes"][0] = raw(frozen["timelines"][0])
        frozen["execution_manifest"]["sources"][0]["event_timeline_sha256"] = (
            hashlib.sha256(frozen["timeline_bytes"][0]).hexdigest())
        # A timeline event at Skiing 200 may still be frozen as a control.
        scenes = {"schema_version": "aegis360.scene-change-candidates.v1",
            "source_id": frozen["sources"][1]["source_id"],
            "candidates": [{"event_id": "signal:scene:0002",
                            "timestamp_seconds": 200.0, "scene_score": 0.5}]}
        frozen["timelines"][1] = build_multi_signal_timeline(
            frozen["grids"][1], scenes,
            grid_sha256=hashlib.sha256(frozen["grid_bytes"][1]).hexdigest(),
            scene_candidates_sha256=digest(scenes))
        frozen["timeline_bytes"][1] = raw(frozen["timelines"][1])
        frozen["execution_manifest"]["sources"][1]["event_timeline_sha256"] = (
            hashlib.sha256(frozen["timeline_bytes"][1]).hexdigest())
        frozen["execution_manifest_bytes"] = raw(frozen["execution_manifest"])
        packets, _ = build_stage_a_private_packets(**frozen)
        self.assertEqual(packets[0]["selection"]["original_signal_ids"],
                         ["signal:scene:0000"])
        self.assertEqual(packets[2]["selection"]["role"], "proposal")
        frozen["execution_manifest"]["selections"][2] = {
            "source_id": frozen["sources"][1]["source_id"], "role": "control",
            "original_event_id": None, "original_signal_ids": [],
            "center_source_time": rational(CENTERS[2])}
        frozen["execution_manifest_bytes"] = raw(frozen["execution_manifest"])
        packets, _ = build_stage_a_private_packets(**frozen)
        self.assertEqual(packets[2]["selection"]["role"], "control")


if __name__ == "__main__":
    unittest.main()
