#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-viewport-so3.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

python3 "$repo_dir/tests/generate_vision_viewport_rotation_fixture.py" \
    "$work_dir/fixture"

for axis in yaw pitch roll; do
    ffmpeg -hide_banner -loglevel error -y -framerate 1 \
        -i "$work_dir/fixture/$axis/%d.ppm" \
        -c:v libx264 -crf 0 -pix_fmt yuv444p "$work_dir/$axis.mp4"
    "$repo_dir/scripts/run_vision_motion_probe.sh" \
        "$work_dir/$axis.mp4" "$work_dir/$axis-vision.json" \
        "viewport-$axis" 0 2 1
    python3 "$repo_dir/scripts/fit_vision_viewport_motion.py" \
        "$work_dir/$axis-vision.json" "$work_dir/$axis-fit.json" \
        --horizontal-fov-degrees 90
done

python3 - "$work_dir/fixture/manifest.json" "$work_dir" <<'PY'
import json
import math
from pathlib import Path
import sys

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
work = Path(sys.argv[2])

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

def matrix_rotate(matrix, ray):
    return tuple(sum(matrix[row * 3 + column] * ray[column]
                     for column in range(3)) for row in range(3))

def angular_error(first, second):
    dot = sum(a * b for a, b in zip(first, second))
    return math.acos(max(-1.0, min(1.0, dot)))

for axis, expected in manifest["cases"].items():
    vision = json.loads(
        (work / f"{axis}-vision.json").read_text(encoding="utf-8")
    )
    fit = json.loads((work / f"{axis}-fit.json").read_text(encoding="utf-8"))
    if not fit["observations"]:
        assert vision["summary"]["outcome"] == "no_motion_observations"
        (work / "VISION_UNAVAILABLE").touch()
        print(
            "SKIP: Vision homography unavailable in this sandbox; "
            "run tests/test_vision_viewport_so3_gate.sh on the macOS host",
            file=sys.stderr,
        )
        raise SystemExit(0)
    assert len(fit["observations"]) == 1
    observation = fit["observations"][0]
    quaternion = observation["rotationXyzw"]
    matrix = expected["rotationRowMajor"]
    errors = []
    for ray in ((0.0, 0.0, 1.0), (0.3, 0.0, math.sqrt(0.91)),
                (0.0, 0.25, math.sqrt(0.9375))):
        errors.append(angular_error(
            rotate(quaternion, ray), matrix_rotate(matrix, ray)
        ))
    maximum_degrees = math.degrees(max(errors))
    assert maximum_degrees < 0.35, (axis, maximum_degrees, observation)
    assert math.degrees(observation["residualRadians"]) < 0.2, observation

    # Pin the expected sign independently on all three axes.  A missing
    # Vision inversion or bottom-left/top-left basis change fails here.
    component = {"yaw": 1, "pitch": 0, "roll": 2}[axis]
    expected_sign = {"yaw": 1, "pitch": -1, "roll": 1}[axis]
    assert math.copysign(1.0, quaternion[component]) == expected_sign
    print(
        f"{axis}: max_rotation_error_degrees={maximum_degrees:.6f} "
        f"fit_residual_degrees={math.degrees(observation['residualRadians']):.6f}"
    )
PY

[ ! -e "$work_dir/VISION_UNAVAILABLE" ] || exit 0
echo "PASS: Vision-native homography direction and signs recover known viewport SO(3)"
