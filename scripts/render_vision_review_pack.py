#!/usr/bin/env python3
"""Render privacy-safe, local-only Vision candidate review artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


COLORS = {
    "attention_saliency": "#ffd43b",
    "objectness_saliency": "#4dabf7",
    "human_rectangle": "#ff6b6b",
}


def _annotate(image_path: Path, candidates: list[dict], output: Path) -> None:
    image = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for candidate in candidates:
        box = candidate["boundingBox"]
        x0 = float(box["x"]) * width
        x1 = (float(box["x"]) + float(box["width"])) * width
        # Vision bounding boxes use a bottom-left origin.
        y0 = (1.0 - float(box["y"]) - float(box["height"])) * height
        y1 = (1.0 - float(box["y"])) * height
        color = COLORS.get(candidate["kind"], "#ffffff")
        draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
        label = f'{candidate["id"]} {candidate["kind"]}'
        text_box = draw.textbbox((x0, y0), label)
        label_y = max(0, y0 - (text_box[3] - text_box[1]) - 4)
        draw.rectangle(
            (x0, label_y, x0 + text_box[2] - text_box[0] + 4, y0),
            fill=color,
        )
        draw.text((x0 + 2, label_y + 1), label, fill="#000000")
    image.save(output)


def render_sample(sample_dir: Path, timestamp: float) -> dict:
    evidence = json.loads(
        (sample_dir / "vision-frame-gate.json").read_text(encoding="utf-8")
    )
    by_viewport: dict[str, list[dict]] = {}
    for frame in evidence["frames"]:
        for candidate in frame["candidates"]:
            by_viewport.setdefault(candidate["viewportId"], []).append(candidate)

    annotated: list[Path] = []
    candidate_index = []
    for viewport_id in ("yaw_0", "yaw_90", "yaw_180", "yaw_minus90"):
        source = sample_dir / f"{viewport_id}.png"
        target = sample_dir / f"{viewport_id}.annotated.png"
        candidates = by_viewport.get(viewport_id, [])
        _annotate(source, candidates, target)
        annotated.append(target)
        candidate_index.extend(
            {
                "candidate_id": candidate["id"],
                "kind": candidate["kind"],
                "viewport_id": viewport_id,
            }
            for candidate in candidates
        )

    images = [Image.open(path).convert("RGB") for path in annotated]
    cell_width, cell_height = images[0].size
    sheet = Image.new("RGB", (cell_width * 2, cell_height * 2), "#111111")
    draw = ImageDraw.Draw(sheet)
    for index, (viewport_id, image) in enumerate(
        zip(("yaw_0", "yaw_90", "yaw_180", "yaw_minus90"), images)
    ):
        x = (index % 2) * cell_width
        y = (index // 2) * cell_height
        sheet.paste(image, (x, y))
        draw.rectangle((x, y, x + 125, y + 22), fill="#111111")
        draw.text((x + 5, y + 5), viewport_id, fill="#ffffff")
    contact_name = "contact-sheet.png"
    sheet.save(sample_dir / contact_name)
    return {
        "timestamp_seconds": timestamp,
        "sample_id": sample_dir.name,
        "contact_sheet": f"{sample_dir.name}/{contact_name}",
        "viewport_images": [
            f"{sample_dir.name}/{path.name}" for path in annotated
        ],
        "candidate_count": len(candidate_index),
        "candidates": candidate_index,
        "human_review": {
            "candidate_recall": None,
            "notes": None,
            "reviewed": False,
        },
    }


def main() -> int:
    if len(sys.argv) < 4 or (len(sys.argv) - 3) % 2:
        raise SystemExit(
            f"usage: {sys.argv[0]} OUTPUT_INDEX SOURCE_ID SAMPLE_DIR TIMESTAMP ..."
        )
    output = Path(sys.argv[1])
    if output.exists():
        raise SystemExit("refusing to overwrite review index")
    source_id = sys.argv[2]
    samples = [
        render_sample(Path(sys.argv[index]), float(sys.argv[index + 1]))
        for index in range(3, len(sys.argv), 2)
    ]
    result = {
        "schema_version": 1,
        "source_id": source_id,
        "samples": samples,
        "candidate_count": sum(sample["candidate_count"] for sample in samples),
        "privacy": {
            "contains_absolute_paths": False,
            "contains_identity_labels": False,
        },
        "limitations": [
            "Local review aid only; source and derived frames must not be committed.",
            "Candidate boxes are unreviewed Apple Vision outputs, not ground truth.",
            "Human recall fields are intentionally unset and must not be auto-filled.",
            "Four 100-degree equatorial viewports do not cover polar regions.",
        ],
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
