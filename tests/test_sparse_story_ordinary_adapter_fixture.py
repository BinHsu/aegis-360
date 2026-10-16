import os
import select
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64",
                     "native adapter fixture is Darwin arm64 only")
class OrdinaryAdapterFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.executable = Path(cls.temp.name) / "aegis-synthetic-adapter"
        subprocess.run(["/usr/bin/xcrun", "--sdk", "macosx", "clang", "-std=c11",
            "-Os", "-Wall", "-Wextra", "-Werror", "-Wpedantic",
            "-fstack-protector-strong", "-arch", "arm64",
            "-mmacosx-version-min=15.0",
            str(ROOT / "tools/sparse_story_synthetic_adapter_fixture.c"),
            "-o", str(cls.executable)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_ordinary_mode_waits_for_eof_before_closed_abstention(self):
        process = subprocess.Popen([str(self.executable)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            process.stdin.write(b'{"request":"synthetic"}')
            process.stdin.flush()
            ready, _, _ = select.select([process.stdout], [], [], 0.1)
            self.assertEqual(ready, [], "ordinary adapter answered before request EOF")
            process.stdin.close()
            stdout = process.stdout.read()
            stderr = process.stderr.read()
            self.assertEqual(process.wait(timeout=5), 0)
            self.assertEqual(stderr, b"")
            self.assertIn(b'"status":"abstain"', stdout)
            self.assertIn(b'"transition_support":"insufficient"', stdout)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            process.stdin.close()
            process.stdout.close()
            process.stderr.close()

    def test_ordinary_mode_rejects_empty_and_oversized_requests(self):
        for payload, expected_code in ((b"", 65), (b"x" * 1048576, 0),
                                       (b"x" * 1048577, 65)):
            with self.subTest(length=len(payload)):
                result = subprocess.run([str(self.executable)], input=payload,
                                        capture_output=True, timeout=5)
                self.assertEqual(result.returncode, expected_code)
                self.assertEqual(result.stderr, b"")
                self.assertEqual(b'"status":"abstain"' in result.stdout,
                                 expected_code == 0)


if __name__ == "__main__":
    unittest.main()
