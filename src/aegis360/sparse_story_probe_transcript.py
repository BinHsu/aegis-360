"""Closed parser for untrusted sparse-story isolation-probe stdout."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

MAX_TRANSCRIPT_BYTES = 65_536
MAX_DATA_BYTES = 128
OPERATIONS = (
    "bundle_read", "model_read", "prompt_read", "scratch_write",
    "repository_read", "protocol_read", "neighbor_read", "result_read",
    "outside_create", "outside_overwrite", "outside_truncate",
    "outside_rename", "outside_unlink", "process_fork", "ipv4_socket",
    "ipv4_connect", "ipv6_socket", "ipv6_connect", "unix_socket",
    "unix_connect", "forbidden_exec",
)
_INTEGER = re.compile(rb"(?:0|-?[1-9][0-9]{0,19})")
_ERRNO = re.compile(rb"(?:0|[1-9][0-9]{0,9})")
_HEX = re.compile(rb"[0-9a-f]*")


@dataclass(frozen=True)
class ProbeObservation:
    operation: str
    value: int
    errno: int
    data: bytes
    data_sha256: str


def parse_isolation_probe_transcript(value: bytes) -> tuple[ProbeObservation, ...]:
    """Parse exact raw rows without deriving a capability or trusting claims."""
    if (not isinstance(value, bytes) or not 1 <= len(value) <= MAX_TRANSCRIPT_BYTES
            or not value.endswith(b"\n") or b"\r" in value or b"\x00" in value):
        raise ValueError("isolation probe transcript framing is invalid")
    lines = value[:-1].split(b"\n")
    if len(lines) != len(OPERATIONS):
        raise ValueError("isolation probe operation count is invalid")
    observations = []
    for expected, line in zip(OPERATIONS, lines):
        fields = line.split(b"\t")
        if len(fields) != 4 or fields[0] != expected.encode("ascii"):
            raise ValueError("isolation probe operation order is invalid")
        number, error, encoded = fields[1:]
        if (_INTEGER.fullmatch(number) is None or _ERRNO.fullmatch(error) is None
                or _HEX.fullmatch(encoded) is None or len(encoded) % 2
                or len(encoded) > MAX_DATA_BYTES * 2):
            raise ValueError("isolation probe row encoding is invalid")
        parsed_number = int(number)
        parsed_error = int(error)
        if not -(2**63) <= parsed_number < 2**63 or parsed_error > 2**31 - 1:
            raise ValueError("isolation probe integer is out of range")
        data = bytes.fromhex(encoded.decode("ascii"))
        observations.append(ProbeObservation(expected, parsed_number, parsed_error,
            data, hashlib.sha256(data).hexdigest()))
    return tuple(observations)
