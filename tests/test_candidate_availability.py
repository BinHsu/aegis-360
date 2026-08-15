import copy, hashlib, json
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aegis360.candidate_availability import build_candidate_availability, validate_candidate_availability
from aegis360.context_views import build_context_view_grid

class CandidateAvailabilityTests(unittest.TestCase):
    def setUp(self):
        self.grid=build_context_view_grid(source_id="fixture",start_seconds=10,duration_seconds=10)
        self.grid_sha=hashlib.sha256((json.dumps(self.grid,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
        self.config={"schema_version":"aegis360.candidate-availability-config.v1","config_id":"fixture-v1","reviewer_kind":"human","adapter_id":"fixture-review","candidates":[{"candidate_id":"context:cardinal:1","intervals":[{"start_seconds":12,"end_seconds":18}]}]}

    def test_closed_candidate_scoped_binding(self):
        value=build_candidate_availability(self.config,self.grid,config_sha256="a"*64,grid_sha256=self.grid_sha)
        validate_candidate_availability(value,self.grid,grid_sha256=self.grid_sha)
        self.assertEqual(value["candidates"][0]["candidate_id"],"context:cardinal:1")

    def test_unknown_candidate_or_out_of_window_fails(self):
        for mutation in ("candidate","window"):
            config=copy.deepcopy(self.config)
            if mutation=="candidate": config["candidates"][0]["candidate_id"]="invented"
            else: config["candidates"][0]["intervals"][0]["end_seconds"]=21
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                build_candidate_availability(config,self.grid,config_sha256="a"*64,grid_sha256=self.grid_sha)

    def test_unlisted_candidate_has_no_implicit_availability(self):
        value=build_candidate_availability(self.config,self.grid,config_sha256="a"*64,grid_sha256=self.grid_sha)
        self.assertNotIn("context:cardinal:3",{row["candidate_id"] for row in value["candidates"]})

if __name__=="__main__": unittest.main()
