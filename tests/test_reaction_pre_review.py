from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from aegis360.reaction_pre_review import evaluate_reaction_preview

class ReactionPreReviewTests(unittest.TestCase):
    def fixture(self,promote=True):
        grid={"source_id":"fixture","window":{"start_seconds":10.0,"duration_seconds":10.0},"candidates":[{"candidate_id":"primary","yaw_degrees":0.0,"pitch_degrees":0.0,"horizontal_fov_degrees":110.0},{"candidate_id":"reaction","yaw_degrees":45.0,"pitch_degrees":0.0,"horizontal_fov_degrees":110.0}]}
        roles={"assignments":[{"role":"primary_performance","candidate_id":"primary"},{"role":"audience_reaction","candidate_id":"reaction"}]}
        segments=[{"start_seconds":10.0,"end_seconds":14.0,"candidate_id":"primary","reason":"primary_performance_default"},{"start_seconds":14.0,"end_seconds":20.0,"candidate_id":"reaction","reason":"reaction_event_candidate_available_and_gain_promoted"}] if promote else [{"start_seconds":10.0,"end_seconds":20.0,"candidate_id":"primary","reason":"primary_performance_default"}]
        plan={"segments":segments}; primary=[{"start_seconds":10.0,"end_seconds":20.0,"candidate_id":"primary","reason":"primary_only_baseline"}]
        common={"source_id":"fixture","context_view_grid_sha256":"g","reaction_shot_plan_sha256":"p","encoder":{"video":"h264","fps":15}}
        primary_trace={**common,"mode":"primary-only","segments":primary}; planned_trace={**common,"mode":"planned","segments":segments}
        probe={"streams":[{"codec_type":"video","nb_read_frames":"150"},{"codec_type":"audio","nb_read_frames":"400"}]}
        return grid,roles,plan,primary_trace,planned_trace,probe
    def evaluate(self,promote=True,**overrides):
        grid,roles,plan,pt,dt,probe=self.fixture(promote)
        values={"primary_video_hash":"a","planned_video_hash":"b" if promote else "a","primary_audio_hash":"c","planned_audio_hash":"c"}; values.update(overrides)
        return evaluate_reaction_preview(grid,roles,plan,pt,dt,probe,probe,**values)
    def test_promote_requires_video_difference_pose_duration_and_equal_audio(self):
        self.assertTrue(self.evaluate(True)["passed"])
        self.assertFalse(self.evaluate(True,planned_video_hash="a")["passed"])
        self.assertFalse(self.evaluate(True,planned_audio_hash="d")["passed"])
    def test_abstain_requires_decoded_identity(self):
        result=self.evaluate(False); self.assertTrue(result["passed"]); self.assertEqual(result["plan_mode"],"abstain")
        self.assertFalse(self.evaluate(False,planned_video_hash="b")["passed"])
    def test_trace_or_probe_difference_fails(self):
        grid,roles,plan,pt,dt,probe=self.fixture(True); dt["segments"]=[]
        result=evaluate_reaction_preview(grid,roles,plan,pt,dt,probe,probe,primary_video_hash="a",planned_video_hash="b",primary_audio_hash="c",planned_audio_hash="c")
        self.assertFalse(result["passed"])
        different={"streams":[]}
        result=evaluate_reaction_preview(grid,roles,plan,pt,{**pt,"mode":"planned","segments":plan["segments"]},probe,different,primary_video_hash="a",planned_video_hash="b",primary_audio_hash="c",planned_audio_hash="c")
        self.assertFalse(result["passed"])

if __name__=="__main__": unittest.main()
