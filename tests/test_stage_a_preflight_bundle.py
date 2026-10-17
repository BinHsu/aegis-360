"""Synthetic Stage A builder controls; no real media or model invocation."""

from __future__ import annotations

import hashlib
import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from aegis360.context_views import build_context_view_grid  # noqa: E402
from aegis360.multi_signal_timeline import build_multi_signal_timeline  # noqa: E402
from aegis360.sparse_story_projection import PUBLIC_PRIVACY  # noqa: E402
from build_stage_a_preflight_bundle import (  # noqa: E402
    _exclusive_rename, main, prepare_bundle, publish_bundle)


def raw(value):
    return (json.dumps(value, allow_nan=False, sort_keys=True, indent=2) + "\n").encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


class StageABundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        old_media, ski_media = b"synthetic-old-ghost", b"synthetic-skiing"
        self.old_source = self.root / "old.webm"; self.old_source.write_bytes(old_media)
        self.ski_source = self.root / "ski.webm"; self.ski_source.write_bytes(ski_media)
        manifest = {"asset": [
            {"id": "old_ghost_road_360", "byte_size": len(old_media),
             "sha256": sha(old_media), "reported_duration_seconds": 225.453},
            {"id": "skiing_may_2019_360", "byte_size": len(ski_media),
             "sha256": sha(ski_media), "reported_duration_seconds": 616.392}]}
        self.manifest = self.root / "manifest.toml"
        self.manifest.write_text("\n".join(
            f'[[asset]]\nid = "{a["id"]}"\nbyte_size = {a["byte_size"]}\nsha256 = "{a["sha256"]}"\nreported_duration_seconds = {a["reported_duration_seconds"]}\n'
            for a in manifest["asset"]))
        tomllib.loads(self.manifest.read_text())
        old_grid = build_context_view_grid(source_id="old-ghost-synthetic",
            start_seconds=0, duration_seconds=225.453)
        self.old_grid = self.root / "old-grid.json"; self.old_grid.write_bytes(raw(old_grid))
        candidates = ([{"event_id": "event:scene-change:0000", "timestamp_seconds": 10.0,
                        "scene_score": 0.5},
                       {"event_id": "event:scene-change:0001", "timestamp_seconds": 10.5,
                        "scene_score": 0.5}] +
                      [{"event_id": f"event:scene-change:{i:04d}",
                        "timestamp_seconds": 205.6 if i == 24 else 15.0 + (i - 2) * 8,
                        "scene_score": 0.5} for i in range(2, 25)])
        old_scenes = {"schema_version": "aegis360.scene-change-candidates.v1",
                      "source_id": "old-ghost-synthetic", "candidates": candidates}
        self.old_scenes = self.root / "old-scenes.json"; self.old_scenes.write_bytes(raw(old_scenes))
        old_timeline = build_multi_signal_timeline(old_grid, old_scenes,
            grid_sha256=sha(self.old_grid.read_bytes()),
            scene_candidates_sha256=sha(self.old_scenes.read_bytes()))
        self.assertEqual(old_timeline["events"][-1]["event_id"], "event:multi:0023")
        self.old_timeline = self.root / "old-timeline.json"
        self.old_timeline.write_bytes(raw(old_timeline))
        ski_events = {"schema_version": "aegis360.ffmpeg-scene-events.v1",
                      "source_id": "skiing-synthetic", "source_sha256": sha(ski_media),
                      "config": {"sample_fps": 10.0}, "events": [],
                      "privacy": {"contains_source_path": False}}
        self.ski_scene_events = self.root / "ski-events.json"
        self.ski_scene_events.write_bytes(raw(ski_events))
        self.salt_file = self.root / "salt"
        self.salt_file.write_text("a" * 64 + "\n")
        self.salt_file.chmod(0o600)

    def inputs(self):
        return {"old_source": self.old_source, "old_grid": self.old_grid,
                "old_scenes": self.old_scenes, "old_timeline": self.old_timeline,
                "ski_source": self.ski_source,
                "ski_scene_events": self.ski_scene_events,
                "salt_file": self.salt_file,
                "benchmark_manifest": self.manifest}

    def test_deterministic_six_packets_and_closed_projection(self):
        first_files, first = prepare_bundle(**self.inputs())
        second_files, second = prepare_bundle(**self.inputs())
        self.assertEqual(first_files, second_files)
        self.assertEqual(first, second)
        self.assertEqual((first["packet_count"], first["proposal_count"],
                          first["control_count"]), (6, 1, 5))
        self.assertEqual(len([name for name in first_files if name.startswith("private-packet-")]), 6)
        index = json.loads(first_files["adapter-index.json"])
        self.assertEqual(index["packet_count"], 6)
        self.assertEqual(index["packets"][0]["projection"]["privacy"], PUBLIC_PRIVACY)
        for row in index["packets"]:
            self.assertEqual(set(row["projection"]),
                             {"schema_version", "packet_id", "rows", "privacy", "authority"})
        self.assertNotIn(b"old-ghost-synthetic", first_files["adapter-index.json"])
        self.assertNotIn(b'"role":"proposal"', first_files["adapter-index.json"])
        self.assertNotIn(b"synthetic-old-ghost", b"".join(first_files.values()))
        self.assertNotIn(b"a" * 64, b"".join(first_files.values()))
        output = self.root / "bundle"
        self.assertFalse(output.exists())
        publish_bundle(output, first_files)
        self.assertEqual({p.name for p in output.iterdir()}, set(first_files))
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, first_files)
        with self.assertRaises(FileExistsError):
            publish_bundle(output, first_files)
        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, first_files)

    def test_changed_source_and_self_consistent_timeline_rejected(self):
        self.old_source.write_bytes(b"synthetic-old-gh0st")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            prepare_bundle(**self.inputs())
        self.old_source.write_bytes(b"synthetic-old-ghost")
        timeline = json.loads(self.old_timeline.read_bytes())
        timeline["events"][-1]["event_id"] = "event:multi:forged"
        self.old_timeline.write_bytes(raw(timeline))
        with self.assertRaisesRegex(ValueError, "exactly rebuild"):
            prepare_bundle(**self.inputs())

    def test_reject_nonzero_ski_candidate_and_weak_salt(self):
        events = json.loads(self.ski_scene_events.read_bytes())
        events["events"] = [{"timestamp_seconds": 200.0, "scene_score": 0.7}]
        self.ski_scene_events.write_bytes(raw(events))
        with self.assertRaisesRegex(ValueError, "nonzero selected candidates"):
            prepare_bundle(**self.inputs())
        events["events"] = []
        self.ski_scene_events.write_bytes(raw(events))
        self.salt_file.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "owner-owned"):
            prepare_bundle(**self.inputs())

    def test_existing_destination_is_not_changed(self):
        files, _ = prepare_bundle(**self.inputs())
        output = self.root / "bundle"
        output.mkdir()
        sentinel = output / "keep"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            publish_bundle(output, files)
        self.assertEqual(sentinel.read_bytes(), b"keep")
        self.assertEqual(list(output.iterdir()), [sentinel])

    def test_atomic_rename_refuses_racing_existing_destination(self):
        staged, output = self.root / "staged", self.root / "bundle"
        staged.mkdir(); output.mkdir()
        (staged / "new").write_bytes(b"new")
        (output / "keep").write_bytes(b"keep")
        with self.assertRaises(OSError):
            _exclusive_rename(staged, output)
        self.assertEqual((output / "keep").read_bytes(), b"keep")
        self.assertEqual((staged / "new").read_bytes(), b"new")

    def test_cli_dry_run_writes_nothing_and_reports_only_counts_hashes(self):
        output = self.root / "new-bundle"
        arguments = []
        for name, path in (("old-source", self.old_source),
                           ("old-grid", self.old_grid),
                           ("old-scenes", self.old_scenes),
                           ("old-timeline", self.old_timeline),
                           ("ski-source", self.ski_source),
                           ("ski-scene-events", self.ski_scene_events),
                           ("salt-file", self.salt_file),
                           ("output-root", output)):
            arguments.extend(("--" + name, str(path)))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(arguments + ["--dry-run"],
                                  benchmark_manifest=self.manifest), 0)
        self.assertFalse(output.exists())
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["packet_count"], 6)
        self.assertEqual(set(report), {"source_count", "packet_count", "proposal_count",
            "control_count", "source_sha256s", "ski_scene_events_sha256",
            "execution_manifest_sha256", "adapter_index_sha256", "file_sha256s"})
        self.assertNotIn(str(self.root), stdout.getvalue())
        self.assertNotIn("a" * 64, stdout.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments, benchmark_manifest=self.manifest), 0)
        self.assertTrue(output.is_dir())


if __name__ == "__main__":
    unittest.main()
