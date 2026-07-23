import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_duration_ladder import load_toml, validate  # noqa: E402


class DurationLadderContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_toml(ROOT / "benchmarks" / "manifest.toml")
        self.ladder = load_toml(ROOT / "benchmarks" / "duration-ladder.toml")

    def test_repository_contract_is_valid(self):
        self.assertEqual([], validate(self.manifest, self.ladder))

    def test_rejects_duration_longer_than_asset(self):
        invalid = copy.deepcopy(self.ladder)
        invalid["asset"][0]["enabled_duration_seconds"].append(300)
        errors = validate(self.manifest, invalid)
        self.assertTrue(any("bellpuig_onboard_360" in error for error in errors))

    def test_requires_all_three_comparable_outputs(self):
        invalid = copy.deepcopy(self.ladder)
        invalid["required_outputs"].remove("debug-overlay")
        self.assertTrue(validate(self.manifest, invalid))

    def test_requires_debug_to_share_auto_camera_path(self):
        invalid = copy.deepcopy(self.ladder)
        invalid["debug_uses_auto_path"] = False
        self.assertTrue(validate(self.manifest, invalid))


if __name__ == "__main__":
    unittest.main()
