"""Discriminating checks for the private, non-authoritative cardinality audit."""

import hashlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_coordinator_cardinality import (  # noqa: E402
    _audit_private_synthetic_cardinality,
)
from aegis360.sparse_story_probe_denials import _ClaimedProbedBatch  # noqa: E402
from aegis360.sparse_story_raw_probe_transport import _RawProbeCapture  # noqa: E402
from aegis360.sparse_story_runner_contract import AuthorityUnavailable  # noqa: E402
from aegis360.sparse_story_runner_contract import canonical_run_receipt_bytes  # noqa: E402


class CardinalityAuditTests(unittest.TestCase):
    def setUp(self):
        self.row = {"case_id": "fd_hygiene", "expected_result": "success",
            "stimulus": {"argv": [], "stdin_sha256": "0" * 64,
                "support_manifest_sha256": "1" * 64}}
        self.capture = _RawProbeCapture(b'raw stdout', 0, True, True, True, "ok")
        self.session = SimpleNamespace(_invocation_started=True,
            _invocation_capture=self.capture)
        self.claim = object.__new__(_ClaimedProbedBatch)
        self.claim._session = self.session
        self.claim._invoked = True
        self.claim._last_stimulus = (self.row["case_id"], self.row["stimulus"])
        self.live = mock.patch.object(_ClaimedProbedBatch, "revalidate")
        self.live.start()
        self.addCleanup(self.live.stop)

    def test_completed_capture_is_bound_to_exact_frozen_row_without_result_enum(self):
        evidence = _audit_private_synthetic_cardinality(
            claim=self.claim, frozen_row=self.row)
        self.assertEqual(evidence.case_id, "fd_hygiene")
        self.assertTrue(evidence.claim_consumed)
        self.assertFalse(hasattr(evidence, "invocation_count"))
        self.assertEqual(evidence.stdout_sha256,
            hashlib.sha256(self.capture.stdout).hexdigest())
        self.assertIs(evidence.capture, self.capture)
        self.assertFalse(hasattr(evidence, "observed_result"))

    def test_missing_or_duplicate_invocation_state_cannot_pass(self):
        for field, value in (("_invoked", False),
                ("_invocation_started", False),
                ("_invocation_capture", None)):
            with self.subTest(field=field):
                target = self.claim if field == "_invoked" else self.session
                old = getattr(target, field)
                setattr(target, field, value)
                try:
                    with self.assertRaisesRegex(ValueError, "unproven"):
                        _audit_private_synthetic_cardinality(
                            claim=self.claim, frozen_row=self.row)
                finally:
                    setattr(target, field, old)

    def test_changed_row_or_incomplete_capture_is_rejected(self):
        changed = {**self.row, "stimulus": {**self.row["stimulus"],
            "stdin_sha256": "f" * 64}}
        with self.assertRaisesRegex(ValueError, "frozen stimulus"):
            _audit_private_synthetic_cardinality(
                claim=self.claim, frozen_row=changed)
        self.session._invocation_capture = _RawProbeCapture(
            self.capture.stdout, 0, False, True, True, "group_present")
        with self.assertRaisesRegex(ValueError, "unproven"):
            _audit_private_synthetic_cardinality(
                claim=self.claim, frozen_row=self.row)

    def test_probe_receipt_cannot_be_relabelled_as_adapter_run_receipt(self):
        with self.assertRaises(AuthorityUnavailable):
            canonical_run_receipt_bytes(b'{"probe":"receipt"}')


if __name__ == "__main__":
    unittest.main()
