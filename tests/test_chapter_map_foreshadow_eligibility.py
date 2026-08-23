import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.chapter_map_foreshadow_eligibility import assess_chapter_map_foreshadow_eligibility
from aegis360.whole_film_chapter_map import build_whole_film_chapter_map
from tests.test_whole_film_chapter_map import fixture, sha


class ChapterMapForeshadowEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.segments, self.config = fixture()
        self.chapter_map = build_whole_film_chapter_map(
            self.segments, self.config, segment_timeline_sha256=sha(self.segments),
            config_sha256=sha(self.config),
        )
        self.policy = json.loads(
            (ROOT / "config/chapter-map-foreshadow-policy-v1.json").read_text()
        )
        self.qualification = {
            "schema_version": "aegis360.chapter-map-qualification.v1",
            "qualification_id": "fixture-source-review-v1",
            "chapter_map_sha256": sha(self.chapter_map), "status": "qualified",
            "basis": "source_verified", "evidence_sha256": "f" * 64,
        }

    def assess(self, chapter_map=None, qualification=None, policy=None, map_config=None):
        chapter_map = self.chapter_map if chapter_map is None else chapter_map
        qualification = self.qualification if qualification is None else qualification
        policy = self.policy if policy is None else policy
        map_config = self.config if map_config is None else map_config
        return assess_chapter_map_foreshadow_eligibility(
            chapter_map, self.segments, map_config, qualification, policy,
            chapter_map_sha256=sha(chapter_map),
            segment_timeline_sha256=sha(self.segments),
            map_config_sha256=sha(map_config),
            qualification_sha256=sha(qualification), policy_sha256=sha(policy),
        )

    def test_qualified_later_destination_only_authorizes_planning(self):
        value = self.assess()
        self.assertTrue(value["eligible"])
        self.assertTrue(value["planner_authority"]["may_plan_one_prefix_foreshadow"])
        self.assertFalse(value["planner_authority"]["teaser_interval_selected"])

    def test_abstain_and_missing_destination_fail_to_chronology(self):
        abstain = copy.deepcopy(self.qualification)
        abstain["status"] = "abstain"
        self.assertEqual(self.assess(qualification=abstain)["reasons"],
                         ["chapter_map_not_independently_qualified"])
        no_destination_config = copy.deepcopy(self.config)
        no_destination_config["chapter_roles"] = ["journey", "other"]
        no_destination_map = build_whole_film_chapter_map(
            self.segments, no_destination_config,
            segment_timeline_sha256=sha(self.segments),
            config_sha256=sha(no_destination_config),
        )
        no_destination_qualification = copy.deepcopy(self.qualification)
        no_destination_qualification["chapter_map_sha256"] = sha(no_destination_map)
        value = self.assess(no_destination_map, no_destination_qualification,
                            map_config=no_destination_config)
        self.assertFalse(value["eligible"])
        self.assertEqual(value["reasons"], ["no_destination_chapter"])

    def test_stale_qualification_and_policy_mutation_reject(self):
        stale = copy.deepcopy(self.qualification)
        stale["chapter_map_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.assess(qualification=stale)
        broken = copy.deepcopy(self.policy)
        broken["minimum_chapter_count"] = 1
        with self.assertRaises(ValueError):
            self.assess(policy=broken)


if __name__ == "__main__":
    unittest.main()
