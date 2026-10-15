"""Native fixture transport for three coordinator-owned zero-argv modes."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_semantics import select_failure_reason  # noqa: E402


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64",
                     "native synthetic fixture requires Darwin arm64")
class CoordinatorFixtureModesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.executable = Path(cls.temporary.name) / "aegis-synthetic-adapter"
        subprocess.run(["/usr/bin/xcrun", "--sdk", "macosx", "clang", "-std=c11",
            "-Os", "-Wall", "-Wextra", "-Werror", "-Wpedantic",
            "-fstack-protector-strong", "-arch", "arm64",
            "-mmacosx-version-min=15.0",
            str(ROOT / "tools/sparse_story_synthetic_adapter_fixture.c"),
            "-o", str(cls.executable)], check=True, capture_output=True)
        subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-",
                        "--timestamp=none", str(cls.executable)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_case(self, case_id, *suffix):
        return subprocess.run([str(self.executable), "--aegis-synthetic-case",
            case_id, "--", *suffix], capture_output=True, timeout=5)

    def test_three_modes_have_native_closed_output_without_self_attestation(self):
        baseline = self.run_case("fd_hygiene")
        self.assertEqual((baseline.returncode, baseline.stderr), (0, b""))
        for case_id in ("replacement_race", "single_invocation", "receipt_rebuild"):
            with self.subTest(case_id=case_id):
                observed = self.run_case(case_id)
                self.assertEqual((observed.returncode, observed.stderr), (0, b""))
                self.assertEqual(observed.stdout, baseline.stdout)
                self.assertIsNone(select_failure_reason(missing_anchor=False,
                    invocation_failed=False, raw_output=observed.stdout))
                for forbidden in (b"receipt_sha256", b"invocation_count",
                                  b"replacement_preserved", b"exact_rebuild"):
                    self.assertNotIn(forbidden, observed.stdout)

    def test_wrong_argv_and_bundle_mutation_remain_unavailable(self):
        for case_id in ("replacement_race", "single_invocation", "receipt_rebuild"):
            for suffix in (("extra",), ("",)):
                with self.subTest(case_id=case_id, suffix=suffix):
                    result = self.run_case(case_id, *suffix)
                    self.assertEqual((result.returncode, result.stdout, result.stderr),
                                     (64, b"", b""))
        for args in (("--aegis-synthetic-case", "bundle_mutation", "--"),
                     ("--aegis-synthetic-case", "receipt_rebuild", "wrong"),
                     ("--aegis-synthetic-case", "unknown", "--")):
            result = subprocess.run([str(self.executable), *args],
                                    capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (64, b"", b""))
