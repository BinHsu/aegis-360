import copy
import hashlib
import json
import os
import pickle
import subprocess
import struct
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
from aegis360.sparse_story_backend_facade import (  # noqa: E402
    SeatbeltBackendBinding, _AdapterRuntimeBinding, _bind_adapter_runtime,
    open_seatbelt_backend_binding,
)


def thin_macho():
    return (struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 2, 0, 0, 0, 0))


def seal_runtime(root):
    (root / "bin").mkdir(parents=True)
    entrypoint = root / "bin" / "adapter"
    entrypoint.write_bytes(thin_macho())
    entrypoint.chmod(0o555); (root / "bin").chmod(0o555); root.chmod(0o555)
    return entrypoint


def unseal_runtime(root):
    if root.exists():
        for node in root.rglob("*"):
            node.chmod(0o755 if node.is_dir() else 0o644)
        root.chmod(0o755)


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


class FakeAdapterBinding(FakeChild):
    def __init__(self, **kwargs):
        super().__init__(name="adapter", **kwargs)
        self.revalidations = 0
    def revalidate(self):
        self.revalidations += 1


class FailingRegistry:
    def __setitem__(self, _key, _value):
        raise ValueError("registry-publication")
    def pop(self, _key, _default):
        return None


class BackendFacadeTests(unittest.TestCase):
    def open_mocked(self, binding=None):
        binding = binding or FakeBinding()
        backend, runtime = FakeChild("os"), FakeChild("launcher")
        adapter_runtime, adapter_binding = FakeChild("adapter-runtime"), FakeAdapterBinding()
        manifest = {"synthetic": True}; adapter_manifest = {"adapter": True}
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", return_value=b"manifest"), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=(runtime, adapter_runtime)), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        return_value=binding) as bound, \
             mock.patch("aegis360.sparse_story_backend_facade._bind_adapter_runtime",
                        return_value=adapter_binding) as bound_adapter:
            facade = open_seatbelt_backend_binding(
                launcher_root=Path("/absolute/runtime"),
                precommitted_launcher_manifest=manifest,
                adapter_runtime_root=Path("/absolute/adapter-runtime"),
                precommitted_adapter_runtime_manifest=adapter_manifest)
        bound.assert_called_once_with(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=hashlib.sha256(b"manifest").hexdigest())
        bound_adapter.assert_called_once_with(adapter_runtime_proof=adapter_runtime,
                                              expected_adapter_manifest_bytes=b"manifest")
        return facade, binding, adapter_binding

    def test_lifecycle_registry_and_sole_bytes_method(self):
        facade, binding, adapter = self.open_mocked()
        self.assertEqual(facade.canonical_manifest_bytes(), b"manifest")
        self.assertEqual(adapter.revalidations, 1)
        self.assertFalse(hasattr(facade, "__dict__"))
        for name in ("_binding", "_closed", "_origin"):
            with self.assertRaises(AttributeError): setattr(facade, name, object())
        with self.assertRaises(AttributeError):
            facade.canonical_manifest_bytes = lambda: b"shadowed"
        with self.assertRaises(AttributeError):
            facade.close = lambda: None
        facade.close()
        self.assertEqual((adapter.closed, binding.closed), (1, 1))
        facade.close()
        self.assertEqual(binding.closed, 1)
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()
        with self.assertRaisesRegex(ValueError, "not live"): facade.__enter__()

    def test_manual_close_inside_context_is_safe(self):
        facade, binding, adapter = self.open_mocked()
        with facade as entered:
            self.assertIs(entered, facade)
            facade.close()
        self.assertEqual((adapter.closed, binding.closed), (1, 1))
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
        facade, _, _ = self.open_mocked()
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
                    launcher_root=root, precommitted_launcher_manifest=manifest,
                    adapter_runtime_root=root,
                    precommitted_adapter_runtime_manifest=manifest)
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
                    precommitted_launcher_manifest={}, adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={})
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
                    precommitted_launcher_manifest={}, adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={})
        self.assertEqual(order, ["launcher", "os"])

    def test_close_unregisters_before_child_close_failure(self):
        facade, binding, adapter = self.open_mocked(FakeBinding(error=OSError("close")))
        with self.assertRaisesRegex(OSError, "close"): facade.close()
        self.assertEqual(adapter.closed, 1)
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()
        facade.close()

    def test_adapter_close_precedes_backend_and_all_errors_are_attempted(self):
        order = []
        binding = FakeBinding(name="backend", error=OSError("backend-close"), order=order)
        facade, binding, adapter = self.open_mocked(binding)
        adapter.error = OSError("adapter-close"); adapter.order = order
        with self.assertRaisesRegex(OSError, "adapter-close"):
            facade.close()
        self.assertEqual(order, ["adapter", "backend"])
        self.assertEqual((adapter.closed, binding.closed), (1, 1))
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()

    def test_adapter_bind_failure_consumes_proof_once_then_closes_backend(self):
        order = []
        backend, runtime = FakeChild("os", order=order), FakeChild("launcher", order=order)
        adapter_runtime = FakeChild("adapter-runtime", order=order)
        binding = FakeBinding(name="backend", order=order)
        def consume_then_fail(**_):
            adapter_runtime.close()
            raise ValueError("adapter-bind")
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", return_value=b"manifest"), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=(runtime, adapter_runtime)), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        return_value=binding), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_adapter_runtime",
                        side_effect=consume_then_fail):
            with self.assertRaisesRegex(ValueError, "adapter-bind"):
                open_seatbelt_backend_binding(
                    launcher_root=Path("/runtime"), precommitted_launcher_manifest={},
                    adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={})
        self.assertEqual(order, ["adapter-runtime", "backend"])
        self.assertEqual(adapter_runtime.closed, 1)

    def test_registry_publication_failure_closes_live_adapter_then_backend(self):
        order = []
        backend, runtime = FakeChild("os", order=order), FakeChild("launcher", order=order)
        adapter_runtime = FakeChild("adapter-runtime", order=order)
        binding = FakeBinding(name="backend", error=OSError("backend-close"), order=order)
        adapter = FakeAdapterBinding(error=OSError("adapter-close"), order=order)
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", return_value=b"manifest"), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=(runtime, adapter_runtime)), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        return_value=binding), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_adapter_runtime",
                        return_value=adapter), \
             mock.patch("aegis360.sparse_story_backend_facade._LIVE", FailingRegistry()):
            with self.assertRaisesRegex(OSError, "adapter-close") as caught:
                open_seatbelt_backend_binding(
                    launcher_root=Path("/runtime"), precommitted_launcher_manifest={},
                    adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={})
        self.assertEqual(order, ["adapter", "backend"])
        self.assertEqual((adapter.closed, binding.closed), (1, 1))
        self.assertIsInstance(caught.exception.__cause__, ValueError)
        self.assertIn("registry-publication", str(caught.exception.__cause__))

    def test_private_adapter_binding_rejects_direct_construction(self):
        with self.assertRaises(TypeError):
            _AdapterRuntimeBinding(None, runtime=None,
                expected_manifest_bytes=b"manifest", entrypoint="bin/adapter")

    def test_adapter_entrypoint_replacement_blocks_existing_public_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "adapter-runtime"
            with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                    return_value=mock.Mock(sysname="Darwin", machine="arm64")):
                entrypoint = seal_runtime(root)
                manifest = _observe_asset_manifest_shape(root=root, asset_kind="runtime",
                    entrypoint="bin/adapter")
                actual_validate = validate_asset_tree
                backend = FakeChild("os")
                binding = FakeBinding()
                with mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                                return_value=backend), \
                     mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                                return_value=binding), \
                     mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                                side_effect=(FakeChild("launcher"),
                                             actual_validate(manifest=manifest, root=root))):
                    facade = open_seatbelt_backend_binding(
                        launcher_root=root, precommitted_launcher_manifest=manifest,
                        adapter_runtime_root=root,
                        precommitted_adapter_runtime_manifest=manifest)
                try:
                    unseal_runtime(root)
                    entrypoint.unlink(); entrypoint.write_bytes(thin_macho())
                    entrypoint.chmod(0o555); (root / "bin").chmod(0o555); root.chmod(0o555)
                    with self.assertRaisesRegex(ValueError, "identity|changed"):
                        facade.canonical_manifest_bytes()
                finally:
                    facade.close(); unseal_runtime(root)

    def test_adapter_binding_failure_closes_real_retained_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "adapter-runtime"
            with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                    return_value=mock.Mock(sysname="Darwin", machine="arm64")):
                seal_runtime(root)
                manifest = _observe_asset_manifest_shape(root=root, asset_kind="runtime",
                    entrypoint="bin/adapter")
                proof = validate_asset_tree(manifest=manifest, root=root)
                with self.assertRaisesRegex(ValueError, "precommit"):
                    _bind_adapter_runtime(adapter_runtime_proof=proof,
                        expected_adapter_manifest_bytes=b"wrong")
                with self.assertRaisesRegex(ValueError, "closed"):
                    proof.manifest()
                unseal_runtime(root)


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
            adapter_root = Path(directory) / "adapter-runtime"
            subprocess.run([str(ROOT / "scripts/build_sparse_story_native_launcher.sh"),
                            str(adapter_root)], check=True, capture_output=True)
            adapter_manifest = _observe_asset_manifest_shape(root=adapter_root,
                asset_kind="runtime", entrypoint="bin/aegis-sparse-story-launcher")
            try:
                with open_seatbelt_backend_binding(launcher_root=root,
                        precommitted_launcher_manifest=manifest,
                        adapter_runtime_root=adapter_root,
                        precommitted_adapter_runtime_manifest=adapter_manifest) as binding:
                    payload = binding.canonical_manifest_bytes()
                    for forbidden in (b"/Users/", str(root).encode(),
                            str(adapter_root).encode(), b"bin/aegis-sparse-story-launcher",
                            b"/usr/bin/sandbox-exec", b"SystemVersion.plist",
                            b"inode", b"mtime", b"ctime"):
                        self.assertNotIn(forbidden, payload)
                    value = json.loads(payload)
                    self.assertEqual(value["schema_version"],
                                     "aegis360.sparse-story-seatbelt-backend-manifest.v1")
            finally:
                (root / "bin").chmod(0o700); root.chmod(0o700)
                (adapter_root / "bin").chmod(0o700); adapter_root.chmod(0o700)


if __name__ == "__main__": unittest.main()
