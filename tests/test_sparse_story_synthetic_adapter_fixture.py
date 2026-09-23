import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_probe_transcript import (  # noqa: E402
    OPERATIONS, parse_isolation_probe_transcript,
)


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64",
                     "native adapter fixture is Darwin arm64 only")
class SyntheticAdapterFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name).resolve()
        cls.runtime = cls.base / "runtime"
        (cls.runtime / "bin").mkdir(parents=True)
        cls.executable = cls.runtime / "bin" / "aegis-synthetic-adapter"
        subprocess.run(["/usr/bin/xcrun", "--sdk", "macosx", "clang", "-std=c11",
            "-Os", "-Wall", "-Wextra", "-Werror", "-Wpedantic",
            "-fstack-protector-strong", "-arch", "arm64",
            "-mmacosx-version-min=15.0", str(ROOT / "tools" /
                "sparse_story_synthetic_adapter_fixture.c"), "-o", str(cls.executable)],
            check=True, capture_output=True)
        subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-",
                        "--timestamp=none", str(cls.executable)],
                       check=True, capture_output=True)
        cls.executable.chmod(0o555)
        (cls.runtime / "bin").chmod(0o555)
        cls.runtime.chmod(0o555)

    @classmethod
    def tearDownClass(cls):
        for path in (cls.executable, cls.runtime / "bin", cls.runtime):
            if path.exists(): path.chmod(0o700)
        cls.temp.cleanup()

    def test_same_retained_entrypoint_has_closed_probe_and_case_modes(self):
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
            case = subprocess.run([str(self.executable), "--aegis-synthetic-case",
                                   "argv_literal", "--"], capture_output=True, timeout=5)
            self.assertEqual((case.returncode, case.stdout, case.stderr),
                (0, b"aegis-synthetic-argv-literal-v1\n", b""))
            for suffix in ([], ["--aegis-synthetic-case", "bad", "--"],
                           ["--aegis-isolation-probe"],
                           ["--aegis-synthetic-case", "argv_literal", "--", "extra"]):
                wrong = subprocess.run([str(self.executable), *suffix],
                                       capture_output=True, timeout=5)
                self.assertEqual((wrong.returncode, wrong.stdout, wrong.stderr),
                                 (64, b"", b""))
            self.assertEqual(proof.manifest(), manifest)

    def test_raw_probe_rows_are_exact_order_without_claiming_confinement(self):
        manifest = _observe_asset_manifest_shape(root=self.runtime, asset_kind="runtime",
            entrypoint="bin/aegis-synthetic-adapter")
        with tempfile.TemporaryDirectory(dir=self.base) as temporary:
            root = Path(temporary)
            paths = [root / name for name in ("bundle", "model", "prompt", "scratch",
                "repo", "protocol", "neighbor", "result", "outside-create",
                "outside-existing", "rename-source", "rename-dest", "fork-marker")]
            for path in paths[:3]: path.write_bytes(path.name.encode())
            paths[9].write_bytes(b"outside-existing")
            paths[10].write_bytes(b"rename-source")
            argv = [str(self.executable), "--aegis-isolation-probe",
                *map(str, paths[:13]), "0", "0", str(root / "absent.sock"),
                str(root / "absent-executable"), str(root / "exec-marker")]
            self.assertEqual(len(argv), 20)
            with validate_asset_tree(manifest=manifest, root=self.runtime) as proof:
                result = subprocess.run(argv, capture_output=True, timeout=5)
                self.assertEqual((result.returncode, result.stderr), (0, b""))
                rows = parse_isolation_probe_transcript(result.stdout)
                self.assertEqual(tuple(row.operation for row in rows), OPERATIONS)
                self.assertEqual(rows[0].data, b"bundle")
                self.assertEqual(rows[1].data, b"model")
                self.assertEqual(rows[2].data, b"prompt")
                self.assertEqual(proof.manifest(), manifest)


if __name__ == "__main__": unittest.main()
