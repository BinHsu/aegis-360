"""Real Seatbelt integration of the ordered private synthetic case dispatcher."""

import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_coordinator_mutation import (  # noqa: E402
    _OwnedSelectedBundleMutation, _TOKEN,
)
from aegis360.sparse_story_private_complete_cases import (  # noqa: E402
    _observe_private_complete_synthetic_cases_once,
    _revalidate_private_complete_synthetic_observations,
)
from aegis360.sparse_story_private_byte_repeat import (  # noqa: E402
    _observe_private_native_byte_repeat,
)
from aegis360.sparse_story_private_case_result import (  # noqa: E402
    _rebuild_private_synthetic_case_result,
    _revalidate_private_synthetic_case_result,
)
from aegis360.sparse_story_private_packet_schedule import (  # noqa: E402
    _PrivateSyntheticPacketSchedule,
)
from aegis360.sparse_story_private_scheduled_receipt import (  # noqa: E402
    _build_private_scheduled_run_receipt,
)
from aegis360.sparse_story_private_scheduled_publication import (  # noqa: E402
    _publish_private_scheduled_packet_once,
)
from aegis360.sparse_story_private_gate_evidence import (  # noqa: E402
    _bind_private_synthetic_gate_evidence,
    _finalize_private_synthetic_gate_once,
)
from aegis360.sparse_story_private_run_publication import _OwnedPrivateRunRoot  # noqa: E402
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch  # noqa: E402
from aegis360.sparse_story_runner_contract import CASE_SPECS  # noqa: E402
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_adapter_schedule,
)
from tests import test_sparse_story_raw_probe_transport as host_tests  # noqa: E402
from tests import test_sparse_story_synthetic_plan as plan_tests  # noqa: E402

_COORDINATOR = {"bundle_mutation", "replacement_race",
    "single_invocation", "receipt_rebuild"}
