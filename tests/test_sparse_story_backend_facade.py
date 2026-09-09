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
    SeatbeltBackendBinding, _AdapterRuntimeBinding, _ForbiddenExecSentinelBinding,
    _bind_adapter_runtime, _bind_forbidden_exec_sentinel,
    open_seatbelt_backend_binding,
)
from aegis360.sparse_story_runner_contract import canonical_asset_manifest_shape_bytes  # noqa: E402


def thin_macho():
    return (struct.pack("<IiiIIIII", 0xFEEDFACF, 0x0100000C, 0, 2, 0, 0, 0, 0))


def seal_runtime(root, entrypoint="bin/adapter"):
    (root / "bin").mkdir(parents=True)
    executable = root / entrypoint
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_bytes(thin_macho())
    executable.chmod(0o555); (root / "bin").chmod(0o555); root.chmod(0o555)
    return executable


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


class FakeSentinelBinding(FakeChild):
    def __init__(self, **kwargs):
        super().__init__(name="sentinel", **kwargs)
        self.revalidations = 0
    def revalidate(self):
        self.revalidations += 1


class FailingRegistry:
    def __setitem__(self, _key, _value):
        raise ValueError("registry-publication")
    def pop(self, _key, _default):
        return None


def fake_manifest_bytes(manifest):
    return repr(sorted(manifest.items())).encode("ascii")


