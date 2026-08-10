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
        candidates = document.get("candidate", [])
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
            self.assertEqual(
                candidate["revision_status"],
                "pinned_from_hugging_face_metadata_2026-08-11",
            )
            self.assertRegex(candidate["upstream_revision"], r"^[0-9a-f]{40}$")
            self.assertRegex(candidate["conversion_revision"], r"^[0-9a-f]{40}$")
            self.assertGreater(candidate["listed_primary_weight_bytes"], 0)
            self.assertRegex(candidate["listed_primary_weight_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(candidate["upstream_model_card_url"].startswith(
                "https://huggingface.co/"
            ))
            self.assertTrue(candidate["conversion_model_card_url"].startswith(
                "https://huggingface.co/"
            ))
            self.assertTrue(candidate["runtime_url"].startswith(
                "https://github.com/"
            ))


if __name__ == "__main__":
    unittest.main()
