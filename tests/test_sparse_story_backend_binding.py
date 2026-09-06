import copy
import hashlib
import json
import os
import pickle
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_backend_binding import (  # noqa: E402
    _BackendBinding, _bind_backend,
)
from aegis360.sparse_story_os_backend import (  # noqa: E402
    _OSBackendProof, _observe_os_backend, _observe_test_os_backend,
)
from tests.test_sparse_story_os_backend import FakeNative  # noqa: E402


class BackendBindingNegativeTests(unittest.TestCase):
    def test_mapping_hash_fake_and_subclass_proofs_reject(self):
        class Subclass(_OSBackendProof): pass
        values = ({}, "0" * 64, object(), Subclass.__new__(Subclass))
        for value in values:
            with self.subTest(value=type(value).__name__), self.assertRaises(TypeError):
                _bind_backend(os_backend_proof=value, launcher_runtime_proof=object(),
                              expected_launcher_manifest_sha256="0" * 64)

    def test_binding_owns_close_order_and_all_close_after_error(self):
        backend = _OSBackendProof.__new__(_OSBackendProof)
        runtime_type = __import__("aegis360.sparse_story_asset_tree",
                                  fromlist=["_AssetTreeProof"])._AssetTreeProof
        runtime = runtime_type.__new__(runtime_type)
        order = []
        backend.close = lambda: order.append("os")
        runtime.close = lambda: order.append("launcher")
        with mock.patch("aegis360.sparse_story_backend_binding._derive_bytes",
                        return_value=b"frozen"):
            binding = _bind_backend(os_backend_proof=backend,
                launcher_runtime_proof=runtime,
                expected_launcher_manifest_sha256="0" * 64)
            binding.close(); binding.close()
        self.assertEqual(order, ["launcher", "os"])
        order.clear()
        def launcher_failure():
            order.append("launcher")
            raise OSError("launcher-close-first")
        def os_failure():
            order.append("os")
            raise OSError("os-close-second")
        runtime.close = launcher_failure
        backend.close = os_failure
        with mock.patch("aegis360.sparse_story_backend_binding._derive_bytes",
                        side_effect=ValueError("synthetic")):
            with self.assertRaisesRegex(OSError, "launcher-close-first"):
                _bind_backend(os_backend_proof=backend,
                    launcher_runtime_proof=runtime,
                    expected_launcher_manifest_sha256="0" * 64)
        self.assertEqual(order, ["launcher", "os"])

        order.clear()
        with mock.patch("aegis360.sparse_story_backend_binding._derive_bytes",
                        return_value=b"frozen"):
            binding = _bind_backend(os_backend_proof=backend,
                launcher_runtime_proof=runtime,
                expected_launcher_manifest_sha256="0" * 64)
        with self.assertRaisesRegex(OSError, "launcher-close-first"):
            binding.close()
        self.assertEqual(order, ["launcher", "os"])

    def test_binding_copy_pickle_and_direct_construction_reject(self):
        with self.assertRaises(TypeError):
            _BackendBinding(None, backend=None, runtime=None,
                            expected_runtime_sha="0" * 64, frozen_bytes=b"")
        binding = _BackendBinding.__new__(_BackendBinding)
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(TypeError): operation(binding)

    def test_invalid_expected_sha_attempts_all_closes_and_surfaces_first_error(self):
        backend = _OSBackendProof.__new__(_OSBackendProof)
        runtime_type = __import__("aegis360.sparse_story_asset_tree",
                                  fromlist=["_AssetTreeProof"])._AssetTreeProof
        runtime = runtime_type.__new__(runtime_type)
        order = []
        def launcher_close():
            order.append("launcher")
            raise OSError("launcher-close-first")
        def os_close():
            order.append("os")
            raise OSError("os-close-second")
        runtime.close = launcher_close
        backend.close = os_close
        with self.assertRaisesRegex(OSError, "launcher-close-first") as caught:
            _bind_backend(os_backend_proof=backend, launcher_runtime_proof=runtime,
                          expected_launcher_manifest_sha256="invalid")
        self.assertEqual(order, ["launcher", "os"])
        self.assertIsInstance(caught.exception.__cause__, ValueError)
        self.assertIn("SHA-256", str(caught.exception.__cause__))