_DYNAMIC = {"network_ipv4_denied", "network_ipv6_denied",
    "unix_socket_denied", "outside_write_denied"}


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class CompletePrivateCaseHostTests(unittest.TestCase):
    def test_all_thirty_seven_rows_rebuild_in_frozen_order(self):
        with ExitStack() as stack:
            fixed, prepared, denial_sources, coordinator = {}, {}, {}, {}
            live_by_facade = {}
            mutation_owner = None
            for case_id, _ in CASE_SPECS:
                inputs = stack.enter_context(host_tests.RawProbeTransportHostTests.context(
                    self, own_batch_scratch=True, coordinated=True,
                    expose_live=True))
                live_by_facade[id(inputs["candidate"]._facade)] = inputs.pop(
                    "_fixture_live")
                session = _open_retained_probed_batch(**inputs)
                stack.callback(session.close)
                claim = session.claim_once()
                if case_id in _COORDINATOR:
                    coordinator[case_id] = claim
                    if case_id == "bundle_mutation":
                        # Test-only owner over the already retained selected
                        # publication. Factory ownership has its own test.
                        root = session._candidate._proofs[0]._root
                        identity = os.lstat(root)
                        relative = next(relative for relative, *_ in
                            session._candidate._proofs[0]._leaves
                            if relative.endswith(".png"))
                        mutation_owner = _OwnedSelectedBundleMutation(_TOKEN,
                            root, (identity.st_dev, identity.st_ino), relative)
                elif case_id in _DYNAMIC:
                    prepared[case_id] = claim._prepare_fixed_synthetic_owned_case(
                        case_id)
                else:
                    fixed[case_id] = claim
                if case_id in {"neighbor_packet_read_denied",
                        "result_read_denied"}:
                    denial_sources[case_id] = inputs["denial_source"]

            planned = plan_tests.SyntheticCasePlanTests().stimuli()
            planned["bundle_mutation"] = {**planned["bundle_mutation"],
                "argv": (mutation_owner._relative,)}
            packet_id = json.loads(next(iter(fixed.values()))._session
                ._candidate._request_bytes)["packet_id"]
            parameters = dict(adapter_manifest_sha256="a" * 64,
                repeat_packet_id=packet_id, fixed_claims=fixed,
                prepared_owners=prepared, denial_sources=denial_sources,
                coordinator_stimuli={case_id: planned[case_id]
                    for case_id in _COORDINATOR})
            private_parent = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            replacement_owner = _OwnedPrivateRunRoot(private_parent)
            repeat_claims = []
            for _ in range(2):
                repeat_inputs = stack.enter_context(
                    host_tests.RawProbeTransportHostTests.context(
                        self, own_batch_scratch=True, coordinated=True,
                        expose_live=True))
                live_by_facade[id(repeat_inputs["candidate"]._facade)] = (
                    repeat_inputs.pop("_fixture_live"))
                repeat_session = _open_retained_probed_batch(**repeat_inputs)
                stack.callback(repeat_session.close)
                repeat_claims.append(repeat_session.claim_once())
            scheduled_inputs = stack.enter_context(
                host_tests.RawProbeTransportHostTests.context(
                    self, own_batch_scratch=True, coordinated=True,
                    expose_live=True))
            scheduled_live = scheduled_inputs.pop("_fixture_live")
            live_by_facade[id(scheduled_inputs["candidate"]._facade)] = (
                scheduled_live)
            scheduled_session = _open_retained_probed_batch(**scheduled_inputs)
            stack.callback(scheduled_session.close)
            scheduled_claim = scheduled_session.claim_once()
            parameters["adapter_manifest_sha256"] = (
                scheduled_live._adapter_binding._runtime.backend_identity()[2])
            def retained_live(facade):
                return live_by_facade[id(facade)]
            with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                    side_effect=retained_live), mock.patch(
                    "aegis360.sparse_story_receipt_inputs._require_live",
                    side_effect=retained_live), mock.patch(
                    "aegis360.sparse_story_private_gate_evidence._require_live",
                    side_effect=retained_live), mock.patch(
                    "aegis360.sparse_story_raw_probe_transport._TIMEOUT_NS",
                    5_000_000_000):
                _, manifest = _freeze_private_synthetic_adapter_schedule(
                    **parameters)
                observed = _observe_private_complete_synthetic_cases_once(
                    frozen_manifest=manifest, fixed_claims=fixed,
                    prepared_owners=prepared, denial_sources=denial_sources,
                    coordinator_stimuli=parameters["coordinator_stimuli"],
                    mutation_claim=coordinator["bundle_mutation"],
                    mutation_owner=mutation_owner,
                    replacement_claim=coordinator["replacement_race"],
                    replacement_owner=replacement_owner,
                    exact_claims={case_id: coordinator[case_id] for case_id in
                        ("single_invocation", "receipt_rebuild")})
                self.assertFalse(observed.authority)
                self.assertEqual(tuple(row.case_id for row in observed.rows),
                    tuple(case_id for case_id, _ in CASE_SPECS))
                self.assertEqual(tuple(row.ordinal for row in observed.rows),
                    tuple(range(1, 38)))
                self.assertEqual(tuple(row.observed_result for row in observed.rows),
                    tuple(expected for _, expected in CASE_SPECS))
                _revalidate_private_complete_synthetic_observations(
                    proof=observed, frozen_manifest=manifest,
                    prepared_owners=prepared)
                altered = replace(observed, rows=(
                    replace(observed.rows[0], ordinal=2), *observed.rows[1:]))
                with self.assertRaises(ValueError):
                    _revalidate_private_complete_synthetic_observations(
                        proof=altered, frozen_manifest=manifest,
                        prepared_owners=prepared)
                relabelled = replace(observed, rows=(
                    replace(observed.rows[0], case_id=observed.rows[1].case_id),
                    *observed.rows[1:]))
                with self.assertRaises(ValueError):
                    _revalidate_private_complete_synthetic_observations(
                        proof=relabelled, frozen_manifest=manifest,
                        prepared_owners=prepared)
                repeat = _observe_private_native_byte_repeat(
                    first_claim=repeat_claims[0], second_claim=repeat_claims[1],
                    frozen_row=manifest["cases"][2],
                    repeat_packet_id=packet_id)
                private_result = _rebuild_private_synthetic_case_result(
                    frozen_manifest=manifest, complete_proof=observed,
                    repeat_proof=repeat, prepared_owners=prepared)
                self.assertFalse(private_result.authority)
                self.assertIs(_revalidate_private_synthetic_case_result(
                    private_result), private_result)
                with self.assertRaisesRegex(ValueError, "bytes changed"):
                    _revalidate_private_synthetic_case_result(replace(
                        private_result, bytes=private_result.bytes + b" "))
                result_value = json.loads(private_result.bytes)
                self.assertEqual(len(result_value["cases"]), 37)
                self.assertTrue(all(row["passed"]
                    for row in result_value["cases"]))
                self.assertTrue(result_value["repeatability"]["equal"])
                scheduled = _PrivateSyntheticPacketSchedule(
                    scheduled_claim, manifest)
                self.assertEqual(scheduled.packet_id, packet_id)
                self.assertNotIn(id(scheduled_claim),
                    {id(row.proof.claim) for row in observed.rows}
                    | {id(claim) for claim in repeat_claims})
                scheduled_capture = scheduled_claim._run_private_scheduled_packet_once(
                    scheduled)
                self.assertTrue(scheduled_capture.completed)
                scheduled_receipt = _build_private_scheduled_run_receipt(
                    scheduled)
                scheduled_owner = _OwnedPrivateRunRoot(private_parent)
                scheduled_publication = _publish_private_scheduled_packet_once(
                    owner=scheduled_owner, receipt=scheduled_receipt)
                self.assertEqual(scheduled_publication.revalidate(), (
                    scheduled_publication.evidence_sha256,
                    scheduled_publication.receipt_sha256))
                gate = _bind_private_synthetic_gate_evidence(
                    case_result=private_result,
                    publication=scheduled_publication)
                self.assertFalse(gate.authority)
                self.assertIs(gate.revalidate(), gate)
                with self.assertRaises(ValueError):
                    replace(gate, case_result_sha256="0" * 64).revalidate()
                with self.assertRaises(ValueError):
                    replace(gate, packet_id="packet-" + "0" * 20).revalidate()
                with self.assertRaises(ValueError):
                    replace(gate, capability_receipt_sha256="0" * 64).revalidate()
                with self.assertRaises(ValueError):
                    _rebuild_private_synthetic_case_result(
                        frozen_manifest=manifest, complete_proof=observed,
                        repeat_proof=replace(repeat,
                            second_stdout_sha256="0" * 64),
                        prepared_owners=prepared)
                with self.assertRaises(ValueError):
                    _rebuild_private_synthetic_case_result(
                        frozen_manifest=manifest, complete_proof=observed,
                        repeat_proof=replace(repeat,
                            _first_claim=observed.rows[2].proof.claim),
                        prepared_owners=prepared)
                finalized = _finalize_private_synthetic_gate_once(gate)
                self.assertFalse(finalized.authority)
                self.assertEqual(len(finalized.input_hashes), 5)
                self.assertIs(finalized.revalidate(), finalized)
                with self.assertRaises(ValueError):
                    gate.revalidate()


if __name__ == "__main__":
    unittest.main()
