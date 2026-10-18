"""A published preflight bundle must rebuild before local media publication."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_stage_a_preflight_bundle import prepare_bundle  # noqa: E402
from run_stage_a_media_preflight import run, validate_output_placement  # noqa: E402
from tests.test_sparse_story_media_tree import image  # noqa: E402
from tests.test_stage_a_preflight_bundle import StageABundleTests  # noqa: E402


class StageAMediaPreflightTests(unittest.TestCase):
    def test_external_output_placement_rejects_documents_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory); data_root = base / "aegis-360-items"
            data_root.mkdir()
            validate_output_placement(data_root / "outputs" / "new", data_root)
            with self.assertRaisesRegex(ValueError, "under the external data root"):
                validate_output_placement(base / "Documents" / "aegis-360" / "outputs" / "new", data_root)
            (data_root / "escape").symlink_to(base)
            with self.assertRaisesRegex(ValueError, "under the external data root"):
                validate_output_placement(data_root / "escape" / "new", data_root)

    def fixture(self):
        fixture = StageABundleTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        files, _ = prepare_bundle(**fixture.inputs())
        preflight = fixture.root / "preflight"; preflight.mkdir()
        for name, data in files.items(): (preflight / name).write_bytes(data)
        inputs = fixture.inputs()
        arguments = dict(preflight_root=preflight, old_source=inputs["old_source"],
            old_grid=inputs["old_grid"], old_scenes=inputs["old_scenes"],
            old_timeline=inputs["old_timeline"], ski_source=inputs["ski_source"],
            ski_scene_events=inputs["ski_scene_events"], salt_file=inputs["salt_file"],
            output_root=fixture.root / "media",
            benchmark_manifest=inputs["benchmark_manifest"])
        return fixture, files, arguments

    def test_changed_published_member_rejects_before_render(self):
        fixture, files, arguments = self.fixture()
        preflight = arguments["preflight_root"]
        (preflight / "adapter-index.json").write_bytes(files["adapter-index.json"] + b" ")
        with mock.patch("run_stage_a_media_preflight.render_stage_a_payloads") as render:
            with self.assertRaisesRegex(ValueError, "differs from exact rebuild"):
                run(**arguments)
            render.assert_not_called()

    def test_changed_approved_output_rejects_before_publication(self):
        _, files, arguments = self.fixture()
        index = json.loads(files["adapter-index.json"])
        payloads = [(row["media_ref"], image()) for packet in index["packets"]
                    for row in packet["projection"]["rows"]]
        arguments.update(expected_tree_sha256="0" * 64,
                         expected_result_sha256="0" * 64)
        with mock.patch("run_stage_a_media_preflight.render_stage_a_payloads",
                        return_value=payloads):
            with self.assertRaisesRegex(ValueError, "approved prepublication hashes"):
                run(**arguments)
        self.assertFalse(arguments["output_root"].exists())


if __name__ == "__main__":
    unittest.main()
