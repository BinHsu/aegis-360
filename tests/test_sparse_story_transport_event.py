"""Native Popen event and one-shot ledger checks without policy authority."""

import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_raw_probe_transport import (  # noqa: E402
    _NativeLaunchLedger, _NativeLaunchSpec, _RawProbeCapture,
    _run_native_process, _verify_native_launch_event,
)


class _Candidate:
    def _binding_bytes(self):
        return b"unchanged private binding"


class _Proof:
    def manifest(self):
        return None


class NativeLaunchEventTests(unittest.TestCase):
    SUFFIX = ("--aegis-synthetic-case", "fd_hygiene", "--")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root_fd = os.open(self.directory.name, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, self.root_fd)
        self.candidate = _Candidate()
        self.ledger = _NativeLaunchLedger(self.candidate)
        self.proof = _Proof()

    def run_capture(self, *, ledger=None):
        # The child becomes its own group before writing. This exercises the
        # real Popen, pipe, group teardown and returned-capture path.
        code = ("import os,sys,time; os.setsid(); "
            "sys.stdout.write('ok'); sys.stdout.flush(); time.sleep(0.2)")
        spec = _NativeLaunchSpec((sys.executable, "-c", code),
            {"LANG": "C", "LC_ALL": "C", "TZ": "UTC", "NO_COLOR": "1"},
            b"policy", self.root_fd, self.proof, self.proof)
        with mock.patch("aegis360.sparse_story_raw_probe_transport"
                "._retained_launch_spec", return_value=spec):
            return _run_native_process(self.candidate,
                self.SUFFIX,
                postvalidate=lambda: None, request_bytes=b"",
                launch_ledger=ledger or self.ledger)

    def test_real_popen_event_binds_exact_capture_and_mode(self):
        capture = self.run_capture()
        self.assertTrue(capture.completed, capture.reason)
        self.assertEqual(self.ledger.count, 1)
        event = _verify_native_launch_event(capture,
            candidate=self.candidate, suffix=self.SUFFIX)
        self.assertIs(event, capture.launch_event)
        with self.assertRaises(ValueError):
            _verify_native_launch_event(capture,
                candidate=self.candidate,
                suffix=("--aegis-synthetic-case", "stdout_empty", "--"))
        with self.assertRaises(ValueError):
            _verify_native_launch_event(capture,
                candidate=_Candidate(), suffix=self.SUFFIX)

    def test_copied_or_fabricated_capture_has_no_launch_event_authority(self):
        capture = self.run_capture()
        with self.assertRaises(ValueError):
            _verify_native_launch_event(replace(capture, stdout=b"changed"),
                candidate=self.candidate, suffix=self.SUFFIX)
        fabricated = _RawProbeCapture(capture.stdout, capture.returncode,
            capture.group_gone, capture.completed, capture.postcheck_passed,
            capture.reason)
        with self.assertRaises(ValueError):
            _verify_native_launch_event(fabricated,
                candidate=self.candidate, suffix=self.SUFFIX)

    def test_second_launch_with_same_ledger_is_blocked_before_popen(self):
        capture = self.run_capture()
        self.assertTrue(capture.completed, capture.reason)
        with mock.patch("aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                ) as popen, self.assertRaisesRegex(ValueError, "unavailable"):
            self.run_capture()
        popen.assert_not_called()
        self.assertEqual(self.ledger.count, 1)

    def test_failed_popen_releases_reservation_without_fabricating_event(self):
        with mock.patch("aegis360.sparse_story_raw_probe_transport.subprocess.Popen",
                side_effect=OSError("controlled spawn failure")):
            with self.assertRaisesRegex(OSError, "controlled spawn failure"):
                self.run_capture()
        self.assertEqual(self.ledger.count, 0)
        self.assertIsNone(self.ledger._event)
        self.assertTrue(self.run_capture().completed)


if __name__ == "__main__":
    unittest.main()
