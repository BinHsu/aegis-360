import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.whole_film_chapter_map import (build_whole_film_chapter_map,
                                             validate_whole_film_chapter_map)
from tests.test_story_segment_timeline import digest, timeline_fixture
from aegis360.story_segment_timeline import build_story_segment_timeline


def fixture():
    timeline = timeline_fixture()
    segments = build_story_segment_timeline(timeline, timeline_sha256=digest(timeline))
    config = {
        "schema_version": "aegis360.whole-film-chapter-map-config.v1",
        "map_id": "fixture-map-v1",
        "reviewer_type": "agent", "reviewer_id": "fixture-reviewer-v1",
        "reviewer_asset_sha256": None,
        "boundary_dispositions": [
            {**segments["segments"][1]["left_boundary"],
             "structural_role": "within_chapter_cut"},
            {**segments["segments"][2]["left_boundary"],
             "structural_role": "chapter_boundary"},
        ],
        "chapter_roles": ["journey", "destination"],
    }
    return segments, config


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class WholeFilmChapterMapTests(unittest.TestCase):
    def build(self, segments=None, config=None):
        default_segments, default_config = fixture()
        segments = default_segments if segments is None else segments
        config = default_config if config is None else config
        return build_whole_film_chapter_map(
            segments, config, segment_timeline_sha256=sha(segments),
            config_sha256=sha(config),
        )

    def test_accounts_all_boundaries_and_derives_gap_free_chapters(self):
        segments, config = fixture()
        value = self.build(segments, config)
        self.assertEqual([(item["start_seconds"], item["end_seconds"])
                          for item in value["chapters"]], [(0.0, 20.0), (20.0, 30.0)])
        self.assertEqual([item["chapter_role"] for item in value["chapters"]],
                         ["journey", "destination"])
        self.assertTrue(value["completeness"]["all_retained_boundaries_accounted"])
        self.assertFalse(value["planner_authority"]["temporal_reordering_authorized"])
        validate_whole_film_chapter_map(
            value, segments, config, segment_timeline_sha256=sha(segments),
            config_sha256=sha(config),
        )

    def test_missing_reordered_or_ambiguous_boundary_fails_closed(self):
        segments, config = fixture()
        missing = copy.deepcopy(config)
        missing["boundary_dispositions"].pop()
        reordered = copy.deepcopy(config)
        reordered["boundary_dispositions"].reverse()
        unknown = copy.deepcopy(config)
        unknown["boundary_dispositions"][0]["structural_role"] = "unknown"
        for broken in (missing, reordered, unknown):
            with self.assertRaises(ValueError):
                self.build(segments, broken)

    def test_signal_id_timestamp_roles_and_exact_rebuild_are_closed(self):
        segments, config = fixture()
        mutations = []
        for key, value in (("signal_id", "wrong"), ("event_id", "wrong"),
                           ("timestamp_seconds", 19.5)):
            broken = copy.deepcopy(config)
            broken["boundary_dispositions"][1][key] = value
            mutations.append(broken)
        bad_roles = copy.deepcopy(config)
        bad_roles["chapter_roles"] = ["destination"]
        mutations.append(bad_roles)
        for broken in mutations:
            with self.assertRaises(ValueError):
                self.build(segments, broken)
        value = self.build(segments, config)
        value["chapters"][1]["chapter_role"] = "closing"
        with self.assertRaises(ValueError):
            validate_whole_film_chapter_map(
                value, segments, config, segment_timeline_sha256=sha(segments),
                config_sha256=sha(config),
            )

    def test_reviewer_provenance_is_explicit_and_fail_closed(self):
        segments, config = fixture()
        local = copy.deepcopy(config)
        local["reviewer_type"] = "local_model"
        local["reviewer_asset_sha256"] = "a" * 64
        self.assertEqual(self.build(segments, local)["provenance"]["reviewer_type"],
                         "local_model")
        for key, value in (("reviewer_id", "contains space"),
                           ("reviewer_asset_sha256", "bad")):
            broken = copy.deepcopy(local)
            broken[key] = value
            with self.assertRaises(ValueError):
                self.build(segments, broken)


if __name__ == "__main__":
    unittest.main()
