import os
import subprocess
import sys
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_probe_context import _ProbeContext  # noqa: E402
from aegis360.sparse_story_probe_listeners import _ProbeListeners  # noqa: E402
from aegis360.sparse_story_probe_sentinels import (  # noqa: E402
    _OutsideSentinelSnapshot, _ReadDenialSentinel, _ScratchProbeSnapshot,
)
from aegis360.sparse_story_probe_transcript import (  # noqa: E402
    _check_probe_row_values, parse_isolation_probe_transcript,
)
from aegis360.sparse_story_raw_probe_transport import _run_raw_probe  # noqa: E402
from tests import test_sparse_story_batch_policy as batch_policy_tests  # noqa: E402


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class RawProbeTransportHostTests(unittest.TestCase):
    @contextmanager
    def context(self):
        fixture = batch_policy_tests.BatchPolicyTests(
            "test_exact_policy_is_frozen_and_path_free_digest_only")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        base = fixture.base
        with ExitStack() as stack:
            launcher_root = base / "real-launcher"
            subprocess.run([str(ROOT / "scripts/build_sparse_story_native_launcher.sh"),
                            str(launcher_root)], check=True, capture_output=True)
            launcher_manifest = _observe_asset_manifest_shape(root=launcher_root,
                asset_kind="runtime", entrypoint="bin/aegis-sparse-story-launcher")
            launcher = stack.enter_context(validate_asset_tree(
                manifest=launcher_manifest, root=launcher_root))
            runtime_root = base / "real-runtime"
            (runtime_root / "bin").mkdir(parents=True)
            executable = runtime_root / "bin/aegis-synthetic-adapter"
            subprocess.run(["/usr/bin/xcrun", "--sdk", "macosx", "clang", "-std=c11",
                "-Os", "-Wall", "-Wextra", "-Werror", "-Wpedantic",
                "-fstack-protector-strong", "-arch", "arm64",
                "-mmacosx-version-min=15.0",
                str(ROOT / "tools/sparse_story_synthetic_adapter_fixture.c"),
                "-o", str(executable)], check=True, capture_output=True)
            subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-",
                "--timestamp=none", str(executable)], check=True, capture_output=True)
            executable.chmod(0o555)
            (runtime_root / "bin").chmod(0o555)
            runtime_root.chmod(0o555)
            runtime_manifest = _observe_asset_manifest_shape(root=runtime_root,
                asset_kind="runtime", entrypoint="bin/aegis-synthetic-adapter")
            runtime = stack.enter_context(validate_asset_tree(
                manifest=runtime_manifest, root=runtime_root))
            fixture.live._backend_binding._runtime = launcher
            fixture.live._adapter_binding._runtime = runtime
            candidate = fixture.candidate()
            outside = base / "outside"; outside.mkdir(mode=0o700)
            (outside / "outside-existing").write_bytes(b"outside-existing-sentinel-v1")
            (outside / "outside-existing").chmod(0o600)
            scratch = fixture.args["scratch_root"]
            (scratch / "rename-source").write_bytes(b"rename-source-v1")
            (scratch / "rename-source").chmod(0o600)
            denied = base / "denied"; denied.mkdir(mode=0o700)
            for name in ("neighbor", "result"):
                (denied / name).write_bytes(name.encode())
                (denied / name).chmod(0o600)
            listener_root = base / "listeners"; listener_root.mkdir(mode=0o700)
            reads = [stack.enter_context(_ReadDenialSentinel(path)) for path in (
                ROOT / "src/aegis360/sparse_story_batch_policy.py",
                ROOT / "docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md",
                denied / "neighbor", denied / "result")]
            context = _ProbeContext(candidate=candidate, repository=reads[0],
                protocol=reads[1], neighbor=reads[2], result=reads[3],
                outside=stack.enter_context(_OutsideSentinelSnapshot(outside)),
                scratch=stack.enter_context(_ScratchProbeSnapshot(scratch,
                    fixture.args["private_home"], fixture.args["private_tmpdir"])),
                listeners=stack.enter_context(_ProbeListeners(listener_root)))
            yield context

    def test_same_retained_runtime_probes_through_native_launcher(self):
        with self.context() as context:
            capture = _run_raw_probe(context)
            self.assertTrue(capture.completed, capture.reason)
            self.assertEqual((capture.returncode, capture.postcheck_passed), (0, True))
            rows = parse_isolation_probe_transcript(capture.stdout)
            allowed = context.allowed
            primitive = _check_probe_row_values(rows,
                bundle_prefix=allowed[0].prefix, model_prefix=allowed[1].prefix,
                prompt_prefix=allowed[2].prefix)
            self.assertTrue(all(primitive.values()), primitive)

    def test_timeout_before_policy_delivery_fails_without_adapter_output(self):
        with self.context() as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS", 1):
            capture = _run_raw_probe(context)
            self.assertFalse(capture.completed)
            self.assertFalse(capture.postcheck_passed)
            self.assertEqual(capture.stdout, b"")

    def test_postexit_sentinel_mutation_invalidates_completed_rows(self):
        with self.context() as context:
            original = _ProbeContext.postvalidate

            def mutate_before_validation(probe):
                (context.outside.root / "outside-existing").write_bytes(b"changed")
                return original(probe)

            with mock.patch.object(_ProbeContext, "postvalidate",
                    mutate_before_validation):
                capture = _run_raw_probe(context)
            self.assertFalse(capture.completed)
            self.assertFalse(capture.postcheck_passed)


if __name__ == "__main__": unittest.main()
