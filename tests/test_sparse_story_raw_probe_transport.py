import os
import hashlib
import json
import signal
import subprocess
import sys
import time
import unittest
from dataclasses import replace
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_asset_tree import (  # noqa: E402
    _observe_asset_manifest_shape, validate_asset_tree,
)
from aegis360.sparse_story_probe_context import _ProbeContext  # noqa: E402
from aegis360.sparse_story_probe_denials import (  # noqa: E402
    _OwnedOnePacketNeighbor, _retain_full_set_denials,
    _run_owned_full_set_batch_probe, _open_retained_probed_batch,
)
from aegis360.sparse_story_media_tree import (  # noqa: E402
    publish_sanitized_media_gate, publish_selected_one_packet_media_gate,
)
from aegis360.sparse_story_probe_listeners import _OwnedProbeListeners  # noqa: E402
from aegis360.sparse_story_probe_sentinels import (  # noqa: E402
    _OwnedOutsideSentinel, _OwnedScratchProbeFiles, _OwnedBatchScratch,
    _ReadDenialSentinel,
)
from aegis360.sparse_story_probe_transcript import (  # noqa: E402
    _check_probe_row_values, parse_isolation_probe_transcript,
)
from aegis360.sparse_story_raw_probe_transport import (  # noqa: E402
    _RawProbeCapture, _run_raw_probe, _run_owned_raw_probe,
    _run_native_process,
)
from aegis360.sparse_story_runner_contract import MATRIX_KEYS  # noqa: E402
from tests import test_sparse_story_batch_policy as batch_policy_tests  # noqa: E402
from tests import test_sparse_story_projection as projection_tests  # noqa: E402
from tests import test_sparse_story_media_tree as media_tests  # noqa: E402


