"""One normal native packet call remains distinct from synthetic fixture cases."""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_packet_schedule import (  # noqa: E402
    _PrivateSyntheticPacketSchedule,
)
from aegis360.sparse_story_private_scheduled_receipt import (  # noqa: E402
    _build_private_scheduled_run_receipt,
    _rebuild_private_scheduled_run_receipt,
)
from aegis360.sparse_story_private_run_publication import (  # noqa: E402
    _OwnedPrivateRunRoot,
)
from aegis360.sparse_story_private_scheduled_publication import (  # noqa: E402
    _publish_private_scheduled_packet_once,
)
from aegis360.sparse_story_private_publication import PublicationIncomplete  # noqa: E402
from aegis360.sparse_story_probe_denials import _open_retained_probed_batch  # noqa: E402
from aegis360.sparse_story_raw_probe_transport import _run_native_process  # noqa: E402
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _freeze_private_synthetic_case_manifest,
)
from tests import test_sparse_story_raw_probe_transport as host_tests  # noqa: E402
from tests import test_sparse_story_synthetic_plan as plan_tests  # noqa: E402


@unittest.skipUnless(os.uname().sysname == "Darwin"
    and os.uname().machine == "arm64"
    and os.environ.get("AEGIS_RUN_HOST_SEATBELT_TESTS") == "1",
    "requires explicit Darwin host Seatbelt gate outside nested sandbox")
