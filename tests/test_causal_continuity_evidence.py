import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.causal_continuity_evidence import (build_causal_continuity_evidence,
                                                validate_causal_continuity_evidence)
from aegis360.context_views import build_context_view_grid
from aegis360.story_segment_review_packet import build_story_segment_review_packet


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


if __name__ == "__main__":
    unittest.main()
