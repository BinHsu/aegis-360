import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aegis360.sparse_story_probe_transcript import (  # noqa: E402
    MAX_TRANSCRIPT_BYTES, OPERATIONS, _check_probe_row_values,
    parse_isolation_probe_transcript,
)


def transcript(rows=None):
    rows = rows or [(name, b"-1", b"1", b"") for name in OPERATIONS]
    return b"".join(name.encode() + b"\t" + value + b"\t" + error + b"\t" + data
                    + b"\n" for name, value, error, data in rows)


class ProbeTranscriptTests(unittest.TestCase):
    def test_row_values_are_checked_without_side_effect_authority(self):
        rows = {name: (b"-1", b"1", b"") for name in OPERATIONS}
        for name, prefix in (("bundle_read", b"bundle"),
                ("model_read", b"model"), ("prompt_read", b"prompt")):
            rows[name] = (str(len(prefix)).encode(), b"0", prefix.hex().encode())
        rows["scratch_write"] = (str(len(b"scratch-write-sentinel-v1")).encode(), b"0", b"")
        rows["outside_overwrite"] = (b"-1", b"1", b"open".hex().encode())
        rows["process_fork"] = (b"-1", b"1", b"-1,-1,0".hex().encode())
        for name in ("ipv4_socket", "ipv6_socket", "unix_socket"):
            rows[name] = (b"3", b"0", b"")
        def checked(value):
            parsed = parse_isolation_probe_transcript(transcript([
                (name, *value[name]) for name in OPERATIONS]))
            return _check_probe_row_values(parsed, bundle_prefix=b"bundle",
                model_prefix=b"model", prompt_prefix=b"prompt")
        self.assertTrue(all(checked(rows).values()))
        self.assertEqual(len(checked(rows)), 14)
        for name, replacement in (("bundle_read", (b"5", b"0", b"")),
                ("scratch_write", (b"-1", b"1", b"")),
                ("repository_read", (b"-1", b"2", b"")),
                ("outside_overwrite", (b"-1", b"1", b"other".hex().encode())),
                ("process_fork", (b"-1", b"1", b"")),
                ("ipv4_socket", (b"-1", b"1", b"")),
                ("forbidden_exec", (b"0", b"0", b""))):
            with self.subTest(name=name):
                changed = dict(rows, **{name: replacement})
                self.assertFalse(all(checked(changed).values()))
        with self.assertRaises(ValueError):
            _check_probe_row_values(tuple(), bundle_prefix=b"bundle",
                model_prefix=b"model", prompt_prefix=b"prompt")

    def test_exact_order_and_raw_bytes_parse_without_authority(self):
        rows = [(name, str(number).encode(), b"0", bytes([number]).hex().encode())
                for number, name in enumerate(OPERATIONS)]
        parsed = parse_isolation_probe_transcript(transcript(rows))
        self.assertEqual(tuple(row.operation for row in parsed), OPERATIONS)
        self.assertEqual(parsed[3].data, b"\x03")
        self.assertEqual(len(parsed[3].data_sha256), 64)
        self.assertFalse(hasattr(parsed[0], "allowed"))
        with self.assertRaises(Exception): parsed[0].value = 7

    def test_framing_count_order_duplicate_and_unknown_reject(self):
        valid = transcript()
        invalid = [b"", valid[:-1], valid.replace(b"\n", b"\r\n"),
                   valid + b"extra\t0\t0\t\n", valid.replace(b"bundle_read", b"unknown", 1)]
        lines = valid.splitlines(keepends=True)
        invalid.extend((b"".join(lines[:-1]), b"".join((lines[1], lines[0], *lines[2:])),
                        b"".join((lines[0], lines[0], *lines[2:]))))
        for value in invalid:
            with self.subTest(value=value[:30]):
                with self.assertRaises(ValueError): parse_isolation_probe_transcript(value)

    def test_integer_hex_and_field_canonicalization_reject(self):
        base = [(name, b"-1", b"1", b"") for name in OPERATIONS]
        mutations = []
        for field, value in ((1, b"+1"), (1, b"01"), (1, b"-0"),
                             (1, str(2**63).encode()), (2, b"-1"), (2, b"01"),
                             (2, str(2**31).encode()), (3, b"0"), (3, b"AA"),
                             (3, b"00" * 129)):
            changed = copy.deepcopy(base)
            row = list(changed[0]); row[field] = value; changed[0] = tuple(row)
            mutations.append(transcript(changed))
        mutations.append(transcript(base).replace(b"\n", b"\textra\n", 1))
        for value in mutations:
            with self.assertRaises(ValueError): parse_isolation_probe_transcript(value)

    def test_type_nul_and_size_bound_reject(self):
        with self.assertRaises(ValueError): parse_isolation_probe_transcript("text")
        with self.assertRaises(ValueError): parse_isolation_probe_transcript(
            transcript().replace(b"\t1\t\n", b"\t1\t\x00\n", 1))
        oversized = transcript() + b"x" * (MAX_TRANSCRIPT_BYTES - len(transcript()) + 1)
        with self.assertRaises(ValueError): parse_isolation_probe_transcript(oversized)


if __name__ == "__main__": unittest.main()
