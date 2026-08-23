from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.bounded_story_render import build_bounded_story_filter_graph
from aegis360.context_views import build_context_view_grid


class BoundedStoryRenderTests(unittest.TestCase):
    def test_renderer_exposes_same_contract_fixed_baseline_mode(self):
        source = (ROOT / "scripts/render_bounded_story_segment_plan.py").read_text()
        self.assertIn('parser.add_argument("--fixed-baseline", action="store_true")', source)
        self.assertIn('parser.add_argument("--allow-symbolic-baseline", action="store_true"', source)
        self.assertIn("not args.allow_symbolic_baseline", source)
        self.assertIn('mode = "fixed_baseline" if args.fixed_baseline else "planned"', source)
        self.assertIn('policy["initial_candidate_id"]', source)

    def test_filter_uses_absolute_video_segments_and_continuous_audio(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                       duration_seconds=30)
        plan = {"window": {"start_seconds": 10, "end_seconds": 20},
                "decisions": [
                    {"start_seconds": 10, "end_seconds": 15,
                     "selected_candidate_id": "context:cardinal:0"},
                    {"start_seconds": 15, "end_seconds": 20,
                     "selected_candidate_id": "context:cardinal:1"},
                ]}
        graph, video, audio = build_bounded_story_filter_graph(
            plan, grid, width=960, height=540,
        )
        self.assertIn("trim=start=10:end=15", graph)
        self.assertIn("yaw=90.0", graph)
        self.assertIn("concat=n=2:v=1:a=0", graph)
        self.assertIn("atrim=start=10:end=20", graph)
        self.assertEqual((video, audio), ("[vout]", "[aout]"))

    def test_gap_and_unknown_candidate_fail(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=0,
                                       duration_seconds=30)
        plan = {"window": {"start_seconds": 0, "end_seconds": 3},
                "decisions": [
                    {"start_seconds": 0, "end_seconds": 1,
                     "selected_candidate_id": "context:cardinal:0"},
                    {"start_seconds": 2, "end_seconds": 3,
                     "selected_candidate_id": "context:cardinal:1"}]}
        with self.assertRaises(ValueError):
            build_bounded_story_filter_graph(plan, grid, width=960, height=540)
        plan["decisions"] = [{"start_seconds": 0, "end_seconds": 3,
                              "selected_candidate_id": "invented"}]
        with self.assertRaises(ValueError):
            build_bounded_story_filter_graph(plan, grid, width=960, height=540)


if __name__ == "__main__":
    unittest.main()
