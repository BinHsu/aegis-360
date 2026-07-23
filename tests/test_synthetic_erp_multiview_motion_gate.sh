#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-synthetic-erp-multiview.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM
config="$repo_dir/config/synthetic-erp-multiview-motion-v1.json"

python3 "$repo_dir/tests/generate_synthetic_erp_motion_sequence.py" "$work_dir/erp"
mkdir "$work_dir/views" "$work_dir/vision"
swiftc "$repo_dir/tools/vision_motion_probe.swift" \
    -o "$work_dir/vision_motion_probe"

python3 - "$config" "$work_dir" "$repo_dir" <<'PY'
import json
from pathlib import Path
import subprocess
import sys

config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
work, repo = Path(sys.argv[2]), Path(sys.argv[3])
viewport = config["viewport"]
fps = config["proxy"]["sampleFps"]
manifest = json.loads((work / "erp" / "manifest.json").read_text(encoding="utf-8"))
frame_count = len(manifest["rawOrientationXyzw"])
for view in config["viewports"]:
    target = work / "views" / view["id"]
    target.mkdir()
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(fps), "-i", str(work / "erp" / "%d.ppm"),
        "-vf", (
            f"v360=input=equirect:output=flat:w={viewport['width']}:"
            f"h={viewport['height']}:yaw={view['yawDegrees']}:"
            f"pitch={view['pitchDegrees']}:"
            f"h_fov={viewport['horizontalFovDegrees']}:interp=linear"
        ),
        str(target / "%d.png"),
    ], check=True)
    frames = [
        {"image": str(target / f"{index + 1}.png"),
         "timestampSeconds": index / fps}
        for index in range(frame_count)
    ]
    probe_input = {
        "sourceId": f"synthetic-{view['id']}",
        "frameWidth": viewport["width"],
        "frameHeight": viewport["height"],
        "frames": frames,
    }
    input_path = work / f"{view['id']}-input.json"
    input_path.write_text(json.dumps(probe_input), encoding="utf-8")
    subprocess.run([
        str(work / "vision_motion_probe"), str(input_path),
        str(work / "vision" / f"{view['id']}.json")
    ], check=True)
PY

python3 "$repo_dir/scripts/assemble_vision_multiview_motion.py" \
    "$config" "$work_dir/vision" "$work_dir/source-motion.json" \
    --source-id synthetic-known-small-rotation

# The same measured sequence must fail closed when a stricter versioned bound
# is selected; this proves the runner enforces the cap before accumulation.
python3 - "$config" "$work_dir/strict-config.json" <<'PY'
import json
from pathlib import Path
import sys
config = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
config["configId"] = "synthetic-six-overlap-110-step0.5-test-v1"
config["fit"]["maxStepRotationDegrees"] = 0.5
Path(sys.argv[2]).write_text(json.dumps(config), encoding="utf-8")
PY
python3 "$repo_dir/scripts/assemble_vision_multiview_motion.py" \
    "$work_dir/strict-config.json" "$work_dir/vision" \
    "$work_dir/strict-source-motion.json" \
    --source-id synthetic-known-small-rotation-strict
python3 - "$work_dir/strict-source-motion.json" <<'PY'
import json
from pathlib import Path
import sys
source = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert source["samples"][1]["state"] == "invalid", source
assert source["gaps"][0]["reason"] == \
    "rotation_step_exceeds_configured_bound", source["gaps"]
PY

python3 - "$work_dir/erp/manifest.json" "$work_dir/source-motion.json" <<'PY'
import json
import math
from pathlib import Path
import sys

expected = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
actual = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
print(json.dumps({
    "states": [sample["state"] for sample in actual["samples"]],
    "orientations": [
        sample["raw_orientation_xyzw"] for sample in actual["samples"]
    ],
    "residuals": [sample["residual_radians"] for sample in actual["samples"]],
}, sort_keys=True))
if any(sample["state"] == "invalid" for sample in actual["samples"]):
    if all(sample["state"] == "invalid" for sample in actual["samples"][1:]):
        print("SKIP: Vision homographies unavailable in this execution environment",
              file=sys.stderr)
        raise SystemExit(77)
    raise AssertionError(actual)
assert not actual["gaps"], actual["gaps"]
assert len(actual["samples"]) == len(expected["rawOrientationXyzw"])
for index, (sample, wanted) in enumerate(zip(
        actual["samples"], expected["rawOrientationXyzw"])):
    observed = sample["raw_orientation_xyzw"]
    error = 2 * math.acos(max(-1.0, min(1.0, abs(sum(
        a * b for a, b in zip(observed, wanted))))))
    assert math.degrees(error) < 1.25, (index, math.degrees(error), sample, wanted)

def inverse(q):
    return (-q[0], -q[1], -q[2], q[3])

def multiply(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )

# Assert each non-commuting interval independently, not only the cumulative
# endpoint, so a multiplication-order bug cannot cancel later in the path.
for index in range(1, len(actual["samples"])):
    observed_previous = actual["samples"][index - 1]["raw_orientation_xyzw"]
    observed_current = actual["samples"][index]["raw_orientation_xyzw"]
    wanted_previous = expected["rawOrientationXyzw"][index - 1]
    wanted_current = expected["rawOrientationXyzw"][index]
    observed_delta = multiply(inverse(observed_previous), observed_current)
    wanted_delta = multiply(inverse(wanted_previous), wanted_current)
    error = 2 * math.acos(max(-1.0, min(1.0, abs(sum(
        a * b for a, b in zip(observed_delta, wanted_delta))))))
    assert math.degrees(error) < 1.25, (
        "interval", index - 1, index, math.degrees(error),
        observed_delta, wanted_delta)
assert actual["estimator"]["fit_bounds"]["max_step_rotation_radians"] == \
    math.radians(1.25)
assert actual["privacy"]["contains_source_path"] is False
print("PASS: bounded synthetic ERP multiview Vision source-motion gate")
PY
