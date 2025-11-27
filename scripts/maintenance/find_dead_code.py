#!/usr/bin/env python3
"""
Dead code scanner for Codexify

Heuristics:
- Parses Python files under repo (excluding common vendor/caches) and builds a graph of imports.
- Marks modules that are referenced by 'import X' or 'from X import ...'.
- Reports files that are not referenced by any other file and are not obvious entrypoints.

Output:
- Writes a human-readable report to dead_code_report.txt at repo root.
- Also writes a machine-readable JSON list to dead_code_report.json.

Does not move files — use this to review before archiving.
"""
from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

REPO = Path(__file__).resolve().parents[2]
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    "venv_memoryos_cli",
    "__pycache__",
    ".ruff_cache",
    ".pytest_cache",
    ".pnpm-store",
    "frontend/node_modules",
}

# Root packages whose modules we map to dotted names based on folder structure
PACKAGE_ROOTS = {"guardian", "server"}


def should_skip_dir(path: Path) -> bool:
    parts = set(path.as_posix().split("/"))
    return bool(EXCLUDE_DIRS & parts)


def iter_py_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in root.rglob("*.py"):
        if should_skip_dir(p.parent):
            continue
        files.append(p)
    return files


def module_name_for(path: Path) -> str | None:
    """Derive logical module name for files under PACKAGE_ROOTS.

    For files outside those roots, return None (treated as scripts/utilities).
    """
    try:
        rel = path.relative_to(REPO)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    if parts[0] not in PACKAGE_ROOTS:
        return None
    # Strip .py and join
    stem_parts = list(parts)
    stem_parts[-1] = stem_parts[-1][:-3]  # remove .py
    return ".".join(stem_parts)


def is_entrypoint(path: Path) -> bool:
    """Heuristics to keep common entrypoints even if not imported anywhere."""
    name = path.name
    rel = path.as_posix()
    if name in {"__init__.py", "env.py"}:
        return True
    if name in {"main.py", "app.py"}:
        return True
    if "/scripts/" in rel:
        return True
    if "/alembic/" in rel or "/migrations/" in rel:
        return True
    if "/tests/" in rel:
        return True
    return False


def collect_imports(code: str) -> set[str]:
    mods: set[str] = set()
    try:
        tree = ast.parse(code)
    except Exception:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    mods.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module)
    return mods


def main() -> int:
    py_files = iter_py_files(REPO)

    # Map: file -> module_name (or None)
    file_to_module: dict[Path, str | None] = {
        p: module_name_for(p) for p in py_files
    }

    # Collect imported module prefixes
    referenced_modules: set[str] = set()
    for p in py_files:
        try:
            code = p.read_text(encoding="utf-8")
        except Exception:
            continue
        referenced_modules.update(collect_imports(code))

    # Anything referenced as guardian.* or server.* counts as used
    used_prefixes = {
        r for r in referenced_modules if r.split(".")[0] in PACKAGE_ROOTS
    }

    dead_candidates: list[Path] = []
    kept: list[Path] = []
    for p, mod in file_to_module.items():
        if mod is None:
            # Files not within our packages are kept unless clearly unused and not entrypoints
            kept.append(p)
            continue
        if is_entrypoint(p):
            kept.append(p)
            continue
        # If the exact module or any parent is referenced, keep
        parents = [
            ".".join(mod.split(".")[:i])
            for i in range(1, len(mod.split(".")) + 1)
        ]
        if any(par in used_prefixes for par in parents):
            kept.append(p)
        else:
            dead_candidates.append(p)

    # Prepare outputs
    report_txt = REPO / "dead_code_report.txt"
    report_json = REPO / "dead_code_report.json"

    dead_rel = sorted([str(p.relative_to(REPO)) for p in dead_candidates])
    kept_rel = sorted([str(p.relative_to(REPO)) for p in kept])

    report = []
    report.append("Dead code scan (heuristic)\n")
    report.append(f"Repo: {REPO}\n")
    report.append(f"Scanned Python files: {len(py_files)}\n")
    report.append(
        f"Package files (guardian/server): {sum(1 for m in file_to_module.values() if m)}\n"
    )
    report.append(f"Referenced module prefixes: {len(used_prefixes)}\n")
    report.append(f"Dead candidates: {len(dead_rel)}\n")
    report.append("\n# Dead candidates (relative):\n")
    for r in dead_rel[:500]:  # show first 500 to keep file reasonable
        report.append(f"- {r}\n")
    if len(dead_rel) > 500:
        report.append(f"... ({len(dead_rel) - 500} more omitted)\n")

    report_txt.write_text("".join(report), encoding="utf-8")
    report_json.write_text(
        json.dumps({"dead": dead_rel, "kept": kept_rel}, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {report_txt}")
    print(f"Wrote {report_json}")
    print(f"Dead candidates: {len(dead_rel)} (kept: {len(kept_rel)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
