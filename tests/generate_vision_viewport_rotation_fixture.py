#!/usr/bin/env python3
"""Generate exact rectilinear camera-rotation fixtures without image packages."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys


WIDTH = 640
HEIGHT = 360
HFOV_DEGREES = 90.0


def multiply(first, second):
    return tuple(
        sum(first[row * 3 + index] * second[index * 3 + column]
            for index in range(3))
        for row in range(3)
        for column in range(3)
    )


def inverse(matrix):
    a, b, c, d, e, f, g, h, i = matrix
    result = (
        e * i - f * h, c * h - b * i, b * f - c * e,
        f * g - d * i, a * i - c * g, c * d - a * f,
        d * h - e * g, b * g - a * h, a * e - b * d,
    )
    determinant = a * result[0] + b * result[3] + c * result[6]
    return tuple(value / determinant for value in result)


def axis_rotation(axis, angle):
    cosine, sine = math.cos(angle), math.sin(angle)
    if axis == "yaw":
        return (cosine, 0.0, sine, 0.0, 1.0, 0.0, -sine, 0.0, cosine)
    if axis == "pitch":
        # Positive project pitch rotates forward toward +Y: rotation about -X.
        return (1.0, 0.0, 0.0, 0.0, cosine, sine, 0.0, -sine, cosine)
    if axis == "roll":
        return (cosine, -sine, 0.0, sine, cosine, 0.0, 0.0, 0.0, 1.0)
    raise ValueError(axis)


def homography(rotation):
    focal = WIDTH / (2.0 * math.tan(math.radians(HFOV_DEGREES) / 2.0))
    center_x, center_y = (WIDTH - 1.0) / 2.0, (HEIGHT - 1.0) / 2.0
    camera = (
        focal, 0.0, center_x,
        0.0, -focal, center_y,
        0.0, 0.0, 1.0,
    )
    return multiply(camera, multiply(rotation, inverse(camera)))


def base_image():
    pixels = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            # Deterministic broadband texture plus asymmetric landmarks.
            noise = (x * 73 + y * 151 + (x * y) * 17 + (x ^ (y * 3)) * 29) & 255
            red = (noise + (x * 3)) & 255
            green = ((noise * 5) + y * 7) & 255
            blue = ((noise * 11) + x + y * 13) & 255
            if 70 < x < 210 and 45 < y < 125:
                red, green, blue = 245, 35 + (x % 40), 25
            if 390 < x < 555 and 215 < y < 315:
                red, green, blue = 30, 220, 235
            offset = (y * WIDTH + x) * 3
            pixels[offset:offset + 3] = bytes((red, green, blue))
    return bytes(pixels)


def sample(image, x, y):
    if x < 0.0 or y < 0.0 or x > WIDTH - 1.0 or y > HEIGHT - 1.0:
        return (8, 8, 8)
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    x1, y1 = min(WIDTH - 1, x0 + 1), min(HEIGHT - 1, y0 + 1)
    fx, fy = x - x0, y - y0
    result = []
    for channel in range(3):
        def value(px, py):
            return image[(py * WIDTH + px) * 3 + channel]
        top = value(x0, y0) * (1.0 - fx) + value(x1, y0) * fx
        bottom = value(x0, y1) * (1.0 - fx) + value(x1, y1) * fx
        result.append(round(top * (1.0 - fy) + bottom * fy))
    return tuple(result)


def warp(image, source_to_target):
    target_to_source = inverse(source_to_target)
    output = bytearray(WIDTH * HEIGHT * 3)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            denominator = (
                target_to_source[6] * x + target_to_source[7] * y
                + target_to_source[8]
            )
            source_x = (
                target_to_source[0] * x + target_to_source[1] * y
                + target_to_source[2]
            ) / denominator
            source_y = (
                target_to_source[3] * x + target_to_source[4] * y
                + target_to_source[5]
            ) / denominator
            offset = (y * WIDTH + x) * 3
            output[offset:offset + 3] = bytes(sample(image, source_x, source_y))
    return bytes(output)


def write_ppm(path, image):
    with path.open("wb") as handle:
        handle.write(f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii"))
        handle.write(image)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_vision_viewport_rotation_fixture.py OUTPUT_DIR")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    source = base_image()
    cases = {}
    for axis, degrees in (("yaw", 1.0), ("pitch", 2.0), ("roll", 3.0)):
        rotation = axis_rotation(axis, math.radians(degrees))
        source_to_target = homography(rotation)
        case = output / axis
        case.mkdir()
        write_ppm(case / "0.ppm", source)
        write_ppm(case / "1.ppm", warp(source, source_to_target))
        cases[axis] = {
            "degrees": degrees,
            "rotationRowMajor": rotation,
            "sourceToTargetTopLeftHomographyRowMajor": source_to_target,
        }
    with (output / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump({
            "width": WIDTH,
            "height": HEIGHT,
            "horizontalFovDegrees": HFOV_DEGREES,
            "cases": cases,
        }, handle, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
