#!/usr/bin/env python3
"""Validate the repo-local architecture documentation corpus."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "docs" / "architecture"
README = ARCH / "README.md"
VALIDITY_MATRIX = ARCH / "kb-validity-matrix.md"
RUNTIME_DIAGRAMS = ARCH / "runtime-diagrams-v1.md"
UI_DIAGRAMS = ARCH / "ui-diagrams-v1.md"
ARCHITECTURE_ATLAS = ARCH / "architecture-atlas.md"

REQUIRED_FILES = (
    README,
    ARCH / "00-current-state.md",
    VALIDITY_MATRIX,
    RUNTIME_DIAGRAMS,
    UI_DIAGRAMS,
    ARCHITECTURE_ATLAS,
    ARCH / "system-overview.md",
    ARCH / "flows.md",
    ARCH / "data-and-storage.md",
    ARCH / "config-and-ops.md",
    ARCH / "modules-and-ownership.md",
)

README_LINK_TARGETS = (
    "./00-current-state.md",
    "./kb-validity-matrix.md",
    "./runtime-diagrams-v1.md",
    "./ui-diagrams-v1.md",
    "./architecture-atlas.md",
    "./system-overview.md",
    "./flows.md",
    "./data-and-storage.md",
    "./config-and-ops.md",
    "./modules-and-ownership.md",
)

README_RUNTIME_DIAGRAMS_ENTRY = re.compile(
    r"(?m)^\s*-\s*\[Runtime Diagrams v1\]\(\./runtime-diagrams-v1\.md\)"
)
README_UI_DIAGRAMS_ENTRY = re.compile(
    r"(?m)^\s*-\s*\[UI Diagrams v1\]\(\./ui-diagrams-v1\.md\)"
)
README_ARCHITECTURE_ATLAS_ENTRY = re.compile(
    r"(?m)^\s*-\s*\[Architecture Atlas\]\(\./architecture-atlas\.md\)"
)
LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\((\./[^)\s]+)\)")

VALIDITY_MATRIX_HEADINGS = (
    "## Diagram Source Sets",
    "### Runtime Diagram Source Set v1",
    "### UI Diagram Source Set v1",
    "### Quarantined From First-Pass Diagramming",
)

RUNTIME_DIAGRAMS_HEADINGS = (
    "## Purpose",
    "## Source set used",
    "## Interpretation constraints",
    "## Diagram legend",
    "## Diagram 1: Runtime Topology Overview",
    "## Diagram 2: Chat Completion Sequence",
    "## Diagram 3: Data and Storage Boundaries",
    "## Diagram 4: Subsystem / Ownership Map",
    "## Reviewer guidance",
)

UI_DIAGRAMS_HEADINGS = (
    "## 1. Title and purpose",
    "## 2. Source set used",
    "## 3. Interpretation constraints",
    "## 4. Diagram legend",
    "## 5. Diagram 1: UI Token Hierarchy",
    "## 6. Diagram 2: Structural Layout Model",
    "## 7. Diagram 3: Rendering / Surface Composition Model",
    "## 8. Diagram 4: Diagnostics / Perceptual Stack",
    "## 9. Omitted / intentionally excluded areas",
    "## 10. Reviewer guidance",
)

ARCHITECTURE_ATLAS_HEADINGS = (
    "## Audience",
    "## Reading order",
    "## Current-truth model",
    "## Two-view model",
    "## What this atlas intentionally excludes",
    "## Peer review checklist",
    "## Next documents after the atlas",
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def add_failure(failures: list[str], message: str) -> None:
    failures.append(message)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return None


def check_required_files(failures: list[str]) -> None:
    for path in REQUIRED_FILES:
        if not path.is_file():
            add_failure(failures, f"missing required file: {rel(path)}")


def check_readme_links(failures: list[str]) -> None:
    if not README.is_file():
        return

    text = read_text(README)
    if text is None:
        add_failure(failures, f"unable to read file: {rel(README)}")
        return

    found_targets = set(LOCAL_LINK_RE.findall(text))
    for target in README_LINK_TARGETS:
        if target not in found_targets:
            add_failure(failures, f"{rel(README)}: missing local link {target}")
            continue

        resolved = README.parent / target
        if not resolved.is_file():
            add_failure(
                failures,
                f"{rel(README)}: local link {target} does not resolve to {rel(resolved)}",
            )

    if not README_RUNTIME_DIAGRAMS_ENTRY.search(text):
        add_failure(
            failures,
            f"{rel(README)}: missing link entry for [Runtime Diagrams v1](./runtime-diagrams-v1.md)",
        )

    if not README_UI_DIAGRAMS_ENTRY.search(text):
        add_failure(
            failures,
            f"{rel(README)}: missing link entry for [UI Diagrams v1](./ui-diagrams-v1.md)",
        )

    if not README_ARCHITECTURE_ATLAS_ENTRY.search(text):
        add_failure(
            failures,
            f"{rel(README)}: missing link entry for [Architecture Atlas](./architecture-atlas.md)",
        )


def check_headings(
    failures: list[str], path: Path, headings: tuple[str, ...]
) -> None:
    if not path.is_file():
        return

    text = read_text(path)
    if text is None:
        add_failure(failures, f"unable to read file: {rel(path)}")
        return

    for heading in headings:
        # Use prefix matching to allow additional text after the heading
        # This handles cases like "## 5. Diagram 1: UI Token Hierarchy (high confidence)"
        if not re.search(rf"(?m)^{re.escape(heading)}", text):
            add_failure(failures, f"{rel(path)}: missing heading {heading}")


def main() -> int:
    failures: list[str] = []

    check_required_files(failures)
    check_readme_links(failures)
    check_headings(failures, VALIDITY_MATRIX, VALIDITY_MATRIX_HEADINGS)
    check_headings(failures, RUNTIME_DIAGRAMS, RUNTIME_DIAGRAMS_HEADINGS)
    check_headings(failures, UI_DIAGRAMS, UI_DIAGRAMS_HEADINGS)
    check_headings(failures, ARCHITECTURE_ATLAS, ARCHITECTURE_ATLAS_HEADINGS)

    if failures:
        print("\n".join(failures))
        return 1

    print(
        "Docs validation passed: required architecture docs, README links, and source headings verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
