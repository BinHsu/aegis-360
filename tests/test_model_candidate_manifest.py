from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ModelCandidateManifestTests(unittest.TestCase):
    def test_proposed_candidates_cannot_claim_acquisition_or_fake_checksum(self):
        document = tomllib.loads(
            (ROOT / "model-manifests/candidates.toml").read_text()
        )
        self.assertIs(document["implicit_downloads_allowed"], False)
        candidates = document["candidate"]
        self.assertGreater(len(candidates), 0)
        for candidate in candidates:
            self.assertEqual(candidate["status"], "proposed_not_acquired")
            self.assertIs(candidate["acquisition_authorized"], False)
            self.assertEqual(
                candidate["sha256_status"],
                "must_be_measured_after_explicit_acquisition",
            )
            self.assertEqual(
                candidate["byte_size_status"],
                "must_be_measured_after_explicit_acquisition",
            )
            self.assertNotIn("sha256", candidate)
            path = Path(candidate["proposed_relative_path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertTrue(
                candidate["release_asset_url"].startswith(
                    "https://github.com/Megvii-BaseDetection/YOLOX/releases/"
                )
            )


if __name__ == "__main__":
    unittest.main()