@unittest.skipUnless(os.environ.get("AEGIS_RUN_HOST_OS_BACKEND_TESTS") == "1",
                     "set AEGIS_RUN_HOST_OS_BACKEND_TESTS=1 for live binding")
class BackendBindingHostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "runtime"
        result = subprocess.run([str(ROOT / "scripts/build_sparse_story_native_launcher.sh"),
                                 str(cls.root)], capture_output=True, text=True, check=True)
        cls.entrypoint = result.stdout.strip()
        cls.manifest = _observe_asset_manifest_shape(root=cls.root,
            asset_kind="runtime", entrypoint="bin/aegis-sparse-story-launcher")
        from aegis360.sparse_story_runner_contract import canonical_asset_manifest_shape_bytes
        cls.manifest_sha = hashlib.sha256(
            canonical_asset_manifest_shape_bytes(cls.manifest)).hexdigest()

    @classmethod
    def tearDownClass(cls):
        (cls.root / "bin").chmod(0o700); cls.root.chmod(0o700)
        cls.temp.cleanup()

    def proofs(self):
        return _observe_os_backend(), validate_asset_tree(manifest=self.manifest,
                                                          root=self.root)

    def test_live_binding_is_only_canonical_byte_path(self):
        backend, runtime = self.proofs()
        binding = _bind_backend(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=self.manifest_sha)
        payload = binding.canonical_bytes()
        value = json.loads(payload)
        self.assertEqual(value["launcher"]["runtime_manifest_sha256"], self.manifest_sha)
        self.assertEqual(len(value["host"]["system_version_sha256"]), 64)
        self.assertEqual(value["system_rules"], [
            {"operation": "file-read*", "match": "subpath", "path": "/System/Library"},
            {"operation": "file-read*", "match": "subpath", "path": "/private/var/db/dyld"},
            {"operation": "file-read*", "match": "subpath", "path": "/usr/lib"},
            {"operation": "file-read-data", "match": "literal", "path": "/"},
            {"operation": "file-read-metadata", "match": "literal", "path": "/tmp"},
        ])
        forbidden = (b"/Users/", b"/usr/bin/sandbox-exec", b"SystemVersion.plist",
                     str(self.root).encode(), b"inode", b"mtime", b"ctime")
        self.assertTrue(all(item not in payload for item in forbidden))
        self.assertEqual(binding.canonical_bytes(), payload)
        binding.close()
        with self.assertRaisesRegex(ValueError, "closed"): binding.canonical_bytes()
        with self.assertRaisesRegex(ValueError, "closed"): runtime.manifest()
        with self.assertRaisesRegex(ValueError, "closed"): backend.revalidate()

    def test_wrong_precommit_and_closed_proofs_reject_and_close(self):
        backend, runtime = self.proofs()
        with self.assertRaisesRegex(ValueError, "precommit"):
            _bind_backend(os_backend_proof=backend, launcher_runtime_proof=runtime,
                          expected_launcher_manifest_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "closed"): backend.revalidate()
        with self.assertRaisesRegex(ValueError, "closed"): runtime.manifest()

    def test_test_proof_subclass_and_copied_production_os_proof_reject(self):
        import plistlib
        build = plistlib.loads(Path(
            "/System/Library/CoreServices/SystemVersion.plist").read_bytes())[
                "ProductBuildVersion"]
        test_proof = _observe_test_os_backend(native=FakeNative(build))
        runtime = validate_asset_tree(manifest=self.manifest, root=self.root)
        with self.assertRaises(TypeError):
            _bind_backend(os_backend_proof=test_proof, launcher_runtime_proof=runtime,
                          expected_launcher_manifest_sha256=self.manifest_sha)
        test_proof.close()
        backend = _observe_os_backend()
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(TypeError): operation(backend)
        backend.close()

    def test_runtime_copy_and_pickle_fail_before_alias_creation(self):
        backend, runtime = self.proofs()
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(TypeError): operation(runtime)
        runtime.close(); backend.close()

    def test_mutation_after_bind_prevents_canonical_bytes(self):
        backend, runtime = self.proofs()
        binding = _bind_backend(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=self.manifest_sha)
        backend._backend_hash = "0" * 64
        with self.assertRaises(ValueError): binding.canonical_bytes()
        binding.close()


if __name__ == "__main__": unittest.main()
