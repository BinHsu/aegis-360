"""Private one-packet shape checks; no native launch or public authority."""

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_private_packet_schedule import (  # noqa: E402
    _PrivateSyntheticPacketSchedule,
)
from aegis360.sparse_story_runner_contract import (  # noqa: E402
    CASE_SPECS, build_adapter_request_shape, build_asset_manifest_shape,
    build_case_manifest, canonical_bytes, sha256,
)
from tests.test_sparse_story_projection import SparseStoryProjectionTests  # noqa: E402


class _Candidate:
    def __init__(self, request):
        self._request_bytes = canonical_bytes(request)
        self.binding = "b" * 64

    def invocation_binding_sha256(self):
        return self.binding


class _Claim:
    def __init__(self, candidate):
        self._session = SimpleNamespace(_candidate=candidate,
            _invocation_started=False, _invocation_capture=None)
        self._invoked = False
        self._launch_ledger = SimpleNamespace(count=0, _event=None)

    def revalidate(self):
        return None


class PrivatePacketScheduleTests(unittest.TestCase):
    def setUp(self):
        _, _, index = SparseStoryProjectionTests().build(1)
        projection = index["packets"][0]["projection"]
        self.packet_id = projection["packet_id"]
        entry = lambda path, digest: {"relative_path": path, "mode": 0o444,
            "size": 1, "sha256": digest * 64}
        prompt = build_asset_manifest_shape(asset_kind="prompt_schema", entries=[
            entry("prompt.txt", "1"), entry("raw-observation-schema.json", "2")])
        model = build_asset_manifest_shape(asset_kind="model", entries=[
            entry("weights.bin", "3")])
        request = build_adapter_request_shape(packet_id=self.packet_id,
            projection=projection, prompt_schema_manifest=prompt,
            prompt_schema_root_path="/private/tmp/prompt",
            model_manifest=model, model_root_path="/private/tmp/model")
        self.claim = _Claim(_Candidate(request))
        support = build_asset_manifest_shape(asset_kind="synthetic_support",
            entries=[])
        rows = [{"case_id": case_id, "expected_result": expected,
            "stimulus": {"argv": [], "stdin_sha256": hashlib.sha256(b"").hexdigest(),
                "support_manifest_sha256": sha256(support)}}
            for case_id, expected in CASE_SPECS]
        self.manifest = build_case_manifest(
            synthetic_adapter_manifest_sha256="a" * 64,
            cases=rows, repeat_packet_id=self.packet_id)
        self.patch = patch("aegis360.sparse_story_probe_denials._ClaimedProbedBatch", _Claim)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.runtime_patch = patch(
            "aegis360.sparse_story_private_packet_schedule._derive_private_receipt_inputs",
            return_value=SimpleNamespace(runtime_manifest_sha256="a" * 64))
        self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)

    def schedule(self):
        return _PrivateSyntheticPacketSchedule(self.claim, self.manifest)

    def test_exact_private_one_packet_hash_rebuilds(self):
        schedule = self.schedule()
        self.assertEqual(schedule.revalidate(), schedule.schedule_bytes)
        self.assertEqual(hashlib.sha256(schedule.schedule_bytes).hexdigest(),
            schedule.schedule_sha256)
        shape = json.loads(schedule.schedule_bytes)
        self.assertEqual(shape["packets"][0]["packet_id"], self.packet_id)
        self.assertEqual(shape["packets"][0]["adapter_request_sha256"],
            hashlib.sha256(self.claim._session._candidate._request_bytes).hexdigest())
        self.assertEqual(shape["packets"][0]["adapter_projection_sha256"],
            sha256(json.loads(self.claim._session._candidate._request_bytes)["projection"]))
        self.assertNotIn("root_path", schedule.schedule_bytes.decode())

    def test_wrong_repeat_id_or_mutated_manifest_rejects(self):
        wrong = copy.deepcopy(self.manifest)
        wrong["repeat_packet_id"] = "packet-" + "0" * 20
        with self.assertRaises(ValueError):
            _PrivateSyntheticPacketSchedule(self.claim, wrong)
        schedule = self.schedule()
        self.manifest["cases"][0]["stimulus"]["argv"].append("changed")
        with self.assertRaises(ValueError): schedule.revalidate()

    def test_wrong_runtime_manifest_rejects_before_schedule_freeze(self):
        self.manifest["synthetic_adapter_manifest_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "differs from runtime"):
            self.schedule()

    def test_changed_request_binding_and_claim_reject(self):
        schedule = self.schedule()
        self.claim._session._candidate.binding = "c" * 64
        with self.assertRaises(ValueError): schedule.revalidate()
        self.claim._session._candidate.binding = "b" * 64
        request = json.loads(self.claim._session._candidate._request_bytes)
        request["model"]["root_path"] = "/private/tmp/replaced"
        self.claim._session._candidate._request_bytes = canonical_bytes(request)
        with self.assertRaises(ValueError): schedule.revalidate()

    def test_self_consistent_relabelled_schedule_hash_rejects(self):
        schedule = self.schedule()
        schedule.request_sha256 = "0" * 64
        shape = json.loads(schedule.schedule_bytes)
        shape["packets"][0]["adapter_request_sha256"] = schedule.request_sha256
        schedule.schedule_bytes = canonical_bytes(shape)
        schedule.schedule_sha256 = hashlib.sha256(schedule.schedule_bytes).hexdigest()
        with self.assertRaises(ValueError): schedule.revalidate()

    def test_only_one_normal_launch_can_postvalidate(self):
        schedule = self.schedule()
        self.claim._invoked = True
        self.claim._session._invocation_started = True
        self.claim._launch_ledger.count = 1
        self.claim._launch_ledger._event = SimpleNamespace(mode="adapter")
        with self.assertRaises(ValueError): schedule.revalidate()
        self.assertEqual(schedule.revalidate(allow_invoked=True), schedule.schedule_bytes)
        self.claim._launch_ledger._event.mode = "synthetic_case"
        with self.assertRaises(ValueError): schedule.revalidate(allow_invoked=True)
        self.claim._launch_ledger._event.mode = "adapter"
        self.claim._launch_ledger.count = 2
        with self.assertRaises(ValueError): schedule.revalidate(allow_invoked=True)


if __name__ == "__main__":
    unittest.main()
