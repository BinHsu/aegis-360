import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_probe_sentinels import _OutsideSentinelSnapshot


class OutsideSentinelSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "outside"
        self.root.mkdir(mode=0o700)
        (self.root / "outside-existing").write_bytes(b"outside-existing-sentinel-v1")
        (self.root / "outside-existing").chmod(0o600)

    def test_unchanged_tree_and_absent_names_revalidate(self):
        with _OutsideSentinelSnapshot(self.root) as proof:
            self.assertEqual(proof.create_path, self.root / "outside-create")
            self.assertEqual(proof.rename_destination, self.root / "rename-dest")
            proof.revalidate()
        self.assertTrue((self.root / "outside-existing").exists())
        with self.assertRaisesRegex(ValueError, "closed"):
            proof.revalidate()

    def test_create_overwrite_truncate_rename_unlink_are_detected(self):
        for operation in ("create", "overwrite", "truncate", "rename", "unlink"):
            with self.subTest(operation=operation):
                with _OutsideSentinelSnapshot(self.root) as proof:
                    existing = proof.existing_path
                    if operation == "create":
                        proof.create_path.write_bytes(b"created")
                    elif operation == "overwrite":
                        existing.write_bytes(b"changed")
                    elif operation == "truncate":
                        existing.write_bytes(b"")
                    elif operation == "rename":
                        existing.rename(proof.rename_destination)
                    else:
                        existing.unlink()
                    with self.assertRaises(ValueError): proof.revalidate()
                for path in self.root.iterdir(): path.unlink()
                existing.write_bytes(b"outside-existing-sentinel-v1")
                existing.chmod(0o600)

    def test_name_replacement_and_mode_change_are_detected(self):
        with _OutsideSentinelSnapshot(self.root) as proof:
            original = self.root / "outside-existing"
            original.rename(self.root / "old-existing")
            original.write_bytes(b"outside-existing-sentinel-v1")
            original.chmod(0o600)
            with self.assertRaises(ValueError): proof.revalidate()
        (self.root / "old-existing").unlink()
        with _OutsideSentinelSnapshot(self.root) as proof:
            self.root.chmod(0o755)
            with self.assertRaises(ValueError): proof.revalidate()


if __name__ == "__main__": unittest.main()
