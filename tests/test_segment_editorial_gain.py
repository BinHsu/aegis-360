import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.segment_editorial_gain import build_segment_editorial_gain, validate_segment_editorial_gain


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class SegmentEditorialGainTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "schema_version": "aegis360.segment-editorial-gain-config.v1",
            "review_id": "skiing-a-v1", "reviewer_type": "human",
            "reviewer_id": "owner-blind-pairwise-v1", "reviewer_asset_sha256": None,
            "candidate_media_sha256": "a" * 64, "baseline_media_sha256": "b" * 64,
            "decision": "retain_baseline",
            "reasons": ["stronger_causal_cues", "smoother_transition",
                        "no_preference_gain", "abrupt_switch"],
        }

    def test_retains_baseline_with_closed_reasons_and_exact_rebuild(self):
        value = build_segment_editorial_gain(self.config, config_sha256=sha(self.config))
        self.assertEqual(value["planner_mapping"],
                         {"candidate_eligible": False, "fallback": "baseline"})
        validate_segment_editorial_gain(value, self.config, config_sha256=sha(self.config))

    def test_contradictions_lineage_and_mutation_fail(self):
        cases = []
        promote = copy.deepcopy(self.config)
        promote["decision"] = "promote_candidate"
        cases.append(promote)
        same = copy.deepcopy(self.config)
        same["baseline_media_sha256"] = same["candidate_media_sha256"]
        cases.append(same)
        unknown = copy.deepcopy(self.config)
        unknown["reasons"] = ["unknown"]
        cases.append(unknown)
        for broken in cases:
            with self.assertRaises(ValueError):
                build_segment_editorial_gain(broken, config_sha256=sha(broken))
        value = build_segment_editorial_gain(self.config, config_sha256=sha(self.config))
        value["decision"] = "promote_candidate"
        with self.assertRaises(ValueError):
            validate_segment_editorial_gain(value, self.config, config_sha256=sha(self.config))


if __name__ == "__main__":
    unittest.main()
