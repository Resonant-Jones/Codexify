from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs"
ALLOWED_TOP_LEVEL_DIRS = {"archive", "reference", "work"}
ALLOWED_TOP_LEVEL_FILES = {"README.md", "__init__.py"}
BANNED_DOC_PATHS = [
    DOCS_ROOT / "_audits",
    DOCS_ROOT / "_audit_runs",
    DOCS_ROOT / "_campaign_runs",
    DOCS_ROOT / "Campaign",
    DOCS_ROOT / "Campaigns",
    DOCS_ROOT / "tasks",
    DOCS_ROOT / "prompt-docs",
]
WARNING_DUPLICATE_BASENAME_ALLOWLIST = {"README.md", "SECURITY.md", "PLAN.md"}


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not DOCS_ROOT.exists():
        print(f"ERROR: docs root missing: {DOCS_ROOT}")
        return 1

    top_dirs = set()
    top_files = set()
    for entry in DOCS_ROOT.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            top_dirs.add(entry.name)
        elif entry.is_file():
            top_files.add(entry.name)

    unexpected_dirs = sorted(top_dirs - ALLOWED_TOP_LEVEL_DIRS)
    if unexpected_dirs:
        errors.append(
            "Unexpected top-level docs directories: "
            + ", ".join(unexpected_dirs)
        )

    unexpected_files = sorted(top_files - ALLOWED_TOP_LEVEL_FILES)
    if unexpected_files:
        errors.append(
            "Unexpected top-level docs files: " + ", ".join(unexpected_files)
        )

    for dirname in sorted(ALLOWED_TOP_LEVEL_DIRS):
        readme = DOCS_ROOT / dirname / "README.md"
        if not readme.exists():
            errors.append(
                f"Missing required section README: docs/{dirname}/README.md"
            )

    for banned in BANNED_DOC_PATHS:
        if banned.exists():
            errors.append(
                "Legacy/generated path still present under docs: "
                + banned.relative_to(DOCS_ROOT.parent).as_posix()
            )

    canonical_basenames: dict[str, list[str]] = defaultdict(list)
    for root_name in ("reference", "work"):
        root = DOCS_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            canonical_basenames[path.name].append(
                path.relative_to(DOCS_ROOT.parent).as_posix()
            )

    for basename, paths in sorted(canonical_basenames.items()):
        if len(paths) <= 1 or basename in WARNING_DUPLICATE_BASENAME_ALLOWLIST:
            continue
        warnings.append(
            f"Duplicate canonical basename '{basename}': " + ", ".join(paths)
        )

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Docs structure OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
