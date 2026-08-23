#!/usr/bin/env python3
"""Fail closed unless every transient review frame matches its declared probe."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def main() -> int:
    media_dir = Path(os.environ["AEGIS_REVIEW_MEDIA_DIR"])
    index_path = Path(os.environ["AEGIS_REVIEW_MEDIA_INDEX"])
    index = json.loads(index_path.read_bytes())
    expected_schemas = {
        "aegis360.transient-review-media-index.v1",
        "aegis360.transient-story-review-media-index.v1",
        "aegis360.transient-story-segment-review-media-index.v1",
    }
    if index.get("schema_version") not in expected_schemas or index.get("audio_provided") is not False:
        raise ValueError("transient review index is invalid")
    frames = index.get("frames")
    if not isinstance(frames, list) or not frames:
        raise ValueError("transient review index has no frames")
    for frame in frames:
        path = media_dir / frame["filename"]
        if path.parent != media_dir or not path.is_file() or path.stat().st_size == 0:
            raise ValueError("transient review frame is missing")
        probe = json.loads(subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(path),
        ], check=True, capture_output=True, text=True).stdout)["streams"]
        if len(probe) != 1 or probe[0] != {"width": frame["width"], "height": frame["height"]}:
            raise ValueError("transient review frame dimensions do not match")
    print(json.dumps({"frame_count": len(frames), "schema_version": index["schema_version"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
