#!/usr/bin/env python3
"""Generate a textured ERP sequence with a known bounded rig rotation path."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys

WIDTH, HEIGHT = 1024, 512
POSES_DEGREES = [
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (1.0, 0.5, 0.0),
    (1.0, 1.0, 0.0),
    (1.0, 1.0, 0.5),
    (1.0, 1.0, 1.0),
]


def multiply(first, second):
    ax, ay, az, aw = first
    bx, by, bz, bw = second
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def axis_angle(axis, angle):
    scale = math.sin(angle / 2.0)
    return axis[0] * scale, axis[1] * scale, axis[2] * scale, math.cos(angle / 2.0)


def pose(yaw, pitch, roll):
    return multiply(
        axis_angle((0.0, 1.0, 0.0), math.radians(yaw)),
        multiply(
            axis_angle((1.0, 0.0, 0.0), math.radians(-pitch)),
            axis_angle((0.0, 0.0, 1.0), math.radians(roll)),
        ),
    )


def inverse(quaternion):
    return -quaternion[0], -quaternion[1], -quaternion[2], quaternion[3]


def rotate(quaternion, ray):
    x, y, z, w = quaternion
    tx = 2.0 * (y * ray[2] - z * ray[1])
    ty = 2.0 * (z * ray[0] - x * ray[2])
    tz = 2.0 * (x * ray[1] - y * ray[0])
    return (
        ray[0] + w * tx + y * tz - z * ty,
        ray[1] + w * ty + z * tx - x * tz,
        ray[2] + w * tz + x * ty - y * tx,
    )


def texture(yaw, pitch):
    # Band-limited, seam-periodic asymmetric texture.  Avoid per-pixel hash
    # noise: rotating that signal requires filtering and otherwise makes
    # adjacent sub-degree samples decorrelate before Vision sees them.
    red = (
        128 + 42 * math.sin(13 * yaw + 7 * pitch)
        + 31 * math.sin(29 * yaw - 11 * pitch)
        + 20 * math.cos(71 * yaw + 43 * pitch)
        + 14 * math.sin(137 * yaw - 61 * pitch)
    )
    green = (
        125 + 44 * math.cos(17 * yaw - 9 * pitch)
        + 29 * math.sin(31 * yaw + 5 * pitch)
        + 18 * math.cos(83 * yaw - 47 * pitch)
        + 13 * math.sin(149 * yaw + 73 * pitch)
    )
    blue = (
        130 + 39 * math.sin(11 * yaw - 17 * pitch)
        + 33 * math.cos(23 * yaw + 13 * pitch)
        + 21 * math.sin(97 * yaw + 53 * pitch)
        + 12 * math.cos(163 * yaw - 67 * pitch)
    )
    # Smooth localized landmarks break periodic aliases without introducing
    # sampling discontinuities.
    for center_yaw, center_pitch, color in (
        (-2.1, 0.45, (70, -25, -40)),
        (0.35, -0.25, (-35, 65, 45)),
        (2.45, 0.10, (20, -40, 75)),
    ):
        delta_yaw = math.atan2(
            math.sin(yaw - center_yaw), math.cos(yaw - center_yaw))
        distance = delta_yaw * delta_yaw + (pitch - center_pitch) ** 2
        weight = math.exp(-distance / 0.035)
        red += color[0] * weight
        green += color[1] * weight
        blue += color[2] * weight
    return tuple(max(0, min(255, round(value)))
                 for value in (red, green, blue))


def render(rig_orientation):
    pixels = bytearray(WIDTH * HEIGHT * 3)
    # R maps source-local rays to the stable reference world.  Each output ERP
    # pixel is a source-local ray and samples the stable texture at R * ray.
    for y in range(HEIGHT):
        pitch = math.pi / 2.0 - math.pi * ((y + 0.5) / HEIGHT)
        cosine = math.cos(pitch)
        for x in range(WIDTH):
            yaw = 2.0 * math.pi * ((x + 0.5) / WIDTH) - math.pi
            local = (math.sin(yaw) * cosine, math.sin(pitch), math.cos(yaw) * cosine)
            world = rotate(rig_orientation, local)
            sample_yaw = math.atan2(world[0], world[2])
            sample_pitch = math.asin(max(-1.0, min(1.0, world[1])))
            offset = (y * WIDTH + x) * 3
            pixels[offset:offset + 3] = bytes(texture(sample_yaw, sample_pitch))
    return pixels


def write_ppm(path, pixels):
    with path.open("wb") as handle:
        handle.write(f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii"))
        handle.write(pixels)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_synthetic_erp_motion_sequence.py OUTPUT_DIR")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    orientations = [pose(*values) for values in POSES_DEGREES]
    for index, orientation in enumerate(orientations):
        write_ppm(output / f"{index}.ppm", render(orientation))
    with (output / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump({
            "schemaVersion": "aegis360.synthetic-erp-motion.v1",
            "width": WIDTH,
            "height": HEIGHT,
            "sampleFps": 2.0,
            "posesDegrees": POSES_DEGREES,
            "rawOrientationXyzw": orientations,
        }, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    main()
