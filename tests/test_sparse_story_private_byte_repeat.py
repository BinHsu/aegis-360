"""Two real retained native launches must bind one frozen repeat row."""

import hashlib
import json
import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_byte_repeat import (  # noqa: E402
    _observe_private_native_byte_repeat,
    _revalidate_private_native_byte_repeat,
)
from aegis360.sparse_story_probe_denials import (  # noqa: E402
    _ClaimedProbedBatch, _open_retained_probed_batch,
)
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_case_manifest,
)
from tests import test_sparse_story_raw_probe_transport as host_tests  # noqa: E402
from tests import test_sparse_story_synthetic_plan as plan_tests  # noqa: E402

PACKET_ID = "packet-" + "b" * 20


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class NativeByteRepeatHostTests(unittest.TestCase):
    def row(self):
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id=PACKET_ID,
            stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
        return next(row for row in manifest["cases"]
            if row["case_id"] == "fd_hygiene")

    def test_two_fresh_native_claims_produce_equal_byte_hashes(self):
        row = self.row()
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as first_inputs:
            first_live = first_inputs.pop("_fixture_live")
            first = _open_retained_probed_batch(**first_inputs)
            with host_tests.RawProbeTransportHostTests.context(self,
                    own_batch_scratch=True, coordinated=True,
                    expose_live=True) as second_inputs:
                second_live = second_inputs.pop("_fixture_live")
                second = _open_retained_probed_batch(**second_inputs)
                try:
                    packet_id = json.loads(first._candidate._request_bytes)["packet_id"]
                    self.assertEqual(packet_id,
                        json.loads(second._candidate._request_bytes)["packet_id"])
                    def retained_live(facade):
                        if facade is first._candidate._facade: return first_live
                        if facade is second._candidate._facade: return second_live
                        raise ValueError("unexpected facade")
                    with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                            side_effect=retained_live):
                        first_claim, second_claim = first.claim_once(), second.claim_once()
                        observed = _observe_private_native_byte_repeat(
                            first_claim=first_claim, second_claim=second_claim,
                            frozen_row=row, repeat_packet_id=packet_id)
                        self.assertIs(
                            _revalidate_private_native_byte_repeat(observed), observed)
                        with self.assertRaisesRegex(ValueError, "hashes differ"):
                            _revalidate_private_native_byte_repeat(replace(
                                observed, second_stdout_sha256="0" * 64))
                        second_claim._launch_ledger.count = 2
                        with self.assertRaises(ValueError):
                            _revalidate_private_native_byte_repeat(observed)
                        second_claim._launch_ledger.count = 1
                    self.assertEqual(observed.packet_id, packet_id)
                    self.assertEqual(observed.case_id, "fd_hygiene")
                    self.assertTrue(observed.equal)
                    self.assertEqual(observed.first_stdout_sha256,
                        hashlib.sha256(first._invocation_capture.stdout).hexdigest())
                    self.assertEqual(observed.second_stdout_sha256,
                        hashlib.sha256(second._invocation_capture.stdout).hexdigest())
                    self.assertEqual(first_claim._launch_ledger.count, 1)
                    self.assertEqual(second_claim._launch_ledger.count, 1)
                finally:
                    first.close()
                    second.close()

    def test_wrong_packet_and_row_reject_before_native_spawn(self):
        row = self.row()
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as first_inputs:
            first_live = first_inputs.pop("_fixture_live")
            first = _open_retained_probed_batch(**first_inputs)
            with host_tests.RawProbeTransportHostTests.context(self,
                    own_batch_scratch=True, coordinated=True,
                    expose_live=True) as second_inputs:
                second_live = second_inputs.pop("_fixture_live")
                second = _open_retained_probed_batch(**second_inputs)
                try:
                    packet_id = json.loads(first._candidate._request_bytes)["packet_id"]
                    def retained_live(facade):
                        if facade is first._candidate._facade: return first_live
                        if facade is second._candidate._facade: return second_live
                        raise ValueError("unexpected facade")
                    with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                            side_effect=retained_live), mock.patch(
                            "aegis360.sparse_story_raw_probe_transport.subprocess.Popen") as spawn:
                        first_claim, second_claim = first.claim_once(), second.claim_once()
                        with self.assertRaises(ValueError):
                            _observe_private_native_byte_repeat(
                                first_claim=first_claim, second_claim=second_claim,
                                frozen_row=row, repeat_packet_id="packet-" + "c" * 20)
                        changed = {**row, "stimulus": {**row["stimulus"],
                            "stdin_sha256": "0" * 64}}
                        with self.assertRaises(ValueError):
                            _observe_private_native_byte_repeat(
                                first_claim=first_claim, second_claim=second_claim,
                                frozen_row=changed, repeat_packet_id=packet_id)
                        spawn.assert_not_called()
                    with self.assertRaises(TypeError):
                        _observe_private_native_byte_repeat(
                            first_claim=first_claim, second_claim=first_claim,
                            frozen_row=row, repeat_packet_id=PACKET_ID)
                finally:
                    first.close()
                    second.close()

    def test_changed_second_capture_is_rejected_by_native_event_binding(self):
        row = self.row()
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as first_inputs:
            first_live = first_inputs.pop("_fixture_live")
            first = _open_retained_probed_batch(**first_inputs)
            with host_tests.RawProbeTransportHostTests.context(self,
                    own_batch_scratch=True, coordinated=True,
                    expose_live=True) as second_inputs:
                second_live = second_inputs.pop("_fixture_live")
                second = _open_retained_probed_batch(**second_inputs)
                try:
                    packet_id = json.loads(first._candidate._request_bytes)["packet_id"]
                    def retained_live(facade):
                        if facade is first._candidate._facade: return first_live
                        if facade is second._candidate._facade: return second_live
                        raise ValueError("unexpected facade")
                    with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                            side_effect=retained_live):
                        first_claim, second_claim = first.claim_once(), second.claim_once()
                        native = _ClaimedProbedBatch._run_fixed_synthetic_fd_case_once
                        def changed_second(claim, frozen_row=None):
                            capture = native(claim, frozen_row)
                            if claim is second_claim:
                                capture = replace(capture, stdout=capture.stdout + b" ")
                                claim._session._invocation_capture = capture
                            return capture
                        with mock.patch.object(_ClaimedProbedBatch,
                                "_run_fixed_synthetic_fd_case_once",
                                changed_second):
                            with self.assertRaisesRegex(ValueError,
                                    "native launch event does not bind this capture"):
                                _observe_private_native_byte_repeat(
                                    first_claim=first_claim, second_claim=second_claim,
                                    frozen_row=row, repeat_packet_id=packet_id)
                finally:
                    first.close()
                    second.close()


if __name__ == "__main__":
    unittest.main()
