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
from aegis360.sparse_story_asset_tree import _observe_asset_manifest_shape  # noqa: E402
from aegis360.sparse_story_backend_facade import (  # noqa: E402
    SeatbeltBackendBinding, open_seatbelt_backend_binding,
)


class FakeChild:
    def __init__(self, name="child", error=None, order=None):
        self.name, self.error, self.order = name, error, order
        self.closed = 0
    def close(self):
        self.closed += 1
        if self.order is not None: self.order.append(self.name)
        if self.error is not None: raise self.error


class FakeBinding(FakeChild):
    def __init__(self, payload=b"manifest", **kwargs):
        super().__init__(**kwargs); self.payload = payload
    def canonical_bytes(self): return self.payload


class BackendFacadeTests(unittest.TestCase):
    def open_mocked(self, binding=None):
        binding = binding or FakeBinding()
        backend, runtime = FakeChild("os"), FakeChild("launcher")
        manifest = {"synthetic": True}
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", return_value=b"manifest"), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        return_value=runtime), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        return_value=binding) as bound:
            facade = open_seatbelt_backend_binding(
                launcher_root=Path("/absolute/runtime"),
                precommitted_launcher_manifest=manifest)
        bound.assert_called_once_with(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=hashlib.sha256(b"manifest").hexdigest())
        return facade, binding

    def test_lifecycle_registry_and_sole_bytes_method(self):
        facade, binding = self.open_mocked()
        self.assertEqual(facade.canonical_manifest_bytes(), b"manifest")
        self.assertFalse(hasattr(facade, "__dict__"))
        for name in ("_binding", "_closed", "_origin"):
            with self.assertRaises(AttributeError): setattr(facade, name, object())
        with self.assertRaises(AttributeError):
            facade.canonical_manifest_bytes = lambda: b"shadowed"
        with self.assertRaises(AttributeError):
            facade.close = lambda: None
        facade.close()
        self.assertEqual(binding.closed, 1)
        facade.close()
        self.assertEqual(binding.closed, 1)
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()
        with self.assertRaisesRegex(ValueError, "not live"): facade.__enter__()

    def test_manual_close_inside_context_is_safe(self):
        facade, binding = self.open_mocked()
        with facade as entered:
            self.assertIs(entered, facade)
            facade.close()
        self.assertEqual(binding.closed, 1)
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()

    def test_constructor_new_subclass_copy_pickle_and_replay_reject(self):
        with self.assertRaises(TypeError): SeatbeltBackendBinding(None, None)
        forged = SeatbeltBackendBinding.__new__(SeatbeltBackendBinding)
        with self.assertRaisesRegex(ValueError, "not live"):
            forged.canonical_manifest_bytes()
        with self.assertRaisesRegex(ValueError, "not live"): forged.close()
        with self.assertRaises(TypeError):
            class Subclass(SeatbeltBackendBinding): pass
        facade, _ = self.open_mocked()
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(TypeError): operation(facade)
        facade.close()
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()

    def test_api_accepts_no_proofs_hashes_or_backend_mappings(self):
        for root, manifest in ((object(), {}), (Path("/runtime"), object()),
                               ("hash", "hash")):
            with self.assertRaises(ValueError):
                open_seatbelt_backend_binding(
                    launcher_root=root, precommitted_launcher_manifest=manifest)
        with self.assertRaises(TypeError):
            open_seatbelt_backend_binding(launcher_root=Path("/runtime"),
                precommitted_launcher_manifest={}, backend_proof=object())

    def test_validation_failure_closes_os_and_surfaces_cleanup_error(self):
        order = []
        backend = FakeChild("os", OSError("os-close"), order)
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", return_value=b"manifest"), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=ValueError("validation")):
            with self.assertRaisesRegex(OSError, "os-close") as caught:
                open_seatbelt_backend_binding(launcher_root=Path("/runtime"),
                    precommitted_launcher_manifest={})
        self.assertEqual(order, ["os"])
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_bind_failure_closes_launcher_then_os_first_error_wins(self):
        order = []
        runtime = FakeChild("launcher", OSError("launcher-first"), order)
        backend = FakeChild("os", OSError("os-second"), order)
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", return_value=b"manifest"), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        return_value=runtime), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        side_effect=ValueError("bind")):
            with self.assertRaisesRegex(OSError, "launcher-first"):
                open_seatbelt_backend_binding(launcher_root=Path("/runtime"),
                    precommitted_launcher_manifest={})
        self.assertEqual(order, ["launcher", "os"])

    def test_close_unregisters_before_child_close_failure(self):
        facade, binding = self.open_mocked(FakeBinding(error=OSError("close")))
        with self.assertRaisesRegex(OSError, "close"): facade.close()
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()
        facade.close()


@unittest.skipUnless(os.environ.get("AEGIS_RUN_HOST_OS_BACKEND_TESTS") == "1",
                     "set AEGIS_RUN_HOST_OS_BACKEND_TESTS=1 for live facade")
class BackendFacadeHostTests(unittest.TestCase):
    def test_real_live_facade_returns_path_free_existing_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            subprocess.run([str(ROOT / "scripts/build_sparse_story_native_launcher.sh"),
                            str(root)], check=True, capture_output=True)
            manifest = _observe_asset_manifest_shape(root=root, asset_kind="runtime",
                entrypoint="bin/aegis-sparse-story-launcher")
            try:
                with open_seatbelt_backend_binding(launcher_root=root,
                        precommitted_launcher_manifest=manifest) as binding:
                    value = json.loads(binding.canonical_manifest_bytes())
                    self.assertEqual(value["schema_version"],
                                     "aegis360.sparse-story-seatbelt-backend-manifest.v1")
                    payload = binding.canonical_manifest_bytes()
                    for forbidden in (b"/Users/", str(root).encode(),
                            b"/usr/bin/sandbox-exec", b"SystemVersion.plist",
                            b"inode", b"mtime", b"ctime"):
                        self.assertNotIn(forbidden, payload)
            finally:
                (root / "bin").chmod(0o700); root.chmod(0o700)


if __name__ == "__main__": unittest.main()
