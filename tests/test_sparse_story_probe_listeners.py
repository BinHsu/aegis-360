import socket
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aegis360.sparse_story_probe_listeners import (  # noqa: E402
    _ProbeListeners, _OwnedProbeListeners,
)


class ProbeListenerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "listeners"
        self.root.mkdir(mode=0o700)

    def listeners(self):
        try: return _ProbeListeners(self.root)
        except PermissionError as error:
            self.skipTest(f"host policy denies local listener bind: {error.errno}")

    def test_live_listeners_have_exact_addresses_and_zero_connections(self):
        with self.listeners() as proof:
            self.assertGreater(proof.ipv4_port, 0)
            self.assertGreater(proof.ipv6_port, 0)
            self.assertTrue(proof.unix_path.is_socket())
            proof.revalidate()
        self.assertFalse((self.root / "listener.sock").exists())

    def test_actual_connections_are_detected_on_each_listener(self):
        for kind in ("ipv4", "ipv6", "unix"):
            with self.subTest(kind=kind), self.listeners() as proof:
                if kind == "unix":
                    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    connection.connect(str(proof.unix_path))
                else:
                    host, port = (("127.0.0.1", proof.ipv4_port) if kind == "ipv4"
                                  else ("::1", proof.ipv6_port))
                    connection = socket.create_connection((host, port), timeout=5)
                with connection, self.assertRaisesRegex(ValueError, "accepted"):
                    proof.revalidate()

    def test_replaced_unix_path_is_preserved_on_close(self):
        proof = self.listeners()
        proof.unix_path.unlink()
        proof.unix_path.write_bytes(b"replacement")
        with self.assertRaisesRegex(ValueError, "preserved"): proof.close()
        self.assertEqual(proof.unix_path.read_bytes(), b"replacement")

    def test_owned_tree_cleans_only_after_reap(self):
        parent = Path(self.temp.name).resolve()
        try: owner = _OwnedProbeListeners(parent)
        except PermissionError as error:
            self.skipTest(f"host policy denies local listener bind: {error.errno}")
        owner.revalidate()
        with self.assertRaisesRegex(ValueError, "before reap"):
            owner.finish_after_reap(None)
        self.assertTrue(owner.root.exists())
        second = _OwnedProbeListeners(parent)
        second.finish_after_reap(0)
        self.assertFalse(second.root.exists())

    def test_owned_tree_preserves_unexpected_child(self):
        parent = Path(self.temp.name).resolve()
        try: owner = _OwnedProbeListeners(parent)
        except PermissionError as error:
            self.skipTest(f"host policy denies local listener bind: {error.errno}")
        extra = owner.root / "unexpected"
        extra.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "tree changed"):
            owner.finish_after_reap(0)
        self.assertEqual(extra.read_bytes(), b"keep")


if __name__ == "__main__": unittest.main()
