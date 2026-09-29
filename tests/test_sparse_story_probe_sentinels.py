import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_probe_sentinels import (
    _OutsideSentinelSnapshot, _OwnedOutsideSentinel,
    _ReadDenialSentinel, _ScratchProbeSnapshot, _OwnedScratchProbeFiles,
)


class OwnedOutsideSentinelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()

    def test_exact_cleanup_requires_reaped_child(self):
        owner = _OwnedOutsideSentinel(self.parent)
        owner.revalidate()
        self.assertTrue(owner.path.exists())
        owner.finish_after_reap(0)
        self.assertFalse(owner.root.exists())
        with self.assertRaisesRegex(ValueError, "closed"):
            owner.revalidate()
        unreaped = _OwnedOutsideSentinel(self.parent)
        with self.assertRaisesRegex(ValueError, "before reap"):
            unreaped.finish_after_reap(None)
        self.assertTrue(unreaped.root.exists())

    def test_changed_outside_file_is_preserved(self):
        owner = _OwnedOutsideSentinel(self.parent)
        owner.path.write_bytes(b"changed")
        with self.assertRaises(ValueError): owner.finish_after_reap(0)
        self.assertEqual(owner.path.read_bytes(), b"changed")


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


class ReadDenialSentinelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / "forbidden-read"
        self.path.write_bytes(b"known-existing-v1")
        self.path.chmod(0o600)

    def test_unchanged_existing_file_revalidates(self):
        with _ReadDenialSentinel(self.path) as proof:
            proof.revalidate()
        with self.assertRaisesRegex(ValueError, "closed"): proof.revalidate()

    def test_content_replacement_and_unlink_reject(self):
        with _ReadDenialSentinel(self.path) as proof:
            self.path.write_bytes(b"changed-content")
            with self.assertRaises(ValueError): proof.revalidate()
        self.path.write_bytes(b"known-existing-v1")
        with _ReadDenialSentinel(self.path) as proof:
            old = self.path.with_name("old-forbidden-read")
            self.path.rename(old)
            self.path.write_bytes(b"known-existing-v1")
            self.path.chmod(0o600)
            with self.assertRaises(ValueError): proof.revalidate()
        old.unlink()
        with _ReadDenialSentinel(self.path) as proof:
            self.path.unlink()
            with self.assertRaises(OSError): proof.revalidate()

    def test_symlink_and_group_writable_file_reject(self):
        alias = self.path.with_name("alias")
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError): _ReadDenialSentinel(alias)
        self.path.chmod(0o620)
        with self.assertRaises(ValueError): _ReadDenialSentinel(self.path)

    def test_repository_and_protocol_files_are_retained_without_mutation(self):
        for relative in ("src/aegis360/sparse_story_batch_policy.py",
                "docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md"):
            with self.subTest(relative=relative), _ReadDenialSentinel(ROOT / relative) as proof:
                proof.revalidate()


class ScratchProbeSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "scratch"
        self.root.mkdir(mode=0o700)
        self.home, self.tmpdir = self.root / "home", self.root / "tmp"
        self.home.mkdir(mode=0o700)
        self.tmpdir.mkdir(mode=0o700)
        (self.root / "rename-source").write_bytes(b"rename-source-v1")
        (self.root / "rename-source").chmod(0o600)

    def test_exact_pre_and_post_probe_state(self):
        with _ScratchProbeSnapshot(self.root, self.home, self.tmpdir) as proof:
            proof.prevalidate()
            self.assertEqual(proof.source_path, self.root / "rename-source")
            proof.scratch_write_path.write_bytes(b"scratch-write-sentinel-v1")
            proof.scratch_write_path.chmod(0o600)
            proof.postvalidate()
        with self.assertRaisesRegex(ValueError, "closed"): proof.prevalidate()

    def test_source_mutation_and_fork_marker_reject(self):
        with _ScratchProbeSnapshot(self.root, self.home, self.tmpdir) as proof:
            proof.source_path.write_bytes(b"changed")
            with self.assertRaises(ValueError): proof.prevalidate()
        (self.root / "rename-source").write_bytes(b"rename-source-v1")
        with _ScratchProbeSnapshot(self.root, self.home, self.tmpdir) as proof:
            proof.scratch_write_path.write_bytes(b"scratch-write-sentinel-v1")
            proof.fork_marker_path.write_bytes(b"forked")
            with self.assertRaises(ValueError): proof.postvalidate()

    def test_private_directory_replacement_rejects(self):
        with _ScratchProbeSnapshot(self.root, self.home, self.tmpdir) as proof:
            self.home.rename(self.root / "old-home")
            self.home.mkdir(mode=0o700)
            with self.assertRaises(ValueError): proof.prevalidate()


class OwnedScratchProbeFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "scratch"
        self.root.mkdir(mode=0o700)
        self.home, self.tmpdir = self.root / "home", self.root / "tmp"
        self.home.mkdir(mode=0o700)
        self.tmpdir.mkdir(mode=0o700)

    def test_exact_files_clean_after_reap(self):
        owner = _OwnedScratchProbeFiles(self.root, self.home, self.tmpdir)
        owner.snapshot.scratch_write_path.write_bytes(b"scratch-write-sentinel-v1")
        owner.snapshot.scratch_write_path.chmod(0o600)
        owner.finish_after_reap(0)
        self.assertEqual(set(self.root.iterdir()), {self.home, self.tmpdir})

    def test_unreaped_or_changed_write_is_preserved(self):
        owner = _OwnedScratchProbeFiles(self.root, self.home, self.tmpdir)
        with self.assertRaisesRegex(ValueError, "before reap"):
            owner.finish_after_reap(None)
        self.assertTrue(owner.snapshot.source_path.exists())
        owner.snapshot.source_path.unlink()
        owner = _OwnedScratchProbeFiles(self.root, self.home, self.tmpdir)
        owner.snapshot.scratch_write_path.write_bytes(b"changed")
        with self.assertRaises(ValueError): owner.finish_after_reap(0)
        self.assertEqual(owner.snapshot.scratch_write_path.read_bytes(), b"changed")

    def test_replacement_after_snapshot_close_is_preserved(self):
        owner = _OwnedScratchProbeFiles(self.root, self.home, self.tmpdir)
        write = owner.snapshot.scratch_write_path
        write.write_bytes(b"scratch-write-sentinel-v1")
        write.chmod(0o600)
        original_close = owner.snapshot.close

        def replace_after_close():
            original_close()
            write.unlink()
            write.write_bytes(b"replacement")

        owner.snapshot.close = replace_after_close
        with self.assertRaisesRegex(ValueError, "cleanup target changed"):
            owner.finish_after_reap(0)
        self.assertEqual(write.read_bytes(), b"replacement")
        self.assertTrue(owner.snapshot.source_path.exists())


if __name__ == "__main__": unittest.main()
