"""Retained claim invokes each closed coordinator fixture mode by exact row."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_probe_denials import _open_retained_probed_batch
from aegis360.sparse_story_raw_probe_transport import _verify_native_launch_event
from aegis360.sparse_story_synthetic_plan import _freeze_private_synthetic_case_manifest
from tests import test_sparse_story_raw_probe_transport as host_tests
from tests import test_sparse_story_synthetic_plan as plan_tests


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class CoordinatorClaimModeHostTests(unittest.TestCase):
    def test_each_coordinator_mode_binds_its_own_native_launch(self):
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20,
            stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
        rows = {row["case_id"]: row for row in manifest["cases"]}
        for case_id in ("replacement_race", "single_invocation",
                        "receipt_rebuild"):
            with self.subTest(case_id=case_id), host_tests.RawProbeTransportHostTests.context(
                    self, own_batch_scratch=True, coordinated=True) as inputs:
                session = _open_retained_probed_batch(**inputs)
                try:
                    claim = session.claim_once()
                    capture = claim._run_coordinator_fixture_case_once(
                        case_id, rows[case_id])
                    self.assertTrue(capture.completed, capture.reason)
                    self.assertIs(capture, session._invocation_capture)
                    self.assertIs(_verify_native_launch_event(capture,
                        candidate=session._candidate,
                        suffix=("--aegis-synthetic-case", case_id, "--")),
                        capture.launch_event)
                    self.assertEqual(claim._launch_ledger.count, 1)
                    with mock.patch(
                            "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                            ) as second, self.assertRaises(ValueError):
                        claim._run_coordinator_fixture_case_once(
                            case_id, rows[case_id])
                    second.assert_not_called()
                finally:
                    session.close()


if __name__ == "__main__":
    unittest.main()