@unittest.skipUnless(os.uname().sysname == "Darwin" and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class RawProbeTransportHostTests(unittest.TestCase):
    @contextmanager
    def context(self, *, one_packet=False, presentation_ordinal=6,
                own_batch_scratch=False, coordinated=False):
        fixture = batch_policy_tests.BatchPolicyTests(
            "test_exact_policy_is_frozen_and_path_free_digest_only")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        base = fixture.base
        batch_scratch_owner = None
        if own_batch_scratch:
            batch_scratch_owner = _OwnedBatchScratch(base)
            self.addCleanup(batch_scratch_owner.abandon)
            fixture.args.update(scratch_root=batch_scratch_owner.root,
                private_home=batch_scratch_owner.home,
                private_tmpdir=batch_scratch_owner.tmpdir)
        if not one_packet:
            packets, hashes, index = projection_tests.SparseStoryProjectionTests().build(6)
            payloads = media_tests.SparseStoryMediaTreeTests().payloads(index)
            full_bundle = base / "full-bundle"
            full_result = base / "full-result.json"
            selected_bundle = base / "selected-bundle"
            selected_result = base / "selected-result.json"
            with mock.patch("aegis360.sparse_story_media_tree._rename_exclusive",
                    side_effect=media_tests.local_rename):
                publish_sanitized_media_gate(index=index, private_packets=packets,
                    ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                    payloads=payloads, bundle_destination=full_bundle,
                    result_destination=full_result)
                _, one, chosen, chosen_hashes, chosen_payloads = (
                    publish_selected_one_packet_media_gate(
                        result_bytes=full_result.read_bytes(), index=index,
                        private_packets=packets,
                        ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                        payloads=payloads, bundle=full_bundle,
                        presentation_ordinal=presentation_ordinal,
                        bundle_destination=selected_bundle,
                        result_destination=selected_result))
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
            if one_packet:
                candidate = fixture.candidate()
            else:
                candidate = fixture.candidate(bundle_root=selected_bundle, index=one,
                    private_packets=chosen,
                    ordered_private_packet_sha256s=chosen_hashes,
                    payloads=chosen_payloads,
                    media_result_bytes=selected_result.read_bytes())
            if batch_scratch_owner is not None:
                batch_scratch_owner.bind(candidate)
            outside_owner = _OwnedOutsideSentinel(base)
            stack.callback(outside_owner.abandon)
            scratch = fixture.args["scratch_root"]
            scratch_owner = _OwnedScratchProbeFiles(scratch,
                fixture.args["private_home"], fixture.args["private_tmpdir"])
            stack.callback(scratch_owner.abandon)
            listener_owner = _OwnedProbeListeners(base)
            stack.callback(listener_owner.abandon)
            static_reads = [stack.enter_context(_ReadDenialSentinel(path)) for path in (
                ROOT / "src/aegis360/sparse_story_batch_policy.py",
                ROOT / "docs/experiments/sparse-story-semantic-successor-v1-2026-09-07.md")]
            if coordinated:
                if one_packet or batch_scratch_owner is None:
                    raise ValueError("coordinated fixture requires owned full set")
                yield dict(candidate=candidate, batch_scratch=batch_scratch_owner,
                    outside=outside_owner, scratch=scratch_owner,
                    listeners=listener_owner, repository=static_reads[0],
                    protocol=static_reads[1], denial_source=dict(
                        result_bytes=full_result.read_bytes(), index=index,
                        private_packets=packets,
                        ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                        payloads=payloads, bundle=full_bundle,
                        result_path=full_result))
                return
            if one_packet:
                decoy = _OwnedOnePacketNeighbor(candidate=candidate, parent=base)
                stack.callback(decoy.abandon)
                single_result = base / "single-result.json"
                single_result.write_bytes(fixture.args["media_result_bytes"])
                single_result.chmod(0o600)
                neighbor = decoy.proof
                result = stack.enter_context(_ReadDenialSentinel(single_result))
            else:
                neighbor, result = stack.enter_context(_retain_full_set_denials(
                    candidate=candidate, result_bytes=full_result.read_bytes(),
                    index=index, private_packets=packets,
                    ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                    payloads=payloads, bundle=full_bundle,
                    result_path=full_result))
            reads = (*static_reads, neighbor, result)
            context = _ProbeContext(candidate=candidate, repository=reads[0],
                protocol=reads[1], neighbor=reads[2], result=reads[3],
                outside=outside_owner.snapshot,
                scratch=scratch_owner.snapshot,
                listeners=listener_owner.listeners)
            if one_packet: context.owned_neighbor = decoy
            context.owned_outside = outside_owner
            context.owned_listeners = listener_owner
            context.owned_scratch = scratch_owner
            context.owned_batch_scratch = batch_scratch_owner
            yield context

    def test_same_retained_runtime_probes_through_native_launcher(self):
        with self.context() as context:
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertTrue(capture.completed, capture.reason)
            self.assertTrue(capture.group_gone)
            self.assertEqual((capture.returncode, capture.postcheck_passed), (0, True))
            rows = parse_isolation_probe_transcript(capture.stdout)
            allowed = context.allowed
            primitive = _check_probe_row_values(rows,
                bundle_prefix=allowed[0].prefix, model_prefix=allowed[1].prefix,
                prompt_prefix=allowed[2].prefix)
            self.assertTrue(all(primitive.values()), primitive)
            self.assertFalse(context.owned_outside.root.exists())
            self.assertFalse(context.owned_listeners.root.exists())
            self.assertFalse(context.owned_scratch.snapshot.source_path.exists())

    def test_one_packet_smoke_uses_owned_decoy_and_cleans_after_reap(self):
        with self.context(one_packet=True) as context:
            decoy = context.owned_neighbor
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners, neighbor=decoy)
            self.assertTrue(capture.completed, capture.reason)
            self.assertFalse(decoy.root.exists())
            self.assertFalse(context.owned_outside.root.exists())
            self.assertFalse(context.owned_listeners.root.exists())
            self.assertFalse(context.owned_scratch.snapshot.source_path.exists())

    def test_first_full_set_packet_denies_actual_other_packet(self):
        with self.context(presentation_ordinal=1) as context:
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertTrue(capture.completed, capture.reason)
            self.assertTrue(context.reads[2].path.exists())
            self.assertFalse(context.owned_outside.root.exists())

    def test_batch_scratch_root_closes_after_native_probe_and_candidate(self):
        with self.context(own_batch_scratch=True) as context:
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertTrue(capture.completed, capture.reason)
            owner = context.owned_batch_scratch
            self.assertTrue(owner.root.exists())
            candidate = context.candidate
        candidate.close()
        owner.finish_after_candidate_close(candidate, capture)
        self.assertFalse(owner.root.exists())

    def test_batch_scratch_root_closes_after_no_write_timeout(self):
        with self.context(own_batch_scratch=True) as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS", 1):
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertFalse(capture.completed)
            self.assertTrue(capture.group_gone)
            self.assertFalse(context.owned_scratch.snapshot.source_path.exists())
            owner = context.owned_batch_scratch
            candidate = context.candidate
        candidate.close()
        owner.finish_after_candidate_close(candidate, capture)
        self.assertFalse(owner.root.exists())

    def test_coordinator_owns_full_set_success_and_timeout_cleanup(self):
        for timeout in (False, True):
            with self.subTest(timeout=timeout), self.context(
                    own_batch_scratch=True, coordinated=True) as inputs:
                owner = inputs["batch_scratch"]
                with mock.patch("aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS",
                        1 if timeout else 120_000_000_000):
                    capture = _run_owned_full_set_batch_probe(**inputs)
                self.assertEqual(capture.completed, not timeout)
                self.assertTrue(capture.group_gone)
                self.assertTrue(inputs["candidate"]._closed)
            self.assertFalse(owner.root.exists())

    def test_retained_probe_preserves_candidate_until_terminal_close(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            candidate = inputs["candidate"]
            root = inputs["batch_scratch"].root
            self.assertFalse(candidate._closed)
            self.assertTrue(root.exists())
            session.revalidate()
            claim = session.claim_once()
            claim.revalidate()
            receipt = json.loads(claim.receipt_bytes())
            self.assertEqual(receipt["compiled_policy_sha256"],
                hashlib.sha256(candidate._policy_bytes()).hexdigest())
            self.assertEqual(receipt["backend_manifest_sha256"],
                hashlib.sha256(candidate._backend_bytes).hexdigest())
            self.assertEqual(receipt["runner_policy_sha256"],
                hashlib.sha256(candidate._runner_policy_bytes).hexdigest())
            self.assertEqual(set(receipt["matrix"]), set(MATRIX_KEYS))
            self.assertTrue(all(value is True for value in receipt["matrix"].values()))
            with self.assertRaisesRegex(ValueError, "already claimed"):
                session.claim_once()
            self.assertFalse(inputs["outside"].root.exists())
            self.assertFalse(inputs["listeners"].root.exists())
            session.close()
            self.assertTrue(candidate._closed)
            self.assertFalse(root.exists())
            with self.assertRaises(ValueError):
                session.revalidate()
            with self.assertRaises(ValueError):
                claim.revalidate()
            with self.assertRaises(ValueError):
                claim.receipt_bytes()

    def test_retained_probe_rejects_changed_batch_before_close(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            root = inputs["batch_scratch"].root
            (root / "home" / "unexpected").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                session.revalidate()
            with self.assertRaises(ValueError):
                session.claim_once()
            with self.assertRaises(ValueError):
                session.close()
            self.assertTrue(root.exists())
            self.assertTrue(inputs["candidate"]._closed)

    def test_claim_runs_one_fixed_native_synthetic_case(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            capture = claim._run_fixed_synthetic_fd_case_once()
            self.assertTrue(capture.completed, capture.reason)
            self.assertEqual(capture.returncode, 0)
            self.assertTrue(capture.group_gone)
            self.assertIn(b'"status":"abstain"', capture.stdout)
            with self.assertRaisesRegex(ValueError, "already invoked"):
                claim._run_fixed_synthetic_fd_case_once()
            session.close()
            self.assertFalse(inputs["batch_scratch"].root.exists())

    def test_claim_refuses_changed_home_before_synthetic_spawn(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            root = inputs["batch_scratch"].root
            (root / "home" / "unexpected").write_bytes(b"changed")
            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_native_process"
                    ) as launch, self.assertRaises(ValueError):
                claim._run_fixed_synthetic_fd_case_once()
            launch.assert_not_called()
            with self.assertRaises(ValueError):
                session.close()
            self.assertTrue(root.exists())

    def test_claim_handles_simultaneous_policy_request_and_stdout(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            capture = claim._run_fixed_synthetic_pipe_case_once()
            self.assertTrue(capture.completed, capture.reason)
            self.assertEqual(len(capture.stdout), 60_000)
            self.assertTrue(capture.group_gone)
            session.close()
            self.assertFalse(inputs["batch_scratch"].root.exists())

    def test_claim_cleans_exact_synthetic_scratch_write(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            capture = claim._run_fixed_synthetic_scratch_case_once()
            self.assertTrue(capture.completed, capture.reason)
            self.assertTrue(capture.group_gone)
            self.assertFalse((inputs["batch_scratch"].root / "synthetic-write").exists())
            session.close()
            self.assertFalse(inputs["batch_scratch"].root.exists())

    def test_claim_preserves_unexpected_synthetic_scratch_content(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            real_run = _run_native_process

            def changed_content(*args, **kwargs):
                capture = real_run(*args, **kwargs)
                (inputs["batch_scratch"].root / "synthetic-write").write_bytes(b"changed")
                return capture

            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_native_process",
                    side_effect=changed_content), self.assertRaises(ValueError):
                claim._run_fixed_synthetic_scratch_case_once()
            with self.assertRaises(ValueError):
                session.close()
            self.assertEqual((inputs["batch_scratch"].root / "synthetic-write").read_bytes(),
                b"changed")

    def test_claim_preserves_scratch_without_inference_group_absence(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            real_run = _run_native_process

            def missing_group_proof(*args, **kwargs):
                return replace(real_run(*args, **kwargs), group_gone=False)

            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_native_process",
                    side_effect=missing_group_proof):
                capture = claim._run_fixed_synthetic_scratch_case_once()
            self.assertFalse(capture.group_gone)
            with self.assertRaises(ValueError):
                session.close()
            self.assertTrue((inputs["batch_scratch"].root / "synthetic-write").exists())

    def test_claim_preserves_empty_batch_without_inference_group_absence(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            real_run = _run_native_process

            def missing_group_proof(*args, **kwargs):
                return replace(real_run(*args, **kwargs), group_gone=False)

            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_native_process",
                    side_effect=missing_group_proof):
                capture = claim._run_fixed_synthetic_fd_case_once()
            self.assertFalse(capture.group_gone)
            with self.assertRaisesRegex(ValueError, "group absence is unverified"):
                session.close()
            self.assertTrue(inputs["batch_scratch"].root.exists())
            self.assertTrue(inputs["candidate"]._closed)

    def test_retained_probe_timeout_closes_candidate_and_owned_root(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            root = inputs["batch_scratch"].root
            with mock.patch("aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS", 1):
                with self.assertRaisesRegex(ValueError, "raw probe is incomplete"):
                    _open_retained_probed_batch(**inputs)
            self.assertTrue(inputs["candidate"]._closed)
            self.assertFalse(root.exists())

    def test_retained_probe_rejects_changed_result_before_launch(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            inputs["denial_source"]["result_bytes"] = b"changed"
            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_raw_probe"
                    ) as launch, self.assertRaises(ValueError):
                _open_retained_probed_batch(**inputs)
            launch.assert_not_called()
            self.assertTrue(inputs["candidate"]._closed)
            self.assertTrue(inputs["batch_scratch"].root.exists())

    def test_coordinator_refuses_changed_full_set_before_launch(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            inputs["denial_source"]["result_bytes"] = b"changed"
            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_raw_probe"
                    ) as launch, self.assertRaises(ValueError):
                _run_owned_full_set_batch_probe(**inputs)
            launch.assert_not_called()
            self.assertTrue(inputs["candidate"]._closed)
            self.assertTrue(inputs["batch_scratch"].root.exists())
            self.assertTrue(inputs["batch_scratch"].closed)
            self.assertTrue(inputs["outside"].closed)
            self.assertTrue(inputs["scratch"].closed)
            self.assertTrue(inputs["listeners"].closed)

    def test_coordinator_invalidates_changed_batch_scratch_after_probe(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            owner = inputs["batch_scratch"]
            original = owner.finish_after_candidate_close

            def change_home(candidate, capture):
                (owner.home / "unexpected").write_bytes(b"changed")
                return original(candidate, capture)

            with mock.patch.object(owner, "finish_after_candidate_close",
                    side_effect=change_home):
                capture = _run_owned_full_set_batch_probe(**inputs)
            self.assertFalse(capture.completed)
            self.assertEqual(capture.reason, "batch_scratch_cleanup_invalid")
            self.assertTrue(owner.root.exists())

    def test_coordinator_preserves_batch_root_if_candidate_close_fails(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            candidate = inputs["candidate"]
            original = candidate.close

            def close_then_fail():
                original()
                raise OSError("candidate close failed")

            with mock.patch.object(candidate, "close", side_effect=close_then_fail):
                with self.assertRaisesRegex(OSError, "candidate close failed"):
                    _run_owned_full_set_batch_probe(**inputs)
            self.assertTrue(inputs["batch_scratch"].closed)
            self.assertTrue(inputs["batch_scratch"].root.exists())

    def test_coordinator_detects_postprobe_full_set_mutation(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            real_run = _run_owned_raw_probe

            def change_result_after_probe(context, **owners):
                capture = real_run(context, **owners)
                inputs["denial_source"]["result_path"].chmod(0o600)
                return capture

            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_owned_raw_probe",
                    side_effect=change_result_after_probe):
                with self.assertRaises(ValueError):
                    _run_owned_full_set_batch_probe(**inputs)
            self.assertTrue(inputs["candidate"]._closed)
            self.assertTrue(inputs["batch_scratch"].closed)
            self.assertTrue(inputs["batch_scratch"].root.exists())

    def test_coordinator_preserves_owned_trees_without_group_absence(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            with mock.patch("aegis360.sparse_story_raw_probe_transport._run_raw_probe",
                    return_value=_RawProbeCapture(b"", 0, False, False, False,
                        "raw_probe_invalid")):
                capture = _run_owned_full_set_batch_probe(**inputs)
            self.assertFalse(capture.completed)
            self.assertEqual(capture.reason, "batch_scratch_cleanup_invalid")
            self.assertTrue(inputs["candidate"]._closed)
            for owner in (inputs["batch_scratch"], inputs["outside"],
                    inputs["scratch"], inputs["listeners"]):
                self.assertTrue(owner.closed)
                self.assertTrue(owner.root.exists())

    def test_coordinator_preserves_batch_root_after_inner_cleanup_refusal(self):
        with self.context(own_batch_scratch=True, coordinated=True) as inputs:
            scratch = inputs["scratch"]
            source = scratch.snapshot.source_path
            with mock.patch.object(scratch, "finish_after_reap",
                    side_effect=ValueError("scratch cleanup refused")):
                capture = _run_owned_full_set_batch_probe(**inputs)
            self.assertFalse(capture.completed)
            self.assertEqual(capture.reason, "batch_scratch_cleanup_invalid")
            self.assertTrue(source.exists())
            self.assertTrue(inputs["batch_scratch"].root.exists())
            self.assertTrue(inputs["candidate"]._closed)

    def test_owned_cleanup_failure_invalidates_raw_completion(self):
        with self.context() as context, mock.patch.object(
                context.owned_scratch, "finish_after_reap",
                side_effect=ValueError("cleanup refused")):
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertFalse(capture.completed)
            self.assertEqual(capture.reason, "raw_probe_cleanup_invalid")
            self.assertTrue(context.owned_scratch.snapshot.source_path.exists())
            self.assertFalse(context.owned_outside.root.exists())
            self.assertFalse(context.owned_listeners.root.exists())

    def test_owned_paths_are_preserved_without_group_absence(self):
        with self.context() as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport._run_raw_probe",
                return_value=_RawProbeCapture(b"", 0, False, False, False,
                    "raw_probe_invalid")):
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertEqual(capture.reason, "raw_probe_cleanup_unverified")
            self.assertTrue(context.owned_scratch.snapshot.source_path.exists())
            self.assertTrue(context.owned_outside.root.exists())
            self.assertTrue(context.owned_listeners.root.exists())

    def test_timeout_before_policy_delivery_fails_without_adapter_output(self):
        with self.context() as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS", 1):
            capture = _run_raw_probe(context)
            self.assertFalse(capture.completed)
            self.assertFalse(capture.postcheck_passed)
            self.assertEqual(capture.stdout, b"")

    def test_owned_timeout_cleans_source_when_write_is_absent(self):
        with self.context() as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS", 1):
            capture = _run_owned_raw_probe(context,
                outside=context.owned_outside, scratch=context.owned_scratch,
                listeners=context.owned_listeners)
            self.assertFalse(capture.completed)
            self.assertIsInstance(capture.returncode, int)
            self.assertFalse(context.owned_scratch.snapshot.source_path.exists())
            self.assertFalse(context.owned_outside.root.exists())
            self.assertFalse(context.owned_listeners.root.exists())

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

    def test_other_packet_leaf_mutation_invalidates_completed_probe(self):
        with self.assertRaisesRegex(ValueError, "read-denial sentinel identity changed"):
            with self.context() as context:
                original = _ProbeContext.postvalidate

                def mutate_neighbor_before_validation(probe):
                    path = probe.reads[2].path
                    path.chmod(0o644)
                    path.write_bytes(b"changed other packet")
                    return original(probe)

                with mock.patch.object(_ProbeContext, "postvalidate",
                        mutate_neighbor_before_validation):
                    capture = _run_raw_probe(context)
                self.assertEqual(capture.returncode, 0)
                self.assertFalse(capture.postcheck_passed)
                self.assertFalse(capture.completed)

    def test_failed_primitive_value_invalidates_complete_transport(self):
        with self.context() as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport._check_probe_row_values",
                return_value={key: key != "allowed_bundle_read"
                    for key in MATRIX_KEYS}):
            capture = _run_raw_probe(context)
            self.assertEqual(capture.returncode, 0)
            self.assertTrue(capture.postcheck_passed)
            self.assertFalse(capture.completed)

    def test_wrong_or_nonboolean_matrix_invalidates_complete_transport(self):
        all_true = {key: True for key in MATRIX_KEYS}
        wrong_key = dict(all_true)
        wrong_key.pop("allowed_bundle_read")
        wrong_key["unrecognized"] = True
        truthy_integer = dict(all_true)
        truthy_integer["allowed_bundle_read"] = 1
        for matrix in (wrong_key, truthy_integer):
            with self.subTest(matrix=matrix), self.context() as context, mock.patch(
                    "aegis360.sparse_story_raw_probe_transport._check_probe_row_values",
                    return_value=matrix):
                capture = _run_raw_probe(context)
                self.assertEqual(capture.returncode, 0)
                self.assertTrue(capture.postcheck_passed)
                self.assertFalse(capture.completed)

    def test_changed_request_bytes_invalidate_completed_probe(self):
        with self.assertRaisesRegex(ValueError, "full-set denial source changed"):
            with self.context() as context:
                original = _ProbeContext.postvalidate

                def mutate_request_before_validation(probe):
                    probe.candidate._request_bytes += b" "
                    return original(probe)

                with mock.patch.object(_ProbeContext, "postvalidate",
                        mutate_request_before_validation):
                    capture = _run_raw_probe(context)
                self.assertEqual(capture.returncode, 0)
                self.assertFalse(capture.postcheck_passed)
                self.assertFalse(capture.completed)

    def test_malformed_rows_invalidate_complete_transport(self):
        with self.context() as context, mock.patch(
                "aegis360.sparse_story_raw_probe_transport.parse_isolation_probe_transcript",
                side_effect=ValueError("malformed row")):
            capture = _run_raw_probe(context)
            self.assertEqual(capture.returncode, 0)
            self.assertTrue(capture.postcheck_passed)
            self.assertFalse(capture.completed)

    def test_exited_leader_does_not_leave_live_descendant(self):
        with self.context() as context:
            marker = context.outside.root.parent / "owned-grandchild-pid"
            script = ("import os,time\n"
                "child=os.fork()\n"
                "if child == 0:\n"
                " os.close(1); os.close(2)\n"
                " time.sleep(30)\n"
                " os._exit(0)\n"
                f"open({str(marker)!r},'w').write(str(child))\n"
                "time.sleep(0.2)\n"
                "os._exit(0)\n")
            real_popen = subprocess.Popen
            owned = []

            def launch_descendant(_argv, **_kwargs):
                process = real_popen([sys.executable, "-c", script],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True,
                    start_new_session=True)
                owned.append(process)
                return process

            try:
                with mock.patch("aegis360.sparse_story_raw_probe_transport.subprocess.Popen",
                        side_effect=launch_descendant):
                    capture = _run_raw_probe(context)
                self.assertFalse(capture.completed)
                self.assertTrue(marker.exists())
                child_pid = int(marker.read_text())
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    try: os.getpgid(child_pid)
                    except ProcessLookupError: break
                    time.sleep(0.02)
                else:
                    self.fail("probe left a live descendant")
            finally:
                if owned and marker.exists():
                    child_pid = int(marker.read_text())
                    try:
                        if os.getpgid(child_pid) == owned[0].pid:
                            os.kill(child_pid, 9)
                    except ProcessLookupError:
                        pass

    def test_term_ignoring_probe_is_killed_after_grace(self):
        with self.context() as context:
            script = ("import os,signal,time\n"
                "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
                "os.write(1,b'ready\\n')\n"
                "time.sleep(30)\n")
            real_popen = subprocess.Popen
            owned = []

            def launch_ignore_term(_argv, **_kwargs):
                process = real_popen([sys.executable, "-c", script],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True,
                    start_new_session=True)
                owned.append(process)
                return process

            try:
                with mock.patch("aegis360.sparse_story_raw_probe_transport.subprocess.Popen",
                        side_effect=launch_ignore_term), mock.patch(
                        "aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS",
                        500_000_000), mock.patch(
                        "aegis360.sparse_story_raw_probe_transport._GRACE_NS",
                        50_000_000):
                    capture = _run_raw_probe(context)
                self.assertFalse(capture.completed)
                self.assertEqual(capture.stdout, b"ready\n")
                self.assertEqual(capture.returncode, -signal.SIGKILL)
                with self.assertRaises(ProcessLookupError):
                    os.killpg(owned[0].pid, 0)
            finally:
                if owned and owned[0].returncode is None:
                    os.kill(owned[0].pid, signal.SIGKILL)
                    owned[0].wait(timeout=2)

    def test_stdout_capture_stops_at_one_byte_beyond_limit(self):
        with self.context() as context:
            real_popen = subprocess.Popen

            def launch_large_output(_argv, **_kwargs):
                return real_popen([sys.executable, "-c",
                    "import os; os.write(1,b'x'*131072)"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, close_fds=True,
                    start_new_session=True)

            with mock.patch("aegis360.sparse_story_raw_probe_transport.subprocess.Popen",
                    side_effect=launch_large_output):
                capture = _run_raw_probe(context)
            self.assertFalse(capture.completed)
            self.assertEqual(len(capture.stdout), 65_537)


if __name__ == "__main__": unittest.main()
