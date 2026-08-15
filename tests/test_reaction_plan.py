import hashlib, json
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from aegis360.context_views import build_context_view_grid
from aegis360.candidate_availability import build_candidate_availability
from aegis360.editorial_roles import build_editorial_roles
from aegis360.reaction_plan import build_reaction_plan, validate_reaction_plan

class ReactionPlanTests(unittest.TestCase):
    def availability(self, grid, checksum, candidate_id="context:cardinal:1", intervals=None):
        config = {"schema_version":"aegis360.candidate-availability-config.v1",
                  "config_id":"fixture","reviewer_kind":"human","adapter_id":"owner-fixture",
                  "candidates":[{"candidate_id":candidate_id,"intervals":intervals or []}]}
        return build_candidate_availability(config, grid, config_sha256="1" * 64,
                                            grid_sha256=checksum)

    def test_intersects_events_with_availability_and_returns_primary(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=20)
        checksum = hashlib.sha256((json.dumps(grid, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        roles = build_editorial_roles(grid, grid_sha256=checksum, primary_candidate_id="context:cardinal:3", reaction_candidate_id="context:cardinal:1", adapter_id="owner-fixture")
        reactions = {"schema_version":"aegis360.reaction-intervals.v1","source_id":"fixture","source_sound_event_schema":"aegis360.apple-sound-events.v1","policy":{"applause_threshold":.5,"clapping_threshold":.5,"minimum_supporting_windows":2,"status":"poc_hypothesis_not_editorial_ground_truth"},"intervals":[{"start_seconds":4,"end_seconds":8,"supporting_window_count":3,"peak_applause_confidence":.8,"peak_clapping_confidence":.9}],"privacy":{},"limitations":[]}
        availability = self.availability(grid, checksum, intervals=[{"start_seconds":2,"end_seconds":6}])
        result = build_reaction_plan(grid, roles, reactions, availability, grid_sha256=checksum)
        validate_reaction_plan(result, grid, grid_sha256=checksum)
        self.assertEqual([(row["start_seconds"],row["end_seconds"],row["candidate_id"]) for row in result["segments"]],[(0,4,"context:cardinal:3"),(4,6,"context:cardinal:1"),(6,20,"context:cardinal:3")])
        self.assertEqual(result["transition_policy"], "hard_cut_only_when_reaction_candidate_is_available_v3")

        broken = json.loads(json.dumps(result)); broken["segments"][1]["start_seconds"] = 5
        with self.assertRaises(ValueError): validate_reaction_plan(broken, grid, grid_sha256=checksum)

        validate_reaction_plan(result, grid, grid_sha256=checksum, roles=roles,
                               reactions=reactions, availability=availability)
        wrong = json.loads(json.dumps(result)); wrong["inputs"]["editorial_roles_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_reaction_plan(wrong, grid, grid_sha256=checksum, roles=roles,
                                   reactions=reactions, availability=availability)

    def test_inputs_are_closed_and_all_sha256_values_are_lowercase_hex(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=20)
        checksum = hashlib.sha256((json.dumps(grid, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        roles = build_editorial_roles(grid, grid_sha256=checksum, primary_candidate_id="context:cardinal:3", reaction_candidate_id="context:cardinal:1", adapter_id="owner-fixture")
        reactions = {"schema_version":"aegis360.reaction-intervals.v1","source_id":"fixture","source_sound_event_schema":"aegis360.apple-sound-events.v1","policy":{"applause_threshold":.5,"clapping_threshold":.5,"minimum_supporting_windows":2,"status":"poc_hypothesis_not_editorial_ground_truth"},"intervals":[],"privacy":{},"limitations":[]}
        availability = self.availability(grid, checksum)
        result = build_reaction_plan(grid, roles, reactions, availability, grid_sha256=checksum)
        for mutation in (
            lambda inputs: inputs.update({"extra": "0" * 64}),
            lambda inputs: inputs.__setitem__("editorial_roles_sha256", "A" * 64),
        ):
            broken = json.loads(json.dumps(result)); mutation(broken["inputs"])
            with self.assertRaises(ValueError): validate_reaction_plan(broken, grid, grid_sha256=checksum)

    def test_event_starting_before_live_scene_is_not_joined_mid_reaction(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=20)
        checksum = hashlib.sha256((json.dumps(grid, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        roles = build_editorial_roles(grid, grid_sha256=checksum, primary_candidate_id="context:cardinal:3", reaction_candidate_id="context:cardinal:1", adapter_id="owner-fixture")
        reactions = {"schema_version":"aegis360.reaction-intervals.v1","source_id":"fixture","source_sound_event_schema":"aegis360.apple-sound-events.v1","policy":{"applause_threshold":.5,"clapping_threshold":.5,"minimum_supporting_windows":2,"status":"poc_hypothesis_not_editorial_ground_truth"},"intervals":[{"start_seconds":2,"end_seconds":8,"supporting_window_count":3,"peak_applause_confidence":.8,"peak_clapping_confidence":.9}],"privacy":{},"limitations":[]}
        availability = self.availability(grid, checksum, intervals=[{"start_seconds":4,"end_seconds":10}])
        result = build_reaction_plan(grid, roles, reactions, availability, grid_sha256=checksum)
        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(result["segments"][0]["candidate_id"], "context:cardinal:3")

    def test_missing_reaction_candidate_availability_fails_closed_to_primary(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=20)
        checksum = hashlib.sha256((json.dumps(grid, indent=2, sort_keys=True) + "\n").encode()).hexdigest()
        roles = build_editorial_roles(grid, grid_sha256=checksum, primary_candidate_id="context:cardinal:3", reaction_candidate_id="context:cardinal:1", adapter_id="owner-fixture")
        reactions = {"schema_version":"aegis360.reaction-intervals.v1","source_id":"fixture","source_sound_event_schema":"aegis360.apple-sound-events.v1","policy":{"applause_threshold":.5,"clapping_threshold":.5,"minimum_supporting_windows":2,"status":"poc_hypothesis_not_editorial_ground_truth"},"intervals":[{"start_seconds":4,"end_seconds":8,"supporting_window_count":3,"peak_applause_confidence":.8,"peak_clapping_confidence":.9}],"privacy":{},"limitations":[]}
        availability = self.availability(grid, checksum, candidate_id="context:cardinal:2",
                                         intervals=[{"start_seconds":2,"end_seconds":10}])
        result = build_reaction_plan(grid, roles, reactions, availability, grid_sha256=checksum)
        self.assertEqual([segment["candidate_id"] for segment in result["segments"]],
                         ["context:cardinal:3"])

if __name__ == "__main__": unittest.main()
