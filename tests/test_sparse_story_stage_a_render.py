"""Stage A renderer binds source bytes, private geometry, and public refs."""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_stage_a_render import render_stage_a_payloads  # noqa: E402
from tests.test_sparse_story_media_tree import image  # noqa: E402
from tests.test_sparse_story_projection import SparseStoryProjectionTests  # noqa: E402


class StageARenderTests(unittest.TestCase):
    def test_render_uses_exact_private_rows_and_public_refs(self):
        packets, hashes, index = SparseStoryProjectionTests().build(1)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.webm"
            source.write_bytes(b"synthetic-source")
            expected = packets[0]["inputs"]["source_sha256"]
            with mock.patch("aegis360.sparse_story_stage_a_render._hash_file", return_value=expected), \
                    mock.patch("aegis360.sparse_story_stage_a_render._capture_png", return_value=image()) as capture:
                payloads = render_stage_a_payloads(index=index, private_packets=packets,
                    ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                    source_by_id={packets[0]["source_id"]: source})
            self.assertEqual(len(payloads), 6)
            self.assertEqual({ref for ref, _ in payloads},
                {row["media_ref"] for row in index["packets"][0]["projection"]["rows"]})
            self.assertEqual(capture.call_count, 6)
            command = capture.call_args_list[0].args[0]
            self.assertIn("v360=input=equirect:output=flat:w=480:h=270", command[command.index("-filter_complex") + 1])

    def test_source_hash_mismatch_stops_before_render(self):
        packets, hashes, index = SparseStoryProjectionTests().build(1)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.webm"
            source.write_bytes(b"wrong-source")
            with mock.patch("aegis360.sparse_story_stage_a_render._capture_png") as capture:
                with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                    render_stage_a_payloads(index=index, private_packets=packets,
                        ordered_private_packet_sha256s=hashes, salt_hex="5" * 64,
                        source_by_id={packets[0]["source_id"]: source})
            capture.assert_not_called()


if __name__ == "__main__":
    unittest.main()
