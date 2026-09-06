import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.causal_continuity_evidence import (build_causal_continuity_evidence,
                                                validate_causal_continuity_evidence)
from aegis360.context_views import build_context_view_grid
from aegis360.story_segment_review_packet import build_story_segment_review_packet
from aegis360.typed_story_segment_timeline import build_typed_story_segment_timeline
from tests.test_typed_segment_boundaries import TypedSegmentBoundaryTests


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class CausalContinuityEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                            duration_seconds=30)
        self.timeline = {"schema_version": "aegis360.story-segment-timeline.v1",
                         "source_id": "fixture", "window": self.grid["window"],
                         "segments": [
            {"segment_id": "s0", "start_seconds": 0, "end_seconds": 10},
            {"segment_id": "s1", "start_seconds": 10, "end_seconds": 20},
            {"segment_id": "s2", "start_seconds": 20, "end_seconds": 30},
        ]}
        self.grid_sha = digest(self.grid)
        self.timeline_sha = digest(self.timeline)
        self.packets = [build_story_segment_review_packet(
            self.timeline, self.grid, segment_id=item["segment_id"],
            segment_timeline_sha256=self.timeline_sha, grid_sha256=self.grid_sha,
        ) for item in self.timeline["segments"]]
        abstain = lambda left, right: {
            "from_segment_id": left, "to_segment_id": right, "status": "abstain",
            "from_cue": "unknown", "to_cue": "unknown",
            "narrative_relation": "unknown", "from_support": [], "to_support": [],
            "candidate_observations": [],
        }
        self.config = {"schema_version": "aegis360.causal-continuity-evidence-config.v1",
                       "reviewer_type": "agent", "reviewer_id": "fixture-v1",
                       "reviewer_asset_sha256": None,
                       "edges": [abstain("s0", "s1"), abstain("s1", "s2")]}

    def observe_first(self):
        edge = self.config["edges"][0]
        edge.update(status="observed", from_cue="transport_context",
                    to_cue="actor_presence", narrative_relation="establishes_expectation",
                    from_support=[{key: self.packets[0]["samples"][0][key]
                                   for key in ("sample_id", "timestamp_seconds")}],
                    to_support=[{key: self.packets[1]["samples"][1][key]
                                 for key in ("sample_id", "timestamp_seconds")}],
                    candidate_observations=[{
                        "candidate_id": candidate["candidate_id"],
                        "from_assessability": "clear", "to_assessability": "clear",
                        "from_cue_match": "present" if index == 0 else "absent",
                        "to_cue_match": "present" if index == 0 else "absent",
                        "relationship_preservation": "preserves" if index == 0 else "breaks",
                    } for index, candidate in enumerate(self.grid["candidates"])])

    def build(self, config=None):
        config = self.config if config is None else config
        return build_causal_continuity_evidence(
            config, self.timeline, self.packets, self.grid,
            config_sha256=digest(config), timeline_sha256=self.timeline_sha,
            packet_sha256s=[digest(item) for item in self.packets], grid_sha256=self.grid_sha,
        )

    def test_complete_scope_mixes_observed_and_explicit_abstention(self):
        self.observe_first()
        value = self.build()
        self.assertEqual([item["status"] for item in value["edges"]], ["observed", "abstain"])
        self.assertEqual(len(value["edges"][0]["candidate_observations"]), 4)
        self.assertFalse(value["planner_authority"]["candidate_selected"])
        validate_causal_continuity_evidence(
            value, self.config, self.timeline, self.packets, self.grid,
            config_sha256=digest(self.config), timeline_sha256=self.timeline_sha,
            packet_sha256s=[digest(item) for item in self.packets],
            grid_sha256=self.grid_sha,
        )
        value["edges"][0]["candidate_observations"][0]["relationship_preservation"] = "breaks"
        with self.assertRaises(ValueError):
            validate_causal_continuity_evidence(
                value, self.config, self.timeline, self.packets, self.grid,
                config_sha256=digest(self.config), timeline_sha256=self.timeline_sha,
                packet_sha256s=[digest(item) for item in self.packets],
                grid_sha256=self.grid_sha,
            )

    def test_legacy_digest_and_lineage_are_unchanged(self):
        value = self.build()
        self.assertEqual(digest(value),
                         "88fe091a6385b085a55bfa93d154a3f0e0e004b30f4d6045cb08b37370b8fa77")
        self.assertEqual(set(value["inputs"]), {
            "review_config_sha256", "story_segment_timeline_sha256",
            "story_segment_review_packet_sha256s", "context_view_grid_sha256"})

    def test_missing_edge_candidate_or_packet_sample_fails_closed(self):
        self.observe_first()
        cases = []
        missing_edge = copy.deepcopy(self.config); missing_edge["edges"].pop(); cases.append(missing_edge)
        missing_candidate = copy.deepcopy(self.config); missing_candidate["edges"][0]["candidate_observations"].pop(); cases.append(missing_candidate)
        invented_sample = copy.deepcopy(self.config); invented_sample["edges"][0]["from_support"][0]["sample_id"] = "invented"; cases.append(invented_sample)
        for config in cases:
            with self.assertRaises(ValueError):
                self.build(config)

    def test_abstention_cannot_carry_claims_and_model_requires_checksum(self):
        claimed = copy.deepcopy(self.config)
        claimed["edges"][0]["from_cue"] = "actor_presence"
        with self.assertRaises(ValueError):
            self.build(claimed)
        model = copy.deepcopy(self.config)
        model.update(reviewer_type="local_model", reviewer_asset_sha256=None)
        with self.assertRaises(ValueError):
            self.build(model)

    def _typed_single_segment(self):
        fixture = TypedSegmentBoundaryTests()
        fixture.setUp()
        boundaries = fixture.build()
        row = boundaries["boundaries"][0]
        row["disposition"] = "rejected"
        row["effective_timestamp_seconds"] = None
        row["typed_labels"] = {
            "classification": "no_semantic_change", "structural_role": "unknown",
            "change_type": "unknown", "narrative_function": "unknown",
            "viewer_value": "unknown"}
        boundaries["boundary_authority"]["authorized_boundary_count"] = 0
        timeline = build_typed_story_segment_timeline(
            fixture.grid, boundaries, grid_sha256=digest(fixture.grid),
            boundaries_sha256=digest(boundaries))
        timeline_sha = digest(timeline)
        packet = build_story_segment_review_packet(
            timeline, fixture.grid, segment_id="segment:typed-story:0000",
            segment_timeline_sha256=timeline_sha, grid_sha256=digest(fixture.grid))
        config = {
            "schema_version": "aegis360.causal-continuity-evidence-config.v1",
            "reviewer_type": "agent", "reviewer_id": "typed-zero-edge-v1",
            "reviewer_asset_sha256": None, "edges": []}
        return fixture.grid, timeline, packet, config

    def test_typed_single_segment_emits_exact_zero_edge_evidence(self):
        grid, timeline, packet, config = self._typed_single_segment()
        value = build_causal_continuity_evidence(
            config, timeline, [packet], grid, config_sha256=digest(config),
            timeline_sha256=digest(timeline), packet_sha256s=[digest(packet)],
            grid_sha256=digest(grid))
        self.assertEqual(value["edges"], [])
        self.assertEqual(set(value["inputs"]), {
            "review_config_sha256", "typed_story_segment_timeline_sha256",
            "typed_story_segment_review_packet_sha256s", "context_view_grid_sha256"})
        validate_causal_continuity_evidence(
            value, config, timeline, [packet], grid,
            config_sha256=digest(config), timeline_sha256=digest(timeline),
            packet_sha256s=[digest(packet)], grid_sha256=digest(grid))

        wrong = copy.deepcopy(packet)
        wrong["schema_version"] = "aegis360.story-segment-review-packet.v1"
        with self.assertRaises(ValueError):
            build_causal_continuity_evidence(
                config, timeline, [wrong], grid, config_sha256=digest(config),
                timeline_sha256=digest(timeline), packet_sha256s=[digest(wrong)],
                grid_sha256=digest(grid))

    def test_cli_accepts_typed_single_segment_and_no_packet_fabrication(self):
        grid, timeline, packet, config = self._typed_single_segment()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {name: root / f"{name}.json" for name in (
                "grid", "timeline", "packet", "config")}
            for name, value in (("grid", grid), ("timeline", timeline),
                                ("packet", packet), ("config", config)):
                paths[name].write_text(json.dumps(value, sort_keys=True))
            output = root / "evidence.json"
            result = subprocess.run([
                sys.executable, str(ROOT / "scripts/build_causal_continuity_evidence.py"),
                str(paths["config"]), str(paths["timeline"]), str(paths["grid"]),
                str(output), "--packet", str(paths["packet"])],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["edges"], [])


if __name__ == "__main__":
    unittest.main()
