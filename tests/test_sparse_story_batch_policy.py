import copy
from contextlib import ExitStack
import hashlib
import json
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
from aegis360.sparse_story_probe_context import _ProbeContext
from aegis360.sparse_story_probe_listeners import _ProbeListeners
from aegis360.sparse_story_probe_sentinels import (
    _OutsideSentinelSnapshot, _ReadDenialSentinel, _ScratchProbeSnapshot,
    _OwnedBatchScratch,
)
from aegis360.sparse_story_raw_probe_transport import _RawProbeCapture
from aegis360.sparse_story_media_tree import (
    publish_sanitized_bundle, publish_selected_one_packet_media_gate,
)
from aegis360.sparse_story_runner_contract import (
    build_runner_policy, build_seatbelt_backend_manifest_shape,
    canonical_seatbelt_backend_manifest_shape_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


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

    def owned_scratch_candidate(self):
        owner = _OwnedBatchScratch(self.base)
        self.addCleanup(owner.abandon)
        candidate = self.candidate(scratch_root=owner.root,
            private_home=owner.home, private_tmpdir=owner.tmpdir)
        owner.bind(candidate)
        return owner, candidate

    def test_owned_batch_scratch_cleans_after_candidate_and_group_close(self):
        owner, candidate = self.owned_scratch_candidate()
        owner.revalidate()
        capture = _RawProbeCapture(b"", 0, True, False, False, "test")
        candidate.close()
        owner.finish_after_candidate_close(candidate, capture)
        self.assertFalse(owner.root.exists())

    def test_owned_batch_scratch_preserves_changed_or_live_tree(self):
        capture = _RawProbeCapture(b"", 0, True, False, False, "test")
        owner, candidate = self.owned_scratch_candidate()
        with self.assertRaisesRegex(ValueError, "owner closure"):
            owner.finish_after_candidate_close(candidate, capture)
        self.assertTrue(owner.root.exists())
        owner, candidate = self.owned_scratch_candidate()
        candidate.close()
        live_group = _RawProbeCapture(b"", 0, False, False, False, "test")
        with self.assertRaisesRegex(ValueError, "owner closure"):
            owner.finish_after_candidate_close(candidate, live_group)
        self.assertTrue(owner.root.exists())
        owner, candidate = self.owned_scratch_candidate()
        other = self.candidate(scratch_root=owner.root,
            private_home=owner.home, private_tmpdir=owner.tmpdir)
        other.close()
        with self.assertRaisesRegex(ValueError, "owner closure"):
            owner.finish_after_candidate_close(other, capture)
        self.assertTrue(owner.root.exists())
        owner, candidate = self.owned_scratch_candidate()
        candidate.close()
        extra = owner.root / "unexpected"
        extra.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "root changed"):
            owner.finish_after_candidate_close(candidate, capture)
        self.assertEqual(extra.read_bytes(), b"keep")
        owner, candidate = self.owned_scratch_candidate()
        candidate.close()
        private_artifact = owner.home / "unexpected"
        private_artifact.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "private directory changed"):
            owner.finish_after_candidate_close(candidate, capture)
        self.assertEqual(private_artifact.read_bytes(), b"keep")

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

    def test_selected_full_set_bundle_is_retained_as_one_packet_candidate(self):
        helper = media_helpers.SparseStoryMediaTreeTests()
        packets, hashes, index = media_helpers.projection_helpers.SparseStoryProjectionTests().build(6)
        payloads = helper.payloads(index)
        full = self.base / "full-bundle"
        selected = self.base / "selected-bundle"
        selected_result = self.base / "selected-result.json"
        with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive",
                side_effect=local_rename):
            full_result = publish_sanitized_bundle(index=index,
                private_packets=packets, ordered_private_packet_sha256s=hashes,
                salt_hex="5" * 64, payloads=payloads, destination=full)
            _, one, chosen, chosen_hashes, chosen_payloads = (
                publish_selected_one_packet_media_gate(result_bytes=full_result,
                    index=index, private_packets=packets,
                    ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                    payloads=payloads, bundle=full, presentation_ordinal=6,
                    bundle_destination=selected,
                    result_destination=selected_result))
        candidate = self.candidate(bundle_root=selected, index=one,
            private_packets=chosen, ordered_private_packet_sha256s=chosen_hashes,
            payloads=chosen_payloads,
            media_result_bytes=selected_result.read_bytes())
        policy = candidate._policy_bytes()
        self.assertIn(str(selected).encode(), policy)
        self.assertNotIn(str(full).encode(), policy)
        self.assertEqual(len(candidate.invocation_binding_sha256()), 64)
        leaf = next((selected / "media").glob("*/*.png"))
        leaf.chmod(0o644)
        leaf.write_bytes(b"changed")
        with self.assertRaises(ValueError): candidate.invocation_binding_sha256()

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

    def test_allowed_probe_leaves_derive_from_retained_files_and_revalidate(self):
        candidate = self.candidate()
        selected = candidate._allowed_probe_leaves()
        self.assertEqual(len(selected), 3)
        self.assertTrue(selected[0].path.is_relative_to(self.args["bundle_root"]))
        self.assertEqual([row.path.parent for row in selected[1:]],
            [self.args["model_root"], self.args["prompt_root"]])
        self.assertEqual(selected[2].path.name, "prompt.txt")
        self.assertEqual(selected[0].path.relative_to(self.args["bundle_root"]).as_posix(),
                         json.loads(candidate._request_bytes)["media"][0]["path"])
        for row in selected:
            self.assertTrue(row.prefix)
            with row.path.open("rb") as source:
                self.assertEqual(source.read(128), row.prefix)
        model = self.args["model_root"] / "weights.bin"
        model.chmod(0o644)
        model.write_bytes(b"tampered")
        model.chmod(0o444)
        with self.assertRaises(ValueError): candidate._allowed_probe_leaves()

    def test_probe_context_binds_exact_args_and_post_execution_facts(self):
        candidate = self.candidate()
        outside = self.base / "outside"
        outside.mkdir(mode=0o700)
        (outside / "outside-existing").write_bytes(b"outside-existing-sentinel-v1")
        (outside / "outside-existing").chmod(0o600)
        scratch = self.args["scratch_root"]
        (scratch / "rename-source").write_bytes(b"rename-source-v1")
        (scratch / "rename-source").chmod(0o600)
        denied = self.base / "denied"
        denied.mkdir(mode=0o700)
        for name in ("neighbor", "result"):
            (denied / name).write_bytes(name.encode())
            (denied / name).chmod(0o600)
        listener_root = self.base / "listeners"
        listener_root.mkdir(mode=0o700)
        with ExitStack() as stack:
            reads = [stack.enter_context(_ReadDenialSentinel(path)) for path in (
                ROOT / "src/aegis360/sparse_story_batch_policy.py",
                ROOT / "docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md",
                denied / "neighbor", denied / "result")]
            outside_proof = stack.enter_context(_OutsideSentinelSnapshot(outside))
            scratch_proof = stack.enter_context(_ScratchProbeSnapshot(scratch,
                self.args["private_home"], self.args["private_tmpdir"]))
            try: listeners = stack.enter_context(_ProbeListeners(listener_root))
            except PermissionError as error:
                self.skipTest(f"host policy denies local listener bind: {error.errno}")
            with self.assertRaisesRegex(ValueError, "fixed source leaves"):
                _ProbeContext(candidate=candidate, repository=reads[2],
                    protocol=reads[1], neighbor=reads[0], result=reads[3],
                    outside=outside_proof, scratch=scratch_proof,
                    listeners=listeners)
            context = _ProbeContext(candidate=candidate, repository=reads[0],
                protocol=reads[1], neighbor=reads[2], result=reads[3],
                outside=outside_proof, scratch=scratch_proof, listeners=listeners)
            argv = context.argv_suffix()
            self.assertEqual((len(argv), argv[0], argv[5:9]),
                (19, "--aegis-isolation-probe", tuple(str(row.path) for row in reads)))
            self.assertEqual(argv[16], str(listeners.unix_path))
            (scratch / "scratch-write").write_bytes(b"scratch-write-sentinel-v1")
            (scratch / "scratch-write").chmod(0o600)
            context.postvalidate()
            (denied / "neighbor").write_bytes(b"changed")
            with self.assertRaises(ValueError): context.postvalidate()

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
