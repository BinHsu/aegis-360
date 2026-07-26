#!/usr/bin/env python3
"""Validate the vendor-neutral repository handoff contract."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs/handoff/current.md"
REQUIRED_HEADINGS = (
    "## Objective",
    "## Last completed milestone",
    "## Repository state",
    "## Verified",
    "## Rejected",
    "## Pending",
    "## Next commands",
    "## External artifacts",
    "## Active agents",
    "## Safety and claims",
)
REQUIRED_METADATA = (
    "Updated",
    "Repository",
    "Branch",
    "Baseline commit",
    "Remote status",
    "Working tree at checkpoint",
)
FORBIDDEN_PATTERNS = (
    (r"/Users/", "absolute macOS user path"),
    (r"/Volumes/", "absolute macOS volume path"),
    (r"\bfile://", "file URI"),
    (r"(?i)\bsee (the )?(above|previous) (chat|conversation)\b",
     "prior-chat dependency"),
    (r"(?i)\b(open|switch to) agent [0-9a-f-]{8,}\b",
     "opaque agent-session dependency"),
)
SIGNIFICANT_PREFIXES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    ".github/",
    "benchmarks/",
    "config/",
    "docs/adr/",
    "docs/design/",
    "docs/experiments/",
    "docs/research/",
    "docs/README.md",
    "docs/status.md",
    "scripts/",
    "src/",
    "tests/",
    "tools/",
)


def parse_handoff(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("# Current handoff\n"):
        errors.append("document must start with '# Current handoff'")
    metadata: dict[str, str] = {}
    first_heading = min(
        (text.find(heading) for heading in REQUIRED_HEADINGS if heading in text),
        default=len(text),
    )
    for line in text[:first_heading].splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            metadata[key] = value.strip()
    for field in REQUIRED_METADATA:
        if not metadata.get(field):
            errors.append(f"missing metadata: {field}")
    positions = []
    for heading in REQUIRED_HEADINGS:
        position = text.find(heading)
        if position < 0:
            errors.append(f"missing heading: {heading}")
        positions.append(position)
    present_positions = [position for position in positions if position >= 0]
    if present_positions != sorted(present_positions):
        errors.append("required headings are out of order")
    for pattern, label in FORBIDDEN_PATTERNS:
        if re.search(pattern, text):
            errors.append(f"handoff contains forbidden {label}")
    if "```sh" not in section(text, "## Next commands"):
        errors.append("Next commands must contain a sh code fence")
    return metadata, errors


def section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    next_heading = text.find("\n## ", start + len(heading))
    return text[start: next_heading if next_heading >= 0 else len(text)]


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def requires_handoff_update(paths: list[str]) -> bool:
    significant = any(
        path == prefix or path.startswith(prefix)
        for path in paths
        for prefix in SIGNIFICANT_PREFIXES
    )
    return significant and "docs/handoff/current.md" not in paths


def validate_repository(metadata: dict[str, str], base_ref: str | None) -> list[str]:
    errors: list[str] = []
    updated = metadata.get("Updated")
    if updated:
        try:
            parsed = datetime.fromisoformat(updated)
            if parsed.tzinfo is None:
                errors.append("Updated must include a timezone")
        except ValueError:
            errors.append("Updated must be an ISO 8601 timestamp")
    repository = metadata.get("Repository")
    if repository and repository != ROOT.name:
        errors.append(f"Repository must be {ROOT.name!r}")
    branch = git("branch", "--show-current")
    if branch.returncode:
        errors.append(f"cannot determine Git branch: {branch.stderr.strip()}")
    elif metadata.get("Branch") != branch.stdout.strip():
        errors.append("Branch metadata does not match the checked-out branch")
    baseline = metadata.get("Baseline commit")
    if baseline:
        exists = git("cat-file", "-e", f"{baseline}^{{commit}}")
        if exists.returncode:
            errors.append("Baseline commit does not exist")
        else:
            ancestor = git("merge-base", "--is-ancestor", baseline, "HEAD")
            if ancestor.returncode:
                errors.append("Baseline commit is not an ancestor of HEAD")
    if base_ref:
        changed = git("diff", "--name-only", f"{base_ref}...HEAD")
        if changed.returncode:
            errors.append(f"cannot compare base ref {base_ref!r}: {changed.stderr.strip()}")
        else:
            paths = [line for line in changed.stdout.splitlines() if line]
            if requires_handoff_update(paths):
                errors.append(
                    "operationally significant files changed without "
                    "docs/handoff/current.md"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-ref",
        help="fail if significant changes since this Git revision omit current.md",
    )
    arguments = parser.parse_args()
    try:
        text = HANDOFF.read_text(encoding="utf-8")
    except OSError as error:
        print(f"handoff validation failed: {error}", file=sys.stderr)
        return 1
    metadata, errors = parse_handoff(text)
    errors.extend(validate_repository(metadata, arguments.base_ref))
    if errors:
        for error in errors:
            print(f"handoff validation failed: {error}", file=sys.stderr)
        return 1
    print("handoff contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
