#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/aegis-vision-sequence-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

: > "$work_dir/fixture.webm"
: > "$work_dir/calls.log"

sed 's/^+//' > "$work_dir/fake-swiftc" <<'SH'
+#!/bin/sh
+set -eu
+printf 'compile\n' >> "$CALLS_LOG"
+[ "$2" = "-o" ]
+sed 's/^+//' > "$3" <<'GATE'
+#!/bin/sh
+set -eu
+python3 - "$1" "$2" "$CALLS_LOG" <<'PY'
+import json
+import os
+import sys
+
+source = json.load(open(sys.argv[1], encoding="utf-8"))
+assert len(source["viewports"]) == 4
+assert all(os.path.isfile(item["image"]) for item in source["viewports"])
+with open(sys.argv[3], "a", encoding="utf-8") as log:
+    log.write("vision\n")
+frames = []
+for viewport in source["viewports"]:
+    frames.append({
+        "sourceId": source["sourceId"],
+        "frameIndex": source["frameIndex"],
+        "timestampSeconds": viewport["timestampSeconds"],
+        "viewportCount": 1,
+        "candidates": [],
+        "requests": [],
+    })
+json.dump({"frames": frames}, open(sys.argv[2], "w", encoding="utf-8"))
+PY
+GATE
+chmod +x "$3"
SH
chmod +x "$work_dir/fake-swiftc"

sed 's/^+//' > "$work_dir/fake-ffmpeg" <<'SH'
+#!/bin/sh
+set -eu
+eval "output=\${$#}"
+printf 'extract %s\n' "$output" >> "$CALLS_LOG"
+: > "$output"
SH
chmod +x "$work_dir/fake-ffmpeg"

CALLS_LOG="$work_dir/calls.log" \
AEGIS_SWIFTC="$work_dir/fake-swiftc" \
AEGIS_FFMPEG="$work_dir/fake-ffmpeg" \
python3 "$repo_dir/scripts/run_vision_sequence_gate.py" \
    "$work_dir/fixture.webm" "$work_dir/evidence.json" \
    synthetic-sequence 1 1 2

python3 - "$work_dir/evidence.json" "$work_dir/calls.log" "$work_dir" <<'PY'
import json
import pathlib
import sys

evidence = json.load(open(sys.argv[1], encoding="utf-8"))
calls = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8").splitlines()
assert calls.count("compile") == 1
assert calls.count("vision") == 2
assert len([line for line in calls if line.startswith("extract ")]) == 8
assert evidence["sourceId"] == "synthetic-sequence"
assert evidence["sequence"]["sampleCount"] == 2
assert len(evidence["frames"]) == 8
assert evidence["privacy"]["temporaryViewportImagesDeletedAfterEachSample"] is True
assert sys.argv[3] not in json.dumps(evidence)
for line in calls:
    if line.startswith("extract "):
        assert not pathlib.Path(line.removeprefix("extract ")).exists()
PY

if CALLS_LOG="$work_dir/calls.log" \
    AEGIS_SWIFTC="$work_dir/fake-swiftc" \
    AEGIS_FFMPEG="$work_dir/fake-ffmpeg" \
    python3 "$repo_dir/scripts/run_vision_sequence_gate.py" \
        "$work_dir/fixture.webm" "$work_dir/evidence.json" \
        synthetic-sequence 1 1 2 \
        >"$work_dir/overwrite.stdout" 2>"$work_dir/overwrite.stderr"; then
    echo "sequence runner unexpectedly overwrote evidence" >&2
    exit 1
fi
grep -q "refusing to overwrite" "$work_dir/overwrite.stderr"

if CALLS_LOG="$work_dir/calls.log" \
    AEGIS_SWIFTC="$work_dir/fake-swiftc" \
    AEGIS_FFMPEG="$work_dir/fake-ffmpeg" \
    python3 "$repo_dir/scripts/run_vision_sequence_gate.py" \
        "$work_dir/fixture.webm" "$work_dir/too-long.json" \
        synthetic-sequence 0 301 1 \
        >"$work_dir/bounds.stdout" 2>"$work_dir/bounds.stderr"; then
    echo "sequence runner unexpectedly accepted an unbounded duration" >&2
    exit 1
fi
grep -q "bounded maximum" "$work_dir/bounds.stderr"

echo "Vision sequence gate fake orchestration test passed"
