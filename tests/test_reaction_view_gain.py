import hashlib, json
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aegis360.context_views import build_context_view_grid
from aegis360.editorial_roles import build_editorial_roles
from aegis360.reaction_view_gain import build_reaction_view_gain, validate_reaction_view_gain

class ReactionViewGainTests(unittest.TestCase):
    def setUp(self):
        self.grid=build_context_view_grid(source_id="fixture",start_seconds=0,duration_seconds=20)
        self.grid_sha=hashlib.sha256((json.dumps(self.grid,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
        self.roles=build_editorial_roles(self.grid,grid_sha256=self.grid_sha,primary_candidate_id="context:cardinal:3",reaction_candidate_id="context:cardinal:1",adapter_id="fixture")
        self.reactions={"schema_version":"aegis360.reaction-intervals.v1","source_id":"fixture","source_sound_event_schema":"aegis360.apple-sound-events.v1","policy":{"applause_threshold":.5,"clapping_threshold":.5,"minimum_supporting_windows":2,"status":"poc_hypothesis_not_editorial_ground_truth"},"intervals":[{"start_seconds":4,"end_seconds":8,"supporting_window_count":3,"peak_applause_confidence":.8,"peak_clapping_confidence":.9}],"privacy":{},"limitations":[]}
        self.roles_sha=hashlib.sha256((json.dumps(self.roles,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
        self.reactions_sha=hashlib.sha256((json.dumps(self.reactions,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
    def build(self, decisions):
        config={"schema_version":"aegis360.reaction-view-gain-config.v2","config_id":"fixture","reviewer_kind":"human","adapter_id":"fixture-review","model_id":None,"model_sha256":None,"decisions":decisions}
        return build_reaction_view_gain(config,self.grid,self.roles,self.reactions,config_sha256="a"*64,grid_sha256=self.grid_sha,roles_sha256=self.roles_sha,reactions_sha256=self.reactions_sha)
    def test_promote_is_bound_to_role_owned_pair_and_exact_event(self):
        value=self.build([{"reaction_start_seconds":4,"reaction_end_seconds":8,"decision":"promote"}])
        validate_reaction_view_gain(value,self.grid,self.roles,self.reactions,grid_sha256=self.grid_sha,roles_sha256=self.roles_sha,reactions_sha256=self.reactions_sha)
        self.assertEqual(value["decisions"][0]["current_candidate_id"],"context:cardinal:3")
        self.assertEqual(value["decisions"][0]["proposed_candidate_id"],"context:cardinal:1")
    def test_unreviewed_is_explicit_fail_closed_default(self):
        value=self.build([])
        self.assertEqual(value["decisions"],[]); self.assertEqual(value["default_decision"],"abstain")
    def test_unknown_duplicate_or_extra_fields_fail(self):
        for decisions in (
            [{"reaction_start_seconds":5,"reaction_end_seconds":8,"decision":"promote"}],
            [{"reaction_start_seconds":4,"reaction_end_seconds":8,"decision":"promote"}]*2,
            [{"reaction_start_seconds":4,"reaction_end_seconds":8,"decision":"better","reason":"looks good"}],
        ):
            with self.assertRaises(ValueError): self.build(decisions)
    def test_tampered_role_or_binding_fails(self):
        value=self.build([{"reaction_start_seconds":4,"reaction_end_seconds":8,"decision":"promote"}])
        value["decisions"][0]["proposed_candidate_id"]="context:cardinal:2"
        with self.assertRaises(ValueError): validate_reaction_view_gain(value,self.grid,self.roles,self.reactions,grid_sha256=self.grid_sha,roles_sha256=self.roles_sha,reactions_sha256=self.reactions_sha)
    def test_local_model_requires_exact_provenance_and_human_forbids_it(self):
        base={"schema_version":"aegis360.reaction-view-gain-config.v2","config_id":"fixture","reviewer_kind":"local_vlm","adapter_id":"fixture-review","model_id":"smolvlm2-2.2b","model_sha256":"b"*64,"decisions":[]}
        value=build_reaction_view_gain(base,self.grid,self.roles,self.reactions,config_sha256="a"*64,grid_sha256=self.grid_sha,roles_sha256=self.roles_sha,reactions_sha256=self.reactions_sha)
        self.assertEqual(value["provenance"]["model_sha256"],"b"*64)
        for mutation in (lambda c:c.__setitem__("model_sha256",None),lambda c:(c.__setitem__("reviewer_kind","human"))):
            broken=dict(base); mutation(broken)
            with self.assertRaises(ValueError): build_reaction_view_gain(broken,self.grid,self.roles,self.reactions,config_sha256="a"*64,grid_sha256=self.grid_sha,roles_sha256=self.roles_sha,reactions_sha256=self.reactions_sha)

if __name__=="__main__": unittest.main()