class ScheduledPacketHostTests(unittest.TestCase):
    def test_no_spawn_failure_consumes_claim_and_allows_owned_cleanup(self):
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as inputs:
            live = inputs.pop("_fixture_live")
            session = _open_retained_probed_batch(**inputs)
            claim = session.claim_once()
            packet_id = json.loads(session._candidate._request_bytes)["packet_id"]
            runtime_sha = live._adapter_binding._runtime.backend_identity()[2]
            _, manifest = _freeze_private_synthetic_case_manifest(
                adapter_manifest_sha256=runtime_sha,
                repeat_packet_id=packet_id,
                stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
            with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                    return_value=live), mock.patch(
                    "aegis360.sparse_story_receipt_inputs._require_live",
                    return_value=live):
                schedule = _PrivateSyntheticPacketSchedule(claim, manifest)
                with mock.patch(
                        "aegis360.sparse_story_raw_probe_transport._run_native_process",
                        side_effect=ValueError("pre-spawn fault")) as launch:
                    with self.assertRaisesRegex(ValueError, "pre-spawn fault"):
                        claim._run_private_scheduled_packet_once(schedule)
                launch.assert_called_once()
                self.assertEqual(claim._launch_ledger.count, 0)
                self.assertTrue(claim._invoked)
                self.assertFalse(session._invocation_started)
                session.close()
                self.assertTrue(session._batch_scratch.closed)

    def test_one_normal_packet_uses_exact_retained_request_and_one_launch(self):
        with host_tests.RawProbeTransportHostTests.context(self,
                own_batch_scratch=True, coordinated=True,
                expose_live=True) as inputs:
            live = inputs.pop("_fixture_live")
            session = _open_retained_probed_batch(**inputs)
            try:
                claim = session.claim_once()
                packet_id = json.loads(session._candidate._request_bytes)["packet_id"]
                runtime_sha = live._adapter_binding._runtime.backend_identity()[2]
                _, manifest = _freeze_private_synthetic_case_manifest(
                    adapter_manifest_sha256=runtime_sha,
                    repeat_packet_id=packet_id,
                    stimuli=plan_tests.SyntheticCasePlanTests().stimuli())
                with mock.patch("aegis360.sparse_story_batch_policy._require_live",
                        return_value=live), mock.patch(
                        "aegis360.sparse_story_receipt_inputs._require_live",
                        return_value=live):
                    manifest["synthetic_adapter_manifest_sha256"] = "a" * 64
                    with mock.patch(
                            "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                            ) as spawn, self.assertRaises(ValueError):
                        _PrivateSyntheticPacketSchedule(claim, manifest)
                    spawn.assert_not_called()
                    manifest["synthetic_adapter_manifest_sha256"] = runtime_sha
                    schedule = _PrivateSyntheticPacketSchedule(claim, manifest)
                    digest = schedule.schedule_sha256
                    schedule.schedule_sha256 = "0" * 64
                    with mock.patch(
                            "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                            ) as spawn, self.assertRaises(ValueError):
                        claim._run_private_scheduled_packet_once(schedule)
                    spawn.assert_not_called()
                    schedule.schedule_sha256 = digest
                    with mock.patch(
                            "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                            ) as spawn, self.assertRaises(ValueError):
                        _run_native_process(session._candidate, (),
                            postvalidate=lambda: None, request_bytes=b"wrong",
                            launch_ledger=claim._launch_ledger)
                    spawn.assert_not_called()
                    capture = claim._run_private_scheduled_packet_once(schedule)
                    self.assertTrue(capture.completed, capture.reason)
                    self.assertEqual(capture.launch_event.mode, "adapter")
                    self.assertEqual(claim._launch_ledger.count, 1)
                    self.assertEqual(capture.launch_event._suffix, ())
                    self.assertEqual(hashlib.sha256(
                        session._candidate._request_bytes).hexdigest(),
                        schedule.request_sha256)
                    self.assertEqual(json.loads(capture.stdout)["status"], "abstain")
                    schedule.revalidate(allow_invoked=True)
                    receipt = _build_private_scheduled_run_receipt(schedule)
                    self.assertEqual(_rebuild_private_scheduled_run_receipt(
                        receipt), receipt.bytes)
                    original = receipt.bytes
                    receipt.bytes += b" "
                    with self.assertRaises(ValueError):
                        _rebuild_private_scheduled_run_receipt(receipt)
                    receipt.bytes = original
                    with tempfile.TemporaryDirectory() as temporary:
                        owner = _OwnedPrivateRunRoot(Path(temporary))
                        receipt.bytes += b" "
                        with self.assertRaises(ValueError):
                            _publish_private_scheduled_packet_once(
                                owner=owner, receipt=receipt)
                        owner.revalidate_empty()
                        receipt.bytes = original
                        published = _publish_private_scheduled_packet_once(
                            owner=owner, receipt=receipt)
                        self.assertFalse(published.authority)
                        self.assertEqual(published.revalidate(), (
                            hashlib.sha256(capture.stdout).hexdigest(),
                            hashlib.sha256(receipt.bytes).hexdigest()))
                        self.assertEqual((owner.root / "evidence.json").read_bytes(),
                            capture.stdout)
                        self.assertEqual((owner.root / "receipt.json").read_bytes(),
                            receipt.bytes)
                        with tempfile.TemporaryDirectory(dir=temporary) as other:
                            other_root = Path(other)
                            (other_root / "evidence.json").write_bytes(b"other")
                            (other_root / "receipt.json").write_bytes(b"other")
                            original_root = owner.root
                            original_identity = owner._identity
                            info = os.lstat(other_root)
                            owner.root = other_root
                            owner._identity = (info.st_dev, info.st_ino)
                            try:
                                with self.assertRaises(ValueError):
                                    published.revalidate()
                            finally:
                                owner.root = original_root
                                owner._identity = original_identity
                        held = owner.root / "held-evidence.json"
                        os.rename(owner.root / "evidence.json", held)
                        replacement = owner.root / "evidence.json"
                        replacement.write_bytes(b"replacement")
                        replacement.chmod(0o444)
                        with self.assertRaises((ValueError, PublicationIncomplete)):
                            published.revalidate()
                        with self.assertRaises(PublicationIncomplete):
                            published.pair.cleanup()
                        self.assertEqual(replacement.read_bytes(), b"replacement")
                        self.assertEqual(held.read_bytes(), capture.stdout)
                    with mock.patch(
                            "aegis360.sparse_story_raw_probe_transport.subprocess.Popen"
                            ) as spawn, self.assertRaises(ValueError):
                        claim._run_private_scheduled_packet_once(schedule)
                    spawn.assert_not_called()
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
