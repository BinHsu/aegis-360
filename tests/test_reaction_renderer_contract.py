import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.context_views import build_context_view_grid
from aegis360.candidate_availability import build_candidate_availability
from aegis360.editorial_roles import build_editorial_roles
from aegis360.reaction_plan import build_reaction_plan
from aegis360.reaction_view_gain import build_reaction_view_gain


SPEC = importlib.util.spec_from_file_location(
    "render_reaction_shot_plan", ROOT / "scripts" / "render_reaction_shot_plan.py"
)
RENDERER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(RENDERER)


class ReactionRendererContractTests(unittest.TestCase):
    def test_nonzero_window_trims_audio_at_absolute_times_and_uses_roles_for_primary(self):
        grid = build_context_view_grid(source_id="fixture", start_seconds=30, duration_seconds=8)
        grid_payload = json.dumps(grid, allow_nan=False, indent=2, sort_keys=True) + "\n"
        grid_sha = hashlib.sha256(grid_payload.encode()).hexdigest()
        roles = build_editorial_roles(
            grid, grid_sha256=grid_sha, primary_candidate_id="context:cardinal:3",
            reaction_candidate_id="context:cardinal:1", adapter_id="owner-fixture",
        )
        reactions = {
            "schema_version": "aegis360.reaction-intervals.v1", "source_id": "fixture",
            "source_sound_event_schema": "aegis360.apple-sound-events.v1",
            "policy": {"applause_threshold": .5, "clapping_threshold": .5,
                       "minimum_supporting_windows": 2,
                       "status": "poc_hypothesis_not_editorial_ground_truth"},
            "intervals": [], "privacy": {}, "limitations": [],
        }
        availability_config = {
            "schema_version": "aegis360.candidate-availability-config.v1",
            "config_id": "fixture", "reviewer_kind": "human", "adapter_id": "owner-fixture",
            "candidates": [{"candidate_id": "context:cardinal:1", "intervals": []}],
        }
        availability = build_candidate_availability(
            availability_config, grid, config_sha256="1" * 64, grid_sha256=grid_sha
        )
        roles_sha=hashlib.sha256((json.dumps(roles,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
        reactions_sha=hashlib.sha256((json.dumps(reactions,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
        gain_config={"schema_version":"aegis360.reaction-view-gain-config.v2","config_id":"fixture","reviewer_kind":"human","adapter_id":"owner-fixture","model_id":None,"model_sha256":None,"decisions":[]}
        gain=build_reaction_view_gain(gain_config,grid,roles,reactions,config_sha256="2"*64,grid_sha256=grid_sha,roles_sha256=roles_sha,reactions_sha256=reactions_sha)
        plan = build_reaction_plan(
            grid, roles, reactions, availability, gain, grid_sha256=grid_sha
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {name: root / f"{name}.json" for name in (
                "grid", "roles", "reactions", "availability", "gain", "plan"
            )}
            paths["grid"].write_text(grid_payload)
            for name, document in (("roles", roles), ("reactions", reactions),
                                   ("availability", availability), ("gain", gain), ("plan", plan)):
                paths[name].write_text(json.dumps(document))
            video = root / "input.mp4"; video.touch()
            output = root / "output"
            argv = ["render_reaction_shot_plan.py", str(video), str(paths["grid"]),
                    str(paths["roles"]), str(paths["reactions"]),
                    str(paths["availability"]), str(paths["gain"]), str(paths["plan"]), str(output),
                    "--mode", "primary-only"]
            with mock.patch.object(sys, "argv", argv), mock.patch.object(
                RENDERER.subprocess, "run"
            ) as run:
                self.assertEqual(RENDERER.main(), 0)
            command = run.call_args.args[0]
            filters = command[command.index("-filter_complex") + 1]
            self.assertIn("trim=start=30.0:end=38.0", filters)
            self.assertIn("yaw=-90.0", filters)
            self.assertIn("[0:a:0]atrim=start=30.0:end=38.0,asetpts=PTS-STARTPTS[audio]", filters)
            self.assertEqual(command[command.index("-map") + 1], "[video]")
            self.assertIn("[audio]", command)


if __name__ == "__main__":
    unittest.main()
