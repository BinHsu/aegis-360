import json
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aegis360.local_reaction_gain_schema import local_reaction_gain_json_schema

class LocalReactionGainContractTests(unittest.TestCase):
    def test_schema_is_decision_only_and_closed(self):
        schema=local_reaction_gain_json_schema()
        self.assertEqual(set(schema["properties"]),{"decision"})
        self.assertEqual(schema["properties"]["decision"]["enum"],["promote","abstain"])
        self.assertFalse(schema["additionalProperties"])
    def test_runner_is_bounded_offline_and_provenance_bound(self):
        text=(ROOT/"scripts"/"run_mlx_vlm_reaction_gain.py").read_text()
        for required in ("maximum-frames","expected-model-sha256","temperature=0","build_json_schema_logits_processor","build_reaction_view_gain","audio_provided\":False","refusing to overwrite"):
            self.assertIn(required,text)
        for forbidden in ("requests.","urllib","http://","https://"):
            self.assertNotIn(forbidden,text)

if __name__=="__main__": unittest.main()
