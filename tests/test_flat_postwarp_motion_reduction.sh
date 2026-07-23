#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-postwarp-motion.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

width=320
height=180
fps=30

# An asymmetric, static texture makes all temporal change attributable to the
# known synthetic camera path rather than scene or subject motion.
ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=0x303030:s=400x260:d=0.1,drawgrid=w=23:h=19:t=2:c=white@0.55,drawbox=x=82:y=66:w=73:h=41:c=red:t=fill,drawbox=x=231:y=147:w=91:h=54:c=cyan:t=fill,drawbox=x=270:y=45:w=31:h=75:c=yellow:t=fill" \
    -frames:v 1 "$work_dir/base.png"

python3 - "$work_dir/generate.sh" "$work_dir/evidence.json" <<'PY'
import json
import math
import sys

# Deliberately alternate both translation and rotation.  The transform maps
# the centered, unjittered crop into each raw frame in top-left image
# coordinates, matching the planner's documented convention.
key_positions = [
    (0, 0, 0), (12, -7, 0.050), (-11, 8, -0.045), (10, 6, 0.040),
    (-12, -6, -0.050), (11, -8, 0.045), (-10, 7, -0.040),
    (12, 5, 0.050), (-11, -7, -0.045), (0, 0, 0),
]
cx, cy = 160.0, 90.0

def matrix(tx, ty, angle):
    c, s = math.cos(angle), math.sin(angle)
    return (c, -s, cx + tx - c * cx + s * cy,
            s, c, cy + ty - s * cx - c * cy,
            0.0, 0.0, 1.0)

def multiply(a, b):
    return tuple(sum(a[r * 3 + k] * b[k * 3 + c] for k in range(3))
                 for r in range(3) for c in range(3))

def inverse(m):
    a, b, tx, c, d, ty, _, _, _ = m
    det = a * d - b * c
    return (d / det, -b / det, (b * ty - d * tx) / det,
            -c / det, a / det, (c * tx - a * ty) / det,
            0.0, 0.0, 1.0)

raw = [matrix(*position) for position in key_positions]
observations = [{
    "frameIndex": 0, "timestampSeconds": 0, "state": "reference",
    "homographyRowMajor": None,
}]
for index in range(1, len(raw)):
    observations.append({
        "frameIndex": index,
        "timestampSeconds": index / 10,
        "state": "measured",
        "homographyRowMajor": list(multiply(raw[index], inverse(raw[index - 1]))),
    })
json.dump({
    "schemaVersion": 1,
    "sourceId": "known-translation-rotation-jitter",
    "frameWidth": 320,
    "frameHeight": 180,
    "observations": observations,
}, open(sys.argv[2], "w"), indent=2)

with open(sys.argv[1], "w") as handle:
    handle.write("#!/bin/sh\nset -eu\n")
    output_count = (len(key_positions) - 1) * 3 + 1
    for index in range(output_count):
        key_index = min(index // 3, len(key_positions) - 2)
        fraction = (index % 3) / 3
        if index == output_count - 1:
            key_index = len(key_positions) - 2
            fraction = 1
        first = key_positions[key_index]
        second = key_positions[key_index + 1]
        tx, ty, angle = (
            first[item] + fraction * (second[item] - first[item])
            for item in range(3)
        )
        # FFmpeg rotate uses the same visual sign as the top-left-coordinate
        # matrix above. Cropping at (margin-t) translates content by +t.
        handle.write(
            'ffmpeg -hide_banner -loglevel error -y -i "$1/base.png" '
            f'-vf "rotate={angle}:ow=iw:oh=ih:fillcolor=0x303030,'
            f'crop=320:180:{40 - tx}:{40 - ty}" '
            f'-frames:v 1 "$1/frame-{index:02d}.png"\n'
        )
PY
chmod +x "$work_dir/generate.sh"
"$work_dir/generate.sh" "$work_dir"

ffmpeg -hide_banner -loglevel error -y -framerate "$fps" \
    -i "$work_dir/frame-%02d.png" \
    -c:v libx264 -crf 10 -pix_fmt yuv420p \
    "$work_dir/jittered.mp4"

PYTHONPATH="$repo_dir/src" python3 "$repo_dir/scripts/plan_flat_stabilization.py" \
    "$work_dir/evidence.json" "$work_dir/plan.json" \
    --measurement-direction previous_to_current --smoothing-radius 0.35

# AVAssetWriter uses VideoToolbox for H.264. Report a distinct infrastructure
# outcome instead of misdiagnosing encoder exhaustion as a warp regression.
if ! ffmpeg -hide_banner -loglevel error -y \
    -f lavfi -i "color=c=black:s=${width}x${height}:d=0.1" \
    -c:v h264_videotoolbox -frames:v 1 "$work_dir/encoder-preflight.mp4"; then
    echo "ENVIRONMENT_UNAVAILABLE: VideoToolbox H.264 encoder cannot create a compression session" >&2
    exit 77
fi

"$repo_dir/scripts/render_flat_postwarp_native.sh" \
    "$work_dir/jittered.mp4" "$work_dir/plan.json" "$work_dir/stabilized.mp4"

python3 "$repo_dir/scripts/measure_temporal_frame_difference.py" \
    "$work_dir/jittered.mp4" --width "$width" --height "$height" >"$work_dir/before.json"
python3 "$repo_dir/scripts/measure_temporal_frame_difference.py" \
    "$work_dir/stabilized.mp4" --width "$width" --height "$height" >"$work_dir/after.json"

python3 - "$work_dir/before.json" "$work_dir/after.json" <<'PY'
import json
import sys

before = json.load(open(sys.argv[1]))
after = json.load(open(sys.argv[2]))
assert before["framePairCount"] == after["framePairCount"], (before, after)
ratio = after["mean"] / before["mean"]
assert ratio < 0.65, {
    "message": "native stabilization did not materially reduce synthetic motion",
    "before": before["mean"],
    "after": after["mean"],
    "ratio": ratio,
}
print(f"motion mean {before['mean']:.4f} -> {after['mean']:.4f} (ratio {ratio:.3f})")
PY

echo "flat post-warp planner-to-native-renderer motion-reduction gate passed"
