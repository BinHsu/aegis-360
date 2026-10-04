import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_runner_contract import (  # noqa: E402
    CASE_SPECS, build_asset_manifest_shape, canonical_bytes,
)
from aegis360.sparse_story_synthetic_plan import (  # noqa: E402
    _ONE_ARG, _TWO_ARGS, _freeze_private_synthetic_case_manifest,
)


class SyntheticCasePlanTests(unittest.TestCase):
    def stimuli(self):
        empty = build_asset_manifest_shape(asset_kind="synthetic_support",
            entries=[])
        result = {}
        for case_id, _ in CASE_SPECS:
            argv = ("/private/tmp/target", "hex:89") if case_id in _TWO_ARGS else (
                ("/private/tmp/target",) if case_id in _ONE_ARG else ())
            if case_id == "argv_literal":
                argv = (";$(touch should-not-run)", "* ' \" \\")
            result[case_id] = {"argv": argv,
                "stdin": b"x" * 60_000 if case_id == "concurrent_pipe_pressure"
                    else b"", "support_manifest": empty}
        return result

    def freeze(self, stimuli):
        return _freeze_private_synthetic_case_manifest(
            adapter_manifest_sha256="a" * 64,
            repeat_packet_id="packet-" + "b" * 20, stimuli=stimuli)

    def test_freezes_exact_order_and_actual_stdin_support_hashes(self):
        encoded, manifest = self.freeze(self.stimuli())
        self.assertEqual(encoded, canonical_bytes(manifest))
        self.assertEqual([row["case_id"] for row in manifest["cases"]],
            [case_id for case_id, _ in CASE_SPECS])
        for row in manifest["cases"]:
            source = self.stimuli()[row["case_id"]]
            self.assertEqual(row["stimulus"]["stdin_sha256"],
                hashlib.sha256(source["stdin"]).hexdigest())
            self.assertEqual(row["stimulus"]["support_manifest_sha256"],
                hashlib.sha256(canonical_bytes(source["support_manifest"])).hexdigest())

    def test_missing_case_wrong_argv_or_stdin_fails_before_freeze(self):
        missing = self.stimuli(); missing.pop("receipt_rebuild")
        with self.assertRaises(ValueError): self.freeze(missing)
        wrong_argv = self.stimuli(); wrong_argv["cwd_identity"] = {
            **wrong_argv["cwd_identity"], "argv": ()}
        with self.assertRaises(ValueError): self.freeze(wrong_argv)
        wrong_stdin = self.stimuli(); wrong_stdin["concurrent_pipe_pressure"] = {
            **wrong_stdin["concurrent_pipe_pressure"], "stdin": b"x" * 59_999}
        with self.assertRaises(ValueError): self.freeze(wrong_stdin)
        unexpected = self.stimuli(); unexpected["stdout_empty"] = {
            **unexpected["stdout_empty"], "stdin": b"secret"}
        with self.assertRaises(ValueError): self.freeze(unexpected)

    def test_manifest_rejects_wrong_support_kind_and_unexpected_file(self):
        wrong_kind = self.stimuli()
        wrong_kind["stdout_empty"] = {**wrong_kind["stdout_empty"],
            "support_manifest": build_asset_manifest_shape(asset_kind="model",
                entries=[{"relative_path": "weights.bin", "mode": 0o444,
                    "size": 1, "sha256": "0" * 64}])}
        with self.assertRaises(ValueError): self.freeze(wrong_kind)
        extra = self.stimuli()
        extra["stdout_empty"] = {**extra["stdout_empty"],
            "support_manifest": build_asset_manifest_shape(
                asset_kind="synthetic_support", entries=[{
                    "relative_path": "unexpected", "mode": 0o444,
                    "size": 1, "sha256": "0" * 64}])}
        with self.assertRaises(ValueError): self.freeze(extra)

    def test_coordinator_stimulus_is_hashed_without_inventing_fixed_argv(self):
        stimuli = self.stimuli()
        stimuli["replacement_race"] = {**stimuli["replacement_race"],
            "argv": ("/private/tmp/owned-target",), "stdin": b"race-input"}
        _, manifest = self.freeze(stimuli)
        row = next(row for row in manifest["cases"]
            if row["case_id"] == "replacement_race")
        self.assertEqual(row["stimulus"]["argv"], ["/private/tmp/owned-target"])
        self.assertEqual(row["stimulus"]["stdin_sha256"],
            hashlib.sha256(b"race-input").hexdigest())


if __name__ == "__main__":
    unittest.main()
