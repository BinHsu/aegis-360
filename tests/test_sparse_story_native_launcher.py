import hashlib
import os
import stat
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_sparse_story_native_launcher.sh"
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, _validate_runtime_entrypoint,
    validate_asset_tree,
)


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64",
                     "native launcher is Darwin arm64 only")
class NativeLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.runtime_root = cls.base / "launcher-runtime"
        result = subprocess.run([str(BUILD), str(cls.runtime_root)], check=True,
                                capture_output=True, text=True)
        cls.launcher = Path(result.stdout.strip())
        source = cls.base / "observer.c"
        source.write_text("""#include <stdio.h>\n#include <unistd.h>\nint main(int c,char**v){printf(\"pid=%ld pgid=%ld cwd=\",(long)getpid(),(long)getpgrp());char b[4096];puts(getcwd(b,sizeof b));for(int i=1;i<c;i++)printf(\"arg=%s\\n\",v[i]);return 0;}\n""")
        cls.adapter = cls.base / "adapter"
        subprocess.run(["/usr/bin/xcrun", "clang", "-arch", "arm64",
                        "-mmacosx-version-min=15.0", str(source), "-o", str(cls.adapter)],
                       check=True)
        cls.adapter.chmod(0o555)
        cls.cwd = cls.base / "bundle"
        cls.cwd.mkdir(); cls.cwd.chmod(0o555)
        cls.home = cls.base / "home"; cls.home.mkdir(); cls.home.chmod(0o700)
        cls.tmp = cls.base / "tmp"; cls.tmp.mkdir(); cls.tmp.chmod(0o700)

    @classmethod
    def tearDownClass(cls):
        for path in (cls.cwd, cls.home, cls.tmp, cls.runtime_root):
            if path.exists(): path.chmod(0o700)
        launcher_bin = cls.runtime_root / "bin"
        if launcher_bin.exists(): launcher_bin.chmod(0o700)
        cls.temp.cleanup()

    def invoke(self, policy=b"(version 1) (allow default)\n", sha=None,
               declared_size=None, prefixed_size=None, transport=None,
               extra_env=None, args=("literal;$(false)",), runtime_ino=None):
        read_fd, write_fd = os.pipe()
        os.set_inheritable(read_fd, True)
        if declared_size is None: declared_size = len(policy)
        if prefixed_size is None: prefixed_size = declared_size
        if transport is None: transport = struct.pack(">Q", prefixed_size) + policy
        os.write(write_fd, transport); os.close(write_fd)
        cwd_stat, runtime_stat = self.cwd.stat(), self.adapter.stat()
        if runtime_ino is None: runtime_ino = runtime_stat.st_ino
        if sha is None: sha = hashlib.sha256(policy).hexdigest()
        argv = [str(self.launcher), f"--policy-fd={read_fd}",
                f"--policy-size={declared_size}", f"--policy-sha256={sha}",
                f"--cwd-fd={os.open(self.cwd, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)}",
                f"--cwd-dev={cwd_stat.st_dev}", f"--cwd-ino={cwd_stat.st_ino}",
                f"--uid={os.getuid()}", f"--gid={os.getgid()}",
                f"--home={self.home}", f"--tmpdir={self.tmp}",
                f"--runtime-dev={runtime_stat.st_dev}",
                f"--runtime-ino={runtime_ino}",
                f"--runtime-size={runtime_stat.st_size}", "--", str(self.adapter), *args]
        cwd_fd = int(argv[4].split("=", 1)[1]); os.set_inheritable(cwd_fd, True)
        env = {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1",
               "HOME": str(self.home), "TMPDIR": str(self.tmp)}
        if extra_env: env.update(extra_env)
        try:
            return subprocess.run(argv, pass_fds=(read_fd, cwd_fd), env=env,
                                  capture_output=True, timeout=10)
        finally:
            os.close(read_fd); os.close(cwd_fd)

    def test_build_is_signed_thin_arm64(self):
        subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(self.launcher)],
                       check=True)
        arch = subprocess.check_output(["/usr/bin/lipo", "-archs", str(self.launcher)],
                                       text=True).strip()
        self.assertEqual(arch, "arm64")
        self.assertEqual(stat.S_IMODE(self.launcher.stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE((self.runtime_root / "bin").stat().st_mode), 0o555)
        self.assertEqual(stat.S_IMODE(self.runtime_root.stat().st_mode), 0o555)
        entitlements = subprocess.run(
            ["/usr/bin/codesign", "-d", "--entitlements", ":-", str(self.launcher)],
            capture_output=True, check=True)
        self.assertNotIn(b"<key>", entitlements.stdout + entitlements.stderr)
        fd = os.open(self.launcher, os.O_RDONLY | os.O_CLOEXEC)
        try:
            _validate_runtime_entrypoint(fd)
        finally:
            os.close(fd)

    def test_sealed_runtime_tree_passes_retained_asset_validation(self):
        manifest = _observe_asset_manifest_shape(
            root=self.runtime_root, asset_kind="runtime",
            entrypoint="bin/aegis-sparse-story-launcher")
        with validate_asset_tree(manifest=manifest, root=self.runtime_root) as proof:
            self.assertEqual(proof.manifest(), manifest)

    def test_build_refuses_to_overwrite_sealed_runtime(self):
        before = hashlib.sha256(self.launcher.read_bytes()).hexdigest()
        result = subprocess.run([str(BUILD), str(self.runtime_root)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(hashlib.sha256(self.launcher.read_bytes()).hexdigest(), before)

    @unittest.skipUnless(os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
                         "set AEGIS_RUN_HOST_SEATBELT_TESTS=1 outside nested sandbox")
    def test_exact_policy_and_literal_argv_reach_runtime_with_same_pid(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout.decode()
        self.assertIn(f"cwd={self.cwd.resolve()}\n", text)
        self.assertIn("arg=literal;$(false)\n", text)
        first = text.splitlines()[0].split()
        self.assertEqual(first[0].removeprefix("pid="),
                         first[1].removeprefix("pgid="))

    def test_wrong_policy_hash_fails_before_runtime(self):
        result = self.invoke(sha="0" * 64)
        self.assertEqual(result.returncode, 70)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"launcher:policy-hash\n")

    def test_runtime_identity_mismatch_fails_closed(self):
        result = self.invoke(runtime_ino=self.adapter.stat().st_ino + 1)
        self.assertEqual((result.returncode, result.stdout), (70, b""))
        self.assertEqual(result.stderr, b"launcher:runtime\n")

    def test_short_and_extra_policy_fail_closed(self):
        short = self.invoke(declared_size=99)
        self.assertEqual((short.returncode, short.stdout), (70, b""))
        extra = self.invoke(declared_size=1)
        self.assertEqual((extra.returncode, extra.stdout), (70, b""))

    def test_prefix_mismatch_and_truncation_fail_closed(self):
        mismatch = self.invoke(prefixed_size=1)
        self.assertEqual(mismatch.stderr, b"launcher:policy-prefix\n")
        truncated = self.invoke(transport=b"\x00\x00\x00")
        self.assertEqual(truncated.stderr, b"launcher:policy-prefix\n")

    def test_policy_requires_exact_final_lf(self):
        absent = self.invoke(policy=b"(version 1) (allow default)")
        self.assertEqual(absent.stderr, b"launcher:policy-bytes\n")
        trailing = self.invoke(policy=b"(version 1) (allow default)\nX")
        self.assertEqual(trailing.stderr, b"launcher:policy-bytes\n")

    def test_policy_size_above_bound_fails_before_read(self):
        result = self.invoke(declared_size=65537)
        self.assertEqual((result.returncode, result.stdout), (70, b""))
        self.assertEqual(result.stderr, b"launcher:argv\n")

    def test_extra_environment_fails_closed(self):
        result = self.invoke(extra_env={"PATH": "/bin"})
        self.assertEqual((result.returncode, result.stdout), (70, b""))
        self.assertEqual(result.stderr, b"launcher:env\n")


if __name__ == "__main__":
    unittest.main()