class BackendFacadeTests(unittest.TestCase):
    def open_mocked(self, binding=None):
        binding = binding or FakeBinding()
        backend, runtime = FakeChild("os"), FakeChild("launcher")
        adapter_runtime, adapter_binding = FakeChild("adapter-runtime"), FakeAdapterBinding()
        sentinel_runtime, sentinel_binding = FakeChild("sentinel-runtime"), FakeSentinelBinding()
        manifest = {"synthetic": True}; adapter_manifest = {"adapter": True}
        sentinel_manifest = {"sentinel": True}
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", side_effect=fake_manifest_bytes), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=(runtime, adapter_runtime, sentinel_runtime)), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        return_value=binding) as bound, \
             mock.patch("aegis360.sparse_story_backend_facade._bind_adapter_runtime",
                        return_value=adapter_binding) as bound_adapter, \
             mock.patch("aegis360.sparse_story_backend_facade._bind_forbidden_exec_sentinel",
                        return_value=sentinel_binding) as bound_sentinel:
            facade = open_seatbelt_backend_binding(
                launcher_root=Path("/absolute/runtime"),
                precommitted_launcher_manifest=manifest,
                adapter_runtime_root=Path("/absolute/adapter-runtime"),
                precommitted_adapter_runtime_manifest=adapter_manifest,
                forbidden_exec_sentinel_runtime_root=Path("/absolute/sentinel-runtime"),
                precommitted_forbidden_exec_sentinel_manifest=sentinel_manifest)
        bound.assert_called_once_with(os_backend_proof=backend,
            launcher_runtime_proof=runtime,
            expected_launcher_manifest_sha256=hashlib.sha256(
                fake_manifest_bytes(manifest)).hexdigest())
        bound_adapter.assert_called_once_with(adapter_runtime_proof=adapter_runtime,
                                              expected_adapter_manifest_bytes=
                                              fake_manifest_bytes(adapter_manifest))
        bound_sentinel.assert_called_once_with(sentinel_runtime_proof=sentinel_runtime,
            expected_sentinel_manifest_bytes=fake_manifest_bytes(sentinel_manifest))
        return facade, binding, adapter_binding, sentinel_binding

    def test_lifecycle_registry_and_sole_bytes_method(self):
        facade, binding, adapter, sentinel = self.open_mocked()
        self.assertEqual(facade.canonical_manifest_bytes(), b"manifest")
        self.assertEqual((sentinel.revalidations, adapter.revalidations), (1, 1))
        self.assertFalse(hasattr(facade, "__dict__"))
        for name in ("_binding", "_closed", "_origin"):
            with self.assertRaises(AttributeError): setattr(facade, name, object())
        with self.assertRaises(AttributeError):
            facade.canonical_manifest_bytes = lambda: b"shadowed"
        with self.assertRaises(AttributeError):
            facade.close = lambda: None
        facade.close()
        self.assertEqual((sentinel.closed, adapter.closed, binding.closed), (1, 1, 1))
        facade.close()
        self.assertEqual(binding.closed, 1)
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()
        with self.assertRaisesRegex(ValueError, "not live"): facade.__enter__()

    def test_manual_close_inside_context_is_safe(self):
        facade, binding, adapter, sentinel = self.open_mocked()
        with facade as entered:
            self.assertIs(entered, facade)
            facade.close()
        self.assertEqual((sentinel.closed, adapter.closed, binding.closed), (1, 1, 1))
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
        facade, _, _, _ = self.open_mocked()
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
                    precommitted_adapter_runtime_manifest=manifest,
                    forbidden_exec_sentinel_runtime_root=root,
                    precommitted_forbidden_exec_sentinel_manifest=manifest)
        with self.assertRaises(TypeError):
            open_seatbelt_backend_binding(launcher_root=Path("/runtime"),
                precommitted_launcher_manifest={}, backend_proof=object())

    def test_all_role_inputs_must_be_pairwise_distinct(self):
        def open_roles(*, launcher_root=Path("/launcher"), launcher_manifest=None,
                       adapter_root=Path("/adapter"), adapter_manifest=None,
                       sentinel_root=Path("/sentinel"), sentinel_manifest=None):
            return open_seatbelt_backend_binding(
                launcher_root=launcher_root,
                precommitted_launcher_manifest=(launcher_manifest if launcher_manifest is not None
                                                else {"launcher": True}),
                adapter_runtime_root=adapter_root,
                precommitted_adapter_runtime_manifest=(adapter_manifest if adapter_manifest is not None
                                                       else {"adapter": True}),
                forbidden_exec_sentinel_runtime_root=sentinel_root,
                precommitted_forbidden_exec_sentinel_manifest=(
                    sentinel_manifest if sentinel_manifest is not None else {"sentinel": True}))

        for first, second in (("launcher", "adapter"), ("launcher", "sentinel"),
                              ("adapter", "sentinel")):
            roots = {"launcher_root": Path("/launcher"), "adapter_root": Path("/adapter"),
                     "sentinel_root": Path("/sentinel")}
            roots[f"{second}_root"] = roots[f"{first}_root"]
            with self.assertRaisesRegex(ValueError, "roles must be distinct"):
                open_roles(**roots)

            shared = {"shared": first + second}
            manifests = {"launcher_manifest": {"launcher": True},
                         "adapter_manifest": {"adapter": True},
                         "sentinel_manifest": {"sentinel": True}}
            manifests[f"{second}_manifest"] = shared
            manifests[f"{first}_manifest"] = shared
            with self.assertRaisesRegex(ValueError, "roles must be distinct"):
                open_roles(**manifests)

        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", side_effect=fake_manifest_bytes):
            for first, second in (("launcher", "adapter"), ("launcher", "sentinel"),
                                  ("adapter", "sentinel")):
                manifests = {"launcher_manifest": {"launcher": True},
                             "adapter_manifest": {"adapter": True},
                             "sentinel_manifest": {"sentinel": True}}
                manifests[f"{first}_manifest"] = {"shared": True}
                manifests[f"{second}_manifest"] = {"shared": True}
                with self.assertRaisesRegex(ValueError, "role manifests must be distinct"):
                    open_roles(**manifests)

    def test_validation_failure_closes_os_and_surfaces_cleanup_error(self):
        order = []
        backend = FakeChild("os", OSError("os-close"), order)
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", side_effect=fake_manifest_bytes), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=ValueError("validation")):
            with self.assertRaisesRegex(OSError, "os-close") as caught:
                open_seatbelt_backend_binding(launcher_root=Path("/runtime"),
                    precommitted_launcher_manifest={}, adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={"adapter": True},
                    forbidden_exec_sentinel_runtime_root=Path("/sentinel"),
                    precommitted_forbidden_exec_sentinel_manifest={"sentinel": True})
        self.assertEqual(order, ["os"])
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_bind_failure_closes_launcher_then_os_first_error_wins(self):
        order = []
        runtime = FakeChild("launcher", OSError("launcher-first"), order)
        backend = FakeChild("os", OSError("os-second"), order)
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", side_effect=fake_manifest_bytes), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        return_value=runtime), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        side_effect=ValueError("bind")):
            with self.assertRaisesRegex(OSError, "launcher-first"):
                open_seatbelt_backend_binding(launcher_root=Path("/runtime"),
                    precommitted_launcher_manifest={}, adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={"adapter": True},
                    forbidden_exec_sentinel_runtime_root=Path("/sentinel"),
                    precommitted_forbidden_exec_sentinel_manifest={"sentinel": True})
        self.assertEqual(order, ["launcher", "os"])

    def test_retained_role_aliases_close_owned_children_without_publication(self):
        cases = (
            ("launcher-adapter", ((1, 1, "launcher"), (1, 1, "adapter"),
                                    (1, 3, "sentinel")),
             ["adapter-runtime", "backend"]),
            ("launcher-sentinel", ((1, 1, "launcher"), (1, 2, "adapter"),
                                    (1, 3, "launcher")),
             ["sentinel-runtime", "adapter", "backend"]),
            ("adapter-sentinel", ((1, 1, "launcher"), (1, 2, "adapter"),
                                   (1, 2, "sentinel")),
             ["sentinel-runtime", "adapter", "backend"]),
        )
        for label, identities, expected_order in cases:
            with self.subTest(label=label):
                order = []
                backend = FakeChild("backend", order=order)
                launcher = FakeChild("launcher-runtime", order=order)
                adapter_runtime = FakeChild("adapter-runtime", order=order)
                sentinel_runtime = FakeChild("sentinel-runtime", order=order)
                adapter = FakeAdapterBinding(order=order)
                with mock.patch("aegis360.sparse_story_backend_facade."
                                "canonical_asset_manifest_shape_bytes",
                                side_effect=fake_manifest_bytes), \
                     mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                                return_value=FakeChild("os", order=order)), \
                     mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                                side_effect=(launcher, adapter_runtime, sentinel_runtime)), \
                     mock.patch("aegis360.sparse_story_backend_facade._asset_identity",
                                side_effect=identities), \
                     mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                                return_value=backend), \
                     mock.patch("aegis360.sparse_story_backend_facade._bind_adapter_runtime",
                                return_value=adapter), \
                     mock.patch("aegis360.sparse_story_backend_facade."
                                "_bind_forbidden_exec_sentinel",
                                return_value=FakeSentinelBinding(order=order)):
                    with self.assertRaisesRegex(ValueError, "roles must be distinct"):
                        open_seatbelt_backend_binding(
                            launcher_root=Path("/launcher"),
                            precommitted_launcher_manifest={"launcher": True},
                            adapter_runtime_root=Path("/adapter"),
                            precommitted_adapter_runtime_manifest={"adapter": True},
                            forbidden_exec_sentinel_runtime_root=Path("/sentinel"),
                            precommitted_forbidden_exec_sentinel_manifest={"sentinel": True})
                self.assertEqual(order, expected_order)
                self.assertEqual(launcher.closed, 0)

    def test_close_unregisters_before_child_close_failure(self):
        facade, binding, adapter, sentinel = self.open_mocked(
            FakeBinding(error=OSError("close")))
        with self.assertRaisesRegex(OSError, "close"): facade.close()
        self.assertEqual((sentinel.closed, adapter.closed), (1, 1))
        with self.assertRaisesRegex(ValueError, "not live"):
            facade.canonical_manifest_bytes()
        facade.close()

    def test_sentinel_adapter_backend_close_order_and_all_errors_are_attempted(self):
        order = []
        binding = FakeBinding(name="backend", error=OSError("backend-close"), order=order)
        facade, binding, adapter, sentinel = self.open_mocked(binding)
        sentinel.error = OSError("sentinel-close"); sentinel.order = order
        adapter.error = OSError("adapter-close"); adapter.order = order
        with self.assertRaisesRegex(OSError, "sentinel-close"):
            facade.close()
        self.assertEqual(order, ["sentinel", "adapter", "backend"])
        self.assertEqual((sentinel.closed, adapter.closed, binding.closed), (1, 1, 1))
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
                        "canonical_asset_manifest_shape_bytes", side_effect=fake_manifest_bytes), \
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
                    precommitted_adapter_runtime_manifest={"adapter": True},
                    forbidden_exec_sentinel_runtime_root=Path("/sentinel"),
                    precommitted_forbidden_exec_sentinel_manifest={"sentinel": True})
        self.assertEqual(order, ["adapter-runtime", "backend"])
        self.assertEqual(adapter_runtime.closed, 1)

    def test_registry_publication_failure_closes_live_sentinel_adapter_then_backend(self):
        order = []
        backend, runtime = FakeChild("os", order=order), FakeChild("launcher", order=order)
        adapter_runtime = FakeChild("adapter-runtime", order=order)
        sentinel_runtime = FakeChild("sentinel-runtime", order=order)
        binding = FakeBinding(name="backend", error=OSError("backend-close"), order=order)
        adapter = FakeAdapterBinding(error=OSError("adapter-close"), order=order)
        sentinel = FakeSentinelBinding(error=OSError("sentinel-close"), order=order)
        with mock.patch("aegis360.sparse_story_backend_facade."
                        "canonical_asset_manifest_shape_bytes", side_effect=fake_manifest_bytes), \
             mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                        return_value=backend), \
             mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                        side_effect=(runtime, adapter_runtime, sentinel_runtime)), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                        return_value=binding), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_adapter_runtime",
                        return_value=adapter), \
             mock.patch("aegis360.sparse_story_backend_facade._bind_forbidden_exec_sentinel",
                        return_value=sentinel), \
             mock.patch("aegis360.sparse_story_backend_facade._LIVE", FailingRegistry()):
            with self.assertRaisesRegex(OSError, "sentinel-close") as caught:
                open_seatbelt_backend_binding(
                    launcher_root=Path("/runtime"), precommitted_launcher_manifest={},
                    adapter_runtime_root=Path("/adapter"),
                    precommitted_adapter_runtime_manifest={"adapter": True},
                    forbidden_exec_sentinel_runtime_root=Path("/sentinel"),
                    precommitted_forbidden_exec_sentinel_manifest={"sentinel": True})
        self.assertEqual(order, ["sentinel", "adapter", "backend"])
        self.assertEqual((sentinel.closed, adapter.closed, binding.closed), (1, 1, 1))
        self.assertIsInstance(caught.exception.__cause__, ValueError)
        self.assertIn("registry-publication", str(caught.exception.__cause__))

    def test_private_adapter_binding_rejects_direct_construction(self):
        with self.assertRaises(TypeError):
            _AdapterRuntimeBinding(None, runtime=None,
                expected_manifest_bytes=b"manifest", entrypoint="bin/adapter")

    def test_private_sentinel_binding_rejects_direct_construction(self):
        with self.assertRaises(TypeError):
            _ForbiddenExecSentinelBinding(None, runtime=None,
                expected_manifest_bytes=b"manifest")

    def test_adapter_entrypoint_replacement_blocks_existing_public_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher_root = Path(directory) / "launcher-runtime"
            root = Path(directory) / "adapter-runtime"
            sentinel_root = Path(directory) / "sentinel-runtime"
            with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                    return_value=mock.Mock(sysname="Darwin", machine="arm64")):
                seal_runtime(launcher_root, "bin/launcher")
                launcher_manifest = _observe_asset_manifest_shape(root=launcher_root,
                    asset_kind="runtime", entrypoint="bin/launcher")
                entrypoint = seal_runtime(root)
                manifest = _observe_asset_manifest_shape(root=root, asset_kind="runtime",
                    entrypoint="bin/adapter")
                seal_runtime(sentinel_root, "bin/aegis-forbidden-exec-sentinel")
                sentinel_manifest = _observe_asset_manifest_shape(root=sentinel_root,
                    asset_kind="runtime", entrypoint="bin/aegis-forbidden-exec-sentinel")
                actual_validate = validate_asset_tree
                backend = FakeChild("os")
                binding = FakeBinding()
                with mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                                return_value=backend), \
                     mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                                return_value=binding), \
                     mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                                side_effect=(FakeChild("launcher"),
                                             actual_validate(manifest=manifest, root=root),
                                             actual_validate(manifest=sentinel_manifest,
                                                                 root=sentinel_root))):
                    facade = open_seatbelt_backend_binding(
                        launcher_root=launcher_root,
                        precommitted_launcher_manifest=launcher_manifest,
                        adapter_runtime_root=root,
                        precommitted_adapter_runtime_manifest=manifest,
                        forbidden_exec_sentinel_runtime_root=sentinel_root,
                        precommitted_forbidden_exec_sentinel_manifest=sentinel_manifest)
                try:
                    unseal_runtime(root)
                    entrypoint.unlink(); entrypoint.write_bytes(thin_macho())
                    entrypoint.chmod(0o555); (root / "bin").chmod(0o555); root.chmod(0o555)
                    with self.assertRaisesRegex(ValueError, "identity|changed"):
                        facade.canonical_manifest_bytes()
                finally:
                    facade.close(); unseal_runtime(launcher_root); unseal_runtime(root)
                    unseal_runtime(sentinel_root)

    def test_sentinel_entrypoint_replacement_blocks_existing_public_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            launcher_root = Path(directory) / "launcher-runtime"
            adapter_root = Path(directory) / "adapter-runtime"
            sentinel_root = Path(directory) / "sentinel-runtime"
            with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                    return_value=mock.Mock(sysname="Darwin", machine="arm64")):
                seal_runtime(launcher_root, "bin/launcher")
                launcher_manifest = _observe_asset_manifest_shape(root=launcher_root,
                    asset_kind="runtime", entrypoint="bin/launcher")
                seal_runtime(adapter_root)
                adapter_manifest = _observe_asset_manifest_shape(root=adapter_root,
                    asset_kind="runtime", entrypoint="bin/adapter")
                entrypoint = seal_runtime(sentinel_root,
                    "bin/aegis-forbidden-exec-sentinel")
                sentinel_manifest = _observe_asset_manifest_shape(root=sentinel_root,
                    asset_kind="runtime", entrypoint="bin/aegis-forbidden-exec-sentinel")
                actual_validate = validate_asset_tree
                with mock.patch("aegis360.sparse_story_backend_facade._observe_os_backend",
                                return_value=FakeChild("os")), \
                     mock.patch("aegis360.sparse_story_backend_facade._bind_backend",
                                return_value=FakeBinding()), \
                     mock.patch("aegis360.sparse_story_backend_facade.validate_asset_tree",
                                side_effect=(FakeChild("launcher"),
                                             actual_validate(manifest=adapter_manifest,
                                                             root=adapter_root),
                                             actual_validate(manifest=sentinel_manifest,
                                                             root=sentinel_root))):
                    facade = open_seatbelt_backend_binding(
                        launcher_root=launcher_root,
                        precommitted_launcher_manifest=launcher_manifest,
                        adapter_runtime_root=adapter_root,
                        precommitted_adapter_runtime_manifest=adapter_manifest,
                        forbidden_exec_sentinel_runtime_root=sentinel_root,
                        precommitted_forbidden_exec_sentinel_manifest=sentinel_manifest)
                try:
                    unseal_runtime(sentinel_root)
                    entrypoint.unlink(); entrypoint.write_bytes(thin_macho())
                    entrypoint.chmod(0o555); (sentinel_root / "bin").chmod(0o555)
                    sentinel_root.chmod(0o555)
                    with self.assertRaisesRegex(ValueError, "identity|changed"):
                        facade.canonical_manifest_bytes()
                finally:
                    facade.close(); unseal_runtime(launcher_root); unseal_runtime(adapter_root)
                    unseal_runtime(sentinel_root)

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

    def test_sentinel_requires_exact_runtime_kind_and_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                    return_value=mock.Mock(sysname="Darwin", machine="arm64")):
                seal_runtime(root)
                wrong_entrypoint_manifest = _observe_asset_manifest_shape(
                    root=root, asset_kind="runtime", entrypoint="bin/adapter")
                proof = validate_asset_tree(manifest=wrong_entrypoint_manifest, root=root)
                with self.assertRaisesRegex(ValueError, "sentinel manifest"):
                    _bind_forbidden_exec_sentinel(
                        sentinel_runtime_proof=proof,
                        expected_sentinel_manifest_bytes=
                        canonical_asset_manifest_shape_bytes(wrong_entrypoint_manifest))
                self.assertTrue(proof._closed)
                unseal_runtime(root)

    def test_sentinel_binding_rejects_copy_pickle_and_nonruntime_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel_root = Path(directory) / "sentinel-runtime"
            support_root = Path(directory) / "support"
            with mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                    return_value=mock.Mock(sysname="Darwin", machine="arm64")):
                seal_runtime(sentinel_root, "bin/aegis-forbidden-exec-sentinel")
                sentinel_manifest = _observe_asset_manifest_shape(root=sentinel_root,
                    asset_kind="runtime", entrypoint="bin/aegis-forbidden-exec-sentinel")
                proof = validate_asset_tree(manifest=sentinel_manifest, root=sentinel_root)
                binding = _bind_forbidden_exec_sentinel(
                    sentinel_runtime_proof=proof,
                    expected_sentinel_manifest_bytes=
                    canonical_asset_manifest_shape_bytes(sentinel_manifest))
                try:
                    for operation in (copy.copy, copy.deepcopy, pickle.dumps):
                        with self.assertRaises(TypeError): operation(binding)
                finally:
                    binding.close()
                support_root.mkdir(mode=0o755)
                support = support_root / "support"; support.write_bytes(b"support")
                support.chmod(0o444); support_root.chmod(0o555)
                support_manifest = _observe_asset_manifest_shape(
                    root=support_root, asset_kind="synthetic_support")
                support_proof = validate_asset_tree(manifest=support_manifest,
                                                    root=support_root)
                with self.assertRaisesRegex(ValueError, "sentinel manifest"):
                    _bind_forbidden_exec_sentinel(
                        sentinel_runtime_proof=support_proof,
                        expected_sentinel_manifest_bytes=
                        canonical_asset_manifest_shape_bytes(support_manifest))
                self.assertTrue(support_proof._closed)
                unseal_runtime(sentinel_root); unseal_runtime(support_root)


