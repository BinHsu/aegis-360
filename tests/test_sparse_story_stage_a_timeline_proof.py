"""Synthetic upstream JSON proof; no source-media or model claim."""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aegis360.context_views import build_context_view_grid  # noqa: E402
from aegis360.multi_signal_timeline import build_multi_signal_timeline  # noqa: E402
from aegis360.sparse_story_stage_a_timeline_proof import (  # noqa: E402
    validate_stage_a_timeline_upstream)


def raw(value):
    return (json.dumps(value, allow_nan=False, sort_keys=True, indent=2)
            + "\n").encode("utf-8")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def fixture(reaction=False):
    grid = build_context_view_grid(source_id="synthetic-source",
        start_seconds=0, duration_seconds=60)
    scenes = {"schema_version": "aegis360.scene-change-candidates.v1",
        "source_id": "synthetic-source", "candidates": [
            {"event_id": "scene:one", "timestamp_seconds": 20.0,
             "scene_score": 0.75}]}
    grid_bytes, scene_bytes = raw(grid), raw(scenes)
    reaction_doc = ({"schema_version": "aegis360.event-timeline.v1",
        "source_id": "synthetic-source", "window": grid["window"],
        "events": [{"event_id": "reaction:one", "start_seconds": 19.5,
            "end_seconds": 20.5, "audio_evidence": {"sample": "synthetic"},
            "view_context": {"current_candidate_id": "view:front",
                "proposed_candidate_id": "view:right",
                "proposed_available_intervals": []}}]} if reaction else None)
    reaction_bytes = None if reaction_doc is None else raw(reaction_doc)
    timeline = build_multi_signal_timeline(grid, scenes,
        grid_sha256=sha(grid_bytes), scene_candidates_sha256=sha(scene_bytes),
        reaction_timeline=reaction_doc,
        reaction_timeline_sha256=None if reaction_bytes is None else sha(reaction_bytes),
        scene_context_seconds=2.0)
    timeline_bytes = raw(timeline)
    return {"grid_bytes": grid_bytes, "scene_candidates_bytes": scene_bytes,
            "reaction_timeline_bytes": reaction_bytes,
            "timeline_bytes": timeline_bytes, "timeline_sha256": sha(timeline_bytes)}


class StageATimelineProofTests(unittest.TestCase):
    def test_exact_rebuild_without_and_with_reaction(self):
        for reaction in (False, True):
            with self.subTest(reaction=reaction):
                validate_stage_a_timeline_upstream(**fixture(reaction))

    def test_self_consistent_changed_timeline_hash_rejected(self):
        evidence = fixture()
        changed = json.loads(evidence["timeline_bytes"])
        changed["events"][0]["event_id"] = "event:multi:forged"
        evidence["timeline_bytes"] = raw(changed)
        evidence["timeline_sha256"] = sha(evidence["timeline_bytes"])
        # The raw hash and the timeline document agree; its upstream derivation
        # does not. A hash-only or shape-only check would accept this mutation.
        self.assertEqual(sha(evidence["timeline_bytes"]), evidence["timeline_sha256"])
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            validate_stage_a_timeline_upstream(**evidence)

    def test_raw_input_hashes_and_frozen_policy(self):
        evidence = fixture()
        changed = copy.deepcopy(evidence)
        changed["grid_bytes"] += b" "
        with self.assertRaisesRegex(ValueError, "upstream raw-byte"):
            validate_stage_a_timeline_upstream(**changed)
        changed = copy.deepcopy(evidence)
        changed["scene_candidates_bytes"] += b" "
        with self.assertRaisesRegex(ValueError, "upstream raw-byte"):
            validate_stage_a_timeline_upstream(**changed)
        changed = copy.deepcopy(evidence)
        changed["timeline_bytes"] += b" "
        with self.assertRaisesRegex(ValueError, "raw-byte"):
            validate_stage_a_timeline_upstream(**changed)
        changed = copy.deepcopy(evidence)
        timeline = json.loads(changed["timeline_bytes"])
        timeline["fusion_policy"]["scene_context_seconds"] = 3.0
        changed["timeline_bytes"] = raw(timeline)
        changed["timeline_sha256"] = sha(changed["timeline_bytes"])
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            validate_stage_a_timeline_upstream(**changed)

    def test_strict_json_rejects_duplicate_and_nonfinite(self):
        evidence = fixture()
        for key, payload in (("grid_bytes", b'{"x":1,"x":2}'),
                             ("scene_candidates_bytes", b'{"x":NaN}'),
                             ("reaction_timeline_bytes", b'{"x":Infinity}'),
                             ("timeline_bytes", b'{"x":1e999}')):
            with self.subTest(key=key):
                changed = copy.deepcopy(evidence)
                changed[key] = payload
                if key == "timeline_bytes":
                    changed["timeline_sha256"] = sha(payload)
                with self.assertRaises(ValueError):
                    validate_stage_a_timeline_upstream(**changed)


if __name__ == "__main__":
    unittest.main()
