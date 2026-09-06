import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid  # noqa: E402
from aegis360.scene_boundary_story_packet import build_scene_boundary_story_packet  # noqa: E402
from aegis360.structural_blind_selection import (  # noqa: E402
    CONFIG_SHA256, TIMELINE_SOURCE_ID, build_selection_proof, validate_selection_config,
    validate_selection_proof,
)


class StructuralBlindSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "config/structural-chapter-blind-selection-v1.json").read_bytes())
        cls.timeline_sha = cls.config["timeline"]["sha256"]
        cls.grid_sha = cls.config["proof_packet_contract"]["context_view_grid_sha256"]

    def fixture(self, times=None):
        if times is None:
            times = [10 + i * 9 for i in range(26)]
        grid = build_context_view_grid(source_id=TIMELINE_SOURCE_ID, start_seconds=0,
                                       duration_seconds=max(300, max(times) + 20))
        events = []
        for i, timestamp in enumerate(times):
            signal = {"signal_id": f"event:scene-change:{i:04d}", "signal_type": "scene_change",
                      "start_seconds": float(timestamp - 2), "end_seconds": float(timestamp + 2),
                      "evidence": {"timestamp_seconds": float(timestamp), "scene_score": 0.5}}
            events.append({"event_id": f"event:multi:{i:04d}", "start_seconds": float(timestamp - 2),
                           "end_seconds": float(timestamp + 2), "signals": [signal],
                           "review_scope": {"mode": "all_declared_candidates", "candidate_ids": [c["candidate_id"] for c in grid["candidates"]]}})
        timeline = {"schema_version": "aegis360.event-timeline.v2", "source_id": TIMELINE_SOURCE_ID,
                    "window": grid["window"], "inputs": {"context_view_grid_sha256": self.grid_sha,
                    "scene_change_candidates_sha256": "a" * 64, "reaction_timeline_sha256": None},
                    "fusion_policy": {"scene_context_seconds": 2.0, "cluster_rule": "overlapping_review_windows_v1"},
                    "events": events, "privacy": {}, "limitations": []}
        packets = [build_scene_boundary_story_packet(timeline, grid, event_id=e["event_id"],
                   signal_id=e["signals"][0]["signal_id"], timeline_sha256=self.timeline_sha,
                   grid_sha256=self.grid_sha, far_context_seconds=15.0,
                   near_context_seconds=3.0, boundary_offset_seconds=0.25) for e in events]
        hashes = [hashlib.sha256(json.dumps(p, sort_keys=True).encode()).hexdigest() for p in packets]
        return timeline, grid, packets, hashes

    def build(self, times=None):
        timeline, grid, packets, hashes = self.fixture(times)
        inputs = dict(config=self.config, config_sha256=CONFIG_SHA256,
                      timeline=timeline, timeline_sha256=self.timeline_sha,
                      grid=grid, grid_sha256=self.grid_sha,
                      packets=packets, packet_sha256s=hashes)
        return build_selection_proof(**inputs), inputs

    def test_exact_config_and_closed_tamper(self):
        validate_selection_config(self.config)
        bad = copy.deepcopy(self.config); bad["selection"]["packet_count"] = 7
        with self.assertRaises(ValueError): validate_selection_config(bad)
        extra = copy.deepcopy(self.config); extra["path"] = "/Volumes/source"
        with self.assertRaises(ValueError): validate_selection_config(extra)

    def test_complete_proof_order_dispositions_and_exact_validator(self):
        artifact, inputs = self.build()
        self.assertEqual(len(artifact["universe"]), 26)
        self.assertEqual(len(artifact["selected"]), 8)
        self.assertTrue(all(artifact["universe"][i]["selection_digest"] <= artifact["universe"][i + 1]["selection_digest"] for i in range(25)))
        self.assertIn("after_cap", {row["disposition"] for row in artifact["universe"]})
        validate_selection_proof(artifact, **inputs)
        bad = copy.deepcopy(artifact)
        bad["universe"][0]["disposition"] = (
            "after_cap" if bad["universe"][0]["disposition"] != "after_cap"
            else "selected")
        with self.assertRaises(ValueError): validate_selection_proof(bad, **inputs)
        self.assertNotIn("/Volumes/", json.dumps(artifact))

    def test_exact_distance_eight_is_eligible_and_exclusion_eight_not_excluded(self):
        # 45 is exactly eight seconds from development time 53 and is eligible.
        times = [45, 100, 108] + [130 + i * 9 for i in range(23)]
        artifact, _ = self.build(times)
        row45 = next(row for row in artifact["universe"] if row["source_time"] == {"numerator": 45, "denominator": 1})
        self.assertNotEqual(row45["disposition"], "development_excluded")
        # If 100 and 108 encounter each other before cap, exact separation 8
        # cannot be rejected for separation (after-cap remains possible).
        rows = [row for row in artifact["universe"] if row["source_time"]["numerator"] in (100, 108)]
        if all(row["disposition"] != "after_cap" for row in rows):
            self.assertFalse(any(row["disposition"] == "minimum_separation" for row in rows))

        source_sha = self.config["source"]["sha256"]
        ranked = sorted(range(26), key=lambda i: hashlib.sha256(
            f"{source_sha}|{self.timeline_sha}|structural-blind-replication-v1|event:multi:{i:04d}|event:scene-change:{i:04d}".encode()).hexdigest())
        spaced = [500 + i * 20 for i in range(26)]
        spaced[ranked[0]], spaced[ranked[1]] = 300, 308
        artifact, _ = self.build(spaced)
        first_two = artifact["universe"][:2]
        self.assertEqual([row["disposition"] for row in first_two],
                         ["selected", "selected"])

    def test_duplicate_packet_signal_and_undercap_fail(self):
        timeline, grid, packets, hashes = self.fixture()
        duplicate = list(packets); duplicate[1] = duplicate[0]
        with self.assertRaisesRegex(ValueError, "duplicated"):
            build_selection_proof(config=self.config, config_sha256=CONFIG_SHA256,
                timeline=timeline, timeline_sha256=self.timeline_sha, grid=grid,
                grid_sha256=self.grid_sha, packets=duplicate, packet_sha256s=hashes)
        # All rows remain valid packets but all timestamps lie within a single
        # <8-second cluster, making the frozen cap impossible.
        close_times = [300 + i / 10 for i in range(26)]
        timeline, grid, packets, hashes = self.fixture(close_times)
        with self.assertRaisesRegex(ValueError, "cannot fill"):
            build_selection_proof(config=self.config, config_sha256=CONFIG_SHA256,
                timeline=timeline, timeline_sha256=self.timeline_sha, grid=grid,
                grid_sha256=self.grid_sha, packets=packets, packet_sha256s=hashes)

    def test_cli_error_is_path_free_and_leaves_no_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            secret = root / "private-source-name"
            secret.write_text("{}")
            output = root / "proof.json"
            command = [sys.executable, str(ROOT / "scripts/build_structural_blind_selection.py"),
                       str(secret), str(secret), str(secret), str(output), str(secret)]
            result = subprocess.run(command, capture_output=True, text=True,
                                    env=dict(os.environ))
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(str(root), result.stderr)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".proof.json.*")), [])


if __name__ == "__main__": unittest.main()
