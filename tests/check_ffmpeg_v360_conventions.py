#!/usr/bin/env python3
"""Executable evidence test for the internal-to-FFmpeg v360 convention gate."""

from __future__ import annotations

import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WIDTH = 640
HEIGHT = 360


def render(fixture: Path, yaw: float, pitch: float, h_fov: float = 60) -> bytes:
    command = [
        "ffmpeg", "-v", "error", "-i", str(fixture),
        "-vf", (
            "v360=input=equirect:output=flat:"
            f"w={WIDTH}:h={HEIGHT}:yaw={yaw}:pitch={pitch}:"
            f"h_fov={h_fov}:v_fov=60:interp=nearest,format=rgb24"
        ),
        "-frames:v", "1", "-f", "rawvideo", "-",
    ]
    result = subprocess.run(command, check=True, capture_output=True)
    expected = WIDTH * HEIGHT * 3
    if len(result.stdout) != expected:
        raise AssertionError(f"expected {expected} RGB bytes, got {len(result.stdout)}")
    return result.stdout


def pixel(frame: bytes, x: int = WIDTH // 2 - 1, y: int = HEIGHT // 2 - 1) -> tuple[int, int, int]:
    offset = (y * WIDTH + x) * 3
    return tuple(frame[offset:offset + 3])  # type: ignore[return-value]


def assert_color(actual: tuple[int, int, int], expected: str) -> None:
    predicates = {
        "red": lambda r, g, b: r > 220 and g < 30 and b < 30,
        "green": lambda r, g, b: r < 30 and g > 100 and b < 30,
        "blue": lambda r, g, b: r < 30 and g < 30 and b > 220,
        "yellow": lambda r, g, b: r > 220 and g > 220 and b < 30,
        "magenta": lambda r, g, b: r > 220 and g < 30 and b > 220,
        "cyan": lambda r, g, b: r < 30 and g > 220 and b > 220,
    }
    if not predicates[expected](*actual):
        raise AssertionError(f"expected {expected}, got RGB{actual}")


def orange_x(frame: bytes) -> float:
    points = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = pixel(frame, x, y)
            if r > 220 and 70 < g < 180 and b < 30:
                points.append(x)
    if not points:
        raise AssertionError("orange +30 degree marker was not visible")
    return sum(points) / len(points)


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg is required", file=sys.stderr)
        return 1
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="aegis-v360-conventions-") as temp:
        fixture = Path(temp) / "fixture.mkv"
        subprocess.run(
            [str(repo / "scripts/generate_v360_convention_fixture.sh"), str(fixture)],
            check=True,
        )

        cases = (
            (0, 0, "red"),
            (90, 0, "blue"),
            (-90, 0, "green"),
            (0, 60, "yellow"),
            (0, -60, "magenta"),
            (180, 0, "cyan"),
            (-180, 0, "cyan"),
        )
        for yaw, pitch, expected in cases:
            assert_color(pixel(render(fixture, yaw, pitch)), expected)

        narrow_x = orange_x(render(fixture, 0, 0, 60))
        wide_x = orange_x(render(fixture, 0, 0, 120))
        center = (WIDTH - 1) / 2
        if not narrow_x > wide_x > center:
            raise AssertionError(
                "positive-yaw marker/FOV mapping is inconsistent: "
                f"60deg x={narrow_x:.2f}, 120deg x={wide_x:.2f}"
            )
        for h_fov, actual_x in ((60, narrow_x), (120, wide_x)):
            expected_x = center + (WIDTH / 2) * (
                math.tan(math.radians(20)) / math.tan(math.radians(h_fov / 2))
            )
            if abs(actual_x - expected_x) > 6:
                raise AssertionError(
                    f"h_fov={h_fov} marker x={actual_x:.2f}, "
                    f"expected approximately {expected_x:.2f}"
                )

        # A flat view with valid ERP input must not synthesize black projection
        # gaps, including a seam-centered view and a pole-adjacent view.
        black_counts = []
        for yaw, pitch in ((180, 0), (0, 89), (0, -89)):
            frame = render(fixture, yaw, pitch, 120)
            black = sum(
                pixel(frame, x, y) == (0, 0, 0)
                for y in range(HEIGHT)
                for x in range(WIDTH)
            )
            if black:
                raise AssertionError(f"yaw={yaw}, pitch={pitch} produced {black} black pixels")
            black_counts.append(black)

    print(
        "PASS: FFmpeg yaw/pitch signs, seam, poles, horizontal FOV, and "
        "gap-free flat projection match the internal ERP convention; "
        f"orange(+20deg) centroid x: h_fov=60 -> {narrow_x:.2f}, "
        f"h_fov=120 -> {wide_x:.2f}; black pixels={black_counts}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