@unittest.skipUnless(os.environ.get("AEGIS_RUN_HOST_OS_BACKEND_TESTS") == "1",
                     "set AEGIS_RUN_HOST_OS_BACKEND_TESTS=1 for live facade")
class BackendFacadeHostTests(unittest.TestCase):
    def test_real_live_facade_returns_path_free_existing_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "runtime"
            subprocess.run([str(ROOT / "scripts/build_sparse_story_native_launcher.sh"),
                            str(root)], check=True, capture_output=True)
            manifest = _observe_asset_manifest_shape(root=root, asset_kind="runtime",
                entrypoint="bin/aegis-sparse-story-launcher")
            adapter_root = base / "adapter-runtime"
            subprocess.run([str(ROOT / "scripts/build_sparse_story_native_launcher.sh"),
                            str(adapter_root)], check=True, capture_output=True)
            adapter_root.chmod(0o700); (adapter_root / "bin").chmod(0o700)
            (adapter_root / "adapter-role").write_bytes(b"adapter-role-v1\n")
            (adapter_root / "adapter-role").chmod(0o444)
            (adapter_root / "bin").chmod(0o555); adapter_root.chmod(0o555)
            adapter_manifest = _observe_asset_manifest_shape(root=adapter_root,
                asset_kind="runtime", entrypoint="bin/aegis-sparse-story-launcher")
            sentinel_root = base / "sentinel-runtime"
            subprocess.run([str(ROOT / "scripts/build_sparse_story_forbidden_exec_sentinel.sh"),
                            str(sentinel_root)], check=True, capture_output=True)
            sentinel_manifest = _observe_asset_manifest_shape(root=sentinel_root,
                asset_kind="runtime", entrypoint="bin/aegis-forbidden-exec-sentinel")
            try:
                with open_seatbelt_backend_binding(launcher_root=root,
                        precommitted_launcher_manifest=manifest,
                        adapter_runtime_root=adapter_root,
                        precommitted_adapter_runtime_manifest=adapter_manifest,
                        forbidden_exec_sentinel_runtime_root=sentinel_root,
                        precommitted_forbidden_exec_sentinel_manifest=sentinel_manifest) as binding:
                    payload = binding.canonical_manifest_bytes()
                    for forbidden in (b"/Users/", str(root).encode(),
                            str(adapter_root).encode(), str(sentinel_root).encode(),
                            b"bin/aegis-sparse-story-launcher",
                            b"bin/aegis-forbidden-exec-sentinel",
                            b"/usr/bin/sandbox-exec", b"SystemVersion.plist",
                            b"inode", b"mtime", b"ctime"):
                        self.assertNotIn(forbidden, payload)
                    value = json.loads(payload)
                    self.assertEqual(value["schema_version"],
                                     "aegis360.sparse-story-seatbelt-backend-manifest.v1")
            finally:
                (root / "bin").chmod(0o700); root.chmod(0o700)
                (adapter_root / "bin").chmod(0o700); adapter_root.chmod(0o700)
                (sentinel_root / "bin").chmod(0o700); sentinel_root.chmod(0o700)


if __name__ == "__main__": unittest.main()
