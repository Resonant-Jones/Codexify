#!/usr/bin/env python3
"""
Organize and Modularize Scripts

- Scans the `scripts/` directory recursively and classifies each .py/.sh file
  into build/dev/maintenance/misc based on filename keywords.
- Writes a report to `scripts/module_report.txt` mapping each file -> category.
- Ensures each subfolder in `scripts/` is importable by creating `__init__.py`
  where missing (skips `__pycache__`).

This script does not move files; it only reports classification and adds
missing `__init__.py` files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple


SCRIPTS_DIR = Path(__file__).resolve().parents[1]  # scripts/
REPO_ROOT = SCRIPTS_DIR.parent
REPORT_PATH = SCRIPTS_DIR / "module_report.txt"


# Keyword rules
MAINTENANCE_KEYWORDS = [
    "check",
    "verify",
    "setup",
    "fix",
    "bootstrap",
    "imprint",
    "env",
    "manage",
    "dependencies",
    "system",
    "test_",
    "pg_",
    "summonriven",
    "autopush",
]

DEV_KEYWORDS = [
    "dev",
    "run_system",
    "run_test",
    "kimi",
    "debug",
    "orchestrate",
    "flow",
    "loop",
    "key",
    "seal",
]

BUILD_KEYWORDS = [
    "build",
    "generate_docs",
    "setup.py",
    "deploy",
    "release",
]


def classify_script(path: Path) -> str:
    """Classify a script path into one of: maintenance/dev/build/misc.

    Classification is done on a lowercase representation of the relative path
    from scripts/, so folder names can also influence classification.
    """
    rel = str(path.relative_to(SCRIPTS_DIR)).lower()

    def has_any(keywords: List[str]) -> bool:
        return any(k in rel for k in keywords)

    if has_any(MAINTENANCE_KEYWORDS):
        return "maintenance"
    if has_any(DEV_KEYWORDS):
        return "dev"
    if has_any(BUILD_KEYWORDS):
        return "build"
    return "misc"


def iter_script_files(base: Path) -> List[Path]:
    files: List[Path] = []
    for p in base.rglob("*"):
        if p.is_dir():
            # Skip caches
            if p.name == "__pycache__":
                # Skip walking into __pycache__
                continue
            continue
        if not p.exists():
            continue
        if p.suffix.lower() in {".py", ".sh"}:
            files.append(p)
    return files


def ensure_init_py(base: Path) -> List[Path]:
    """Ensure every subfolder of `base` has an `__init__.py` (recursive).

    Returns a list of created files.
    """
    created: List[Path] = []
    for d in base.rglob("*"):
        if not d.is_dir():
            continue
        if d.name == "__pycache__":
            continue
        init_path = d / "__init__.py"
        if not init_path.exists():
            init_path.touch()
            created.append(init_path)
    return created


def main() -> int:
    if not SCRIPTS_DIR.exists():
        print(f"scripts folder not found at: {SCRIPTS_DIR}")
        return 1

    files = iter_script_files(SCRIPTS_DIR)

    rows: List[str] = []
    rows.append("# Module classification report for scripts/\n")
    rows.append("# file -> category/\n")

    for f in sorted(files, key=lambda p: str(p.relative_to(SCRIPTS_DIR))):
        cat = classify_script(f)
        rel = f.relative_to(SCRIPTS_DIR)
        rows.append(f"{rel} -> {cat}/\n")

    # Write report
    REPORT_PATH.write_text("".join(rows), encoding="utf-8")
    print(f"Wrote classification report: {REPORT_PATH}")

    # Ensure __init__.py in all script subfolders
    created = ensure_init_py(SCRIPTS_DIR)
    if created:
        print("Created __init__.py in:")
        for p in created:
            print(f" - {p.relative_to(REPO_ROOT)}")
    else:
        print("All script subfolders already had __init__.py")

    # Summary (print a few mappings to stdout)
    print("\nSample classifications:")
    for line in rows[2:12]:  # skip header lines, show up to 10 entries
        print(" ", line.strip())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

