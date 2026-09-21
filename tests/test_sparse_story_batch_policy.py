import copy
import hashlib
import os
import pickle
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tests import test_sparse_story_media_tree as media_helpers
from tests.test_sparse_story_media_tree import local_rename
from tests.test_sparse_story_backend_facade import seal_runtime, unseal_runtime
from aegis360.sparse_story_asset_tree import _observe_asset_tree, _observe_asset_manifest_shape
from aegis360.sparse_story_batch_policy import _open_batch_policy_candidate
from aegis360.sparse_story_media_tree import publish_sanitized_bundle
from aegis360.sparse_story_runner_contract import (
    build_runner_policy, build_seatbelt_backend_manifest_shape,
    canonical_seatbelt_backend_manifest_shape_bytes,
)


def batch_args(base, facade, backend_bytes=None):
    helper = media_helpers.SparseStoryMediaTreeTests()
    packets, hashes, index = helper.fixture()
    payloads = helper.payloads(index)
    gate = helper.publish_args(packets, hashes, index)
    bundle = base / "bundle"
    with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive", side_effect=local_rename):
        result = publish_sanitized_bundle(**gate, payloads=payloads, destination=bundle)
    manifests = []
    for name, kind, leaves in (("model", "model", ("weights.bin",)),
            ("prompt", "prompt_schema", ("prompt.txt", "raw-observation-schema.json"))):
        root = base / name
        root.mkdir()
        for leaf in leaves:
            (root / leaf).write_bytes(leaf.encode())
            (root / leaf).chmod(0o444)
        root.chmod(0o555)
        manifests.append(_observe_asset_manifest_shape(root=root, asset_kind=kind))
    (base / "scratch").mkdir(mode=0o700)
    (base / "scratch" / "home").mkdir(mode=0o700)
    (base / "scratch" / "tmp").mkdir(mode=0o700)
    if backend_bytes is None:
        backend_bytes = facade.canonical_manifest_bytes()
    return dict(facade=facade, bundle_root=bundle, **gate,
        payloads=payloads, media_result_bytes=result,
        model_root=base / "model", model_manifest=manifests[0],
        prompt_root=base / "prompt", prompt_manifest=manifests[1],
        scratch_root=base / "scratch", private_home=base / "scratch" / "home",
        private_tmpdir=base / "scratch" / "tmp", runner_policy=build_runner_policy(
            backend_manifest_sha256=hashlib.sha256(backend_bytes).hexdigest()))

class BatchPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(lambda: unseal_runtime(self.base))
        self.host = mock.patch("aegis360.sparse_story_asset_tree.os.uname",
                               return_value=SimpleNamespace(sysname="Darwin", machine="arm64"))
        self.host.start()
        self.addCleanup(self.host.stop)
        runtimes = []
        for name in ("runtime", "sentinel", "launcher"):
            root = self.base / name
            seal_runtime(root)
            proof = _observe_asset_tree(root=root, asset_kind="runtime", entrypoint="bin/adapter")
            self.addCleanup(proof.close)
            runtimes.append(proof)
        backend = canonical_seatbelt_backend_manifest_shape_bytes(
            build_seatbelt_backend_manifest_shape(os_build="synthetic",
                architecture="arm64", backend_executable_sha256="1" * 64,
                backend_executable_size=1, launcher_runtime_manifest_sha256="2" * 64,
                system_version_sha256="3" * 64))
        self.live = SimpleNamespace(canonical_bytes=lambda: backend,
            _adapter_binding=SimpleNamespace(_runtime=runtimes[0]),
            _sentinel_binding=SimpleNamespace(_runtime=runtimes[1]),
            _backend_binding=SimpleNamespace(_runtime=runtimes[2]))
        self.facade_mock = mock.patch("aegis360.sparse_story_batch_policy._require_live",
                                      return_value=self.live)
        self.facade_mock.start(); self.addCleanup(self.facade_mock.stop)
        self.args = batch_args(self.base, object(), backend)

    def candidate(self, **changes):
        result = _open_batch_policy_candidate(**(self.args | changes))
        self.addCleanup(result.close)
        return result

    def test_exact_policy_is_frozen_and_path_free_digest_only(self):
        candidate = self.candidate()
        data = candidate._policy_bytes()
        self.assertEqual(candidate.candidate_sha256(), hashlib.sha256(data).hexdigest())
        self.assertIn(b"(deny default)", data)
        self.assertIn(str(self.args["bundle_root"]).encode(), data)
        self.assertNotIn(str(self.base / "launcher").encode(), data)
        self.assertEqual(data, candidate._policy_bytes())
        self.assertEqual(len(candidate.invocation_binding_sha256()), 64)
        for private_path in (self.args["private_home"], self.args["private_tmpdir"]):
            self.assertNotIn(str(private_path).encode(), candidate._binding_bytes())
        self.assertFalse(hasattr(candidate, "spawn"))
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises(TypeError): operation(candidate)
        candidate.close(); candidate.close()
        with self.assertRaisesRegex(ValueError, "closed"): candidate.candidate_sha256()
        self.assertFalse(self.live._adapter_binding._runtime._closed)

    def test_multi_packet_input_and_invalid_lineage_reject_before_binding(self):
        index = copy.deepcopy(self.args["index"])
        index["packets"].append(copy.deepcopy(index["packets"][0]))
        with self.assertRaisesRegex(ValueError, "exactly one packet"):
            self.candidate(index=index)
        with self.assertRaises(ValueError): self.candidate(salt_hex="6" * 64)
        with self.assertRaisesRegex(ValueError, "does not derive"):
            self.candidate(media_result_bytes=b"{}")

    def test_named_bundle_replacement_rejects(self):
        candidate = self.candidate()
        root = self.args["bundle_root"]
        root.rename(self.base / "old-bundle")
        root.mkdir(mode=0o555)
        with self.assertRaises(ValueError): candidate.candidate_sha256()

    def test_added_bundle_leaf_rejects_even_with_retained_original_descriptors(self):
        candidate = self.candidate()
        root = self.args["bundle_root"]
        root.chmod(0o755)
        (root / "neighbor").write_bytes(b"forbidden")
        (root / "neighbor").chmod(0o444)
        root.chmod(0o555)
        with self.assertRaisesRegex(ValueError, "children changed"):
            candidate.candidate_sha256()

    def test_model_content_replacement_rejects(self):
        candidate = self.candidate()
        path = self.args["model_root"] / "weights.bin"
        path.chmod(0o644); path.write_bytes(b"replacement"); path.chmod(0o444)
        with self.assertRaises(ValueError): candidate.candidate_sha256()

    def test_runtime_path_replacement_rejects(self):
        candidate = self.candidate()
        root = self.base / "runtime"
        root.rename(self.base / "old-runtime")
        seal_runtime(root)
        with self.assertRaises(ValueError): candidate.candidate_sha256()

    def test_renderer_changes_cannot_replace_frozen_policy(self):
        candidate = self.candidate()
        with mock.patch("aegis360.sparse_story_batch_policy.render_seatbelt_policy_input_shape_bytes",
                        return_value=b"(version 1)\n(allow default)\n"):
            with self.assertRaisesRegex(ValueError, "policy bytes changed"):
                candidate.candidate_sha256()

    def test_scratch_writes_allowed_but_mode_and_path_changes_reject(self):
        candidate = self.candidate()
        root = self.args["scratch_root"]
        digest = candidate.candidate_sha256()
        (root / "owned-output").write_bytes(b"scratch")
        self.assertEqual(candidate.candidate_sha256(), digest)
        root.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "scratch root identity"):
            candidate.candidate_sha256()
        root.chmod(0o700)
        root.rename(self.base / "old-scratch")
        root.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, "scratch root identity"):
            candidate.candidate_sha256()

    def test_private_directories_bind_identity_and_must_remain_empty(self):
        candidate = self.candidate()
        digest = candidate.invocation_binding_sha256()
        home = self.args["private_home"]
        (home / "unexpected").write_bytes(b"x")
        with self.assertRaisesRegex(ValueError, "not empty"):
            candidate.invocation_binding_sha256()
        (home / "unexpected").unlink()
        self.assertEqual(candidate.invocation_binding_sha256(), digest)
        tmpdir = self.args["private_tmpdir"]
        tmpdir.rename(self.base / "old-tmp")
        tmpdir.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, "identity"):
            candidate.invocation_binding_sha256()

    def test_runner_policy_and_effective_identity_are_exact(self):
        with self.assertRaises(ValueError):
            self.candidate(runner_policy=self.args["runner_policy"] | {"timeout_ns": 1})
        candidate = self.candidate()
        with mock.patch("aegis360.sparse_story_batch_policy.os.geteuid",
                        return_value=os.geteuid() + 1):
            with self.assertRaisesRegex(ValueError, "user identity"):
                candidate.invocation_binding_sha256()
        with mock.patch("aegis360.sparse_story_batch_policy.os.getegid",
                        return_value=os.getegid() + 1):
            with self.assertRaisesRegex(ValueError, "group identity"):
                candidate.invocation_binding_sha256()

    def test_request_binding_changes_with_projection_and_never_exposes_request(self):
        candidate = self.candidate()
        first = candidate.invocation_binding_sha256()
        changed = copy.deepcopy(self.args["index"])
        changed["packets"][0]["projection"]["rows"][0]["views"].reverse()
        with self.assertRaises(ValueError): self.candidate(index=changed)
        self.assertNotIn(candidate._request_bytes, candidate._binding_bytes())
        self.assertEqual(first, candidate.invocation_binding_sha256())

    def test_alias_and_overlap_rejected(self):
        alias = self.base / "alias"
        alias.symlink_to(self.args["model_root"], target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "canonical filesystem"):
            self.candidate(model_root=alias)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.candidate(scratch_root=self.base)
        outside = self.base / "outside-home"
        outside.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, "beneath scratch"):
            self.candidate(private_home=outside)

    def test_closed_facade_and_factory_failure_release_owned_proofs(self):
        candidate = self.candidate()
        with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                        side_effect=ValueError("closed facade")):
            with self.assertRaisesRegex(ValueError, "closed facade"):
                candidate.candidate_sha256()
        observed = []
        from aegis360.sparse_story_batch_policy import validate_asset_tree
        def record(**kwargs):
            proof = validate_asset_tree(**kwargs)
            observed.append(proof)
            return proof
        with mock.patch("aegis360.sparse_story_batch_policy.validate_asset_tree", side_effect=record):
            with self.assertRaises(ValueError): self.candidate(scratch_root=self.base)
        self.assertEqual(len(observed), 3)
        self.assertTrue(all(proof._closed for proof in observed))

    def test_factory_failure_closes_private_directories(self):
        opened = []
        from aegis360 import sparse_story_batch_policy as module
        original = module._PrivateDirectory
        class RecordingDirectory(original):
            def __init__(self, root):
                super().__init__(root); opened.append(self)
        with mock.patch.object(module, "_PrivateDirectory", RecordingDirectory):
            with self.assertRaisesRegex(ValueError, "not overlap"):
                self.candidate(private_tmpdir=self.args["private_home"])
        self.assertEqual(len(opened), 2)
        self.assertTrue(all(item.closed for item in opened))


if __name__ == "__main__":
    unittest.main()
