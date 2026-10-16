"""One-row private adapter dispatch preserves the frozen stimulus boundary."""

import copy
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_probe_denials import _open_retained_probed_batch  # noqa: E402
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_case_manifest,
    _observe_private_synthetic_adapter_row_once,
)
from tests import test_sparse_story_raw_probe_transport as host_tests  # noqa: E402
from tests import test_sparse_story_synthetic_plan as plan_tests  # noqa: E402


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class PrivateAdapterRowHostTests(unittest.TestCase):
    def test_one_row_wrong_stimulus_and_duplicate(self):
        _, manifest = _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20,
            stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
        row = next(item for item in manifest["cases"]
            if item["case_id"] == "fd_hygiene")
        with host_tests.RawProbeTransportHostTests.context(
                self, own_batch_scratch=True, coordinated=True) as inputs:
            session = _open_retained_probed_batch(**inputs)
            try:
                claim = session.claim_once()
                wrong = copy.deepcopy(row)
                wrong["stimulus"]["stdin_sha256"] = "0" * 64
                with mock.patch(
                        "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                        ) as spawn, self.assertRaisesRegex(ValueError,
                            "retained stimulus"):
                    _observe_private_synthetic_adapter_row_once(
                        row=wrong, claim=claim)
                spawn.assert_not_called()
                self.assertEqual(claim._launch_ledger.count, 0)

                self.assertEqual(_observe_private_synthetic_adapter_row_once(
                    row=row, claim=claim), "success")
                self.assertEqual(claim._launch_ledger.count, 1)
                with mock.patch(
                        "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                        ) as spawn, self.assertRaisesRegex(ValueError,
                            "retained claim"):
                    _observe_private_synthetic_adapter_row_once(
                        row=row, claim=claim)
                spawn.assert_not_called()
                self.assertEqual(claim._launch_ledger.count, 1)
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
