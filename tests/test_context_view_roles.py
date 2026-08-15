import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.context_views import build_context_view_grid, validate_context_view_grid
from aegis360.editorial_roles import build_editorial_roles, validate_editorial_roles


class ContextViewRoleTests(unittest.TestCase):
    def setUp(self):
        self.grid = build_context_view_grid(source_id="fixture", start_seconds=0, duration_seconds=10)
        payload = json.dumps(self.grid, indent=2, sort_keys=True).encode() + b"\n"
        self.checksum = hashlib.sha256(payload).hexdigest()

    def test_grid_is_deterministic_and_path_free(self):
        validate_context_view_grid(self.grid)
        self.assertEqual([item["yaw_degrees"] for item in self.grid["candidates"]], [0, 90, -180, -90])
        self.assertFalse(self.grid["privacy"]["contains_source_path"])
        self.assertNotIn("/Users/", json.dumps(self.grid))

    def test_roles_reference_geometry_without_carrying_it(self):
        roles = build_editorial_roles(
            self.grid, grid_sha256=self.checksum,
            primary_candidate_id="context:cardinal:3",
            reaction_candidate_id="context:cardinal:1",
            adapter_id="owner-gaudeamus-v1",
        )
        validate_editorial_roles(roles, self.grid, grid_sha256=self.checksum)
        self.assertNotIn("yaw", json.dumps(roles))
        self.assertEqual(sum(item["role"] == "primary_performance" for item in roles["assignments"]), 1)
        self.assertEqual(sum(item["role"] == "audience_reaction" for item in roles["assignments"]), 1)

    def test_roles_fail_on_invented_candidate_or_geometry_change(self):
        with self.assertRaises(ValueError):
            build_editorial_roles(
                self.grid, grid_sha256=self.checksum,
                primary_candidate_id="invented", reaction_candidate_id="context:cardinal:1",
                adapter_id="fixture",
            )
        changed = copy.deepcopy(self.grid)
        changed["candidates"][0]["yaw_degrees"] = 5
        with self.assertRaises(ValueError):
            validate_context_view_grid(changed)


if __name__ == "__main__":
    unittest.main()
