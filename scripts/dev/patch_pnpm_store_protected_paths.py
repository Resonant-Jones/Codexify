#!/usr/bin/env python3
"""Drop macOS-protected developer paths from a pnpm store's package indexes.

macOS refuses writes into any directory named ``.vscode`` or ``.idea``, and to
any file named ``.gitmodules``. These are the clone-time code-execution
vectors macOS protects. Three packages in the Codexify lockfile ship such
paths (``xhr@2.6.0``, ``iconv-lite@0.6.3``, ``extsprintf@1.3.0``), so
``pnpm install`` fails with ``EPERM`` while extracting them.

This script removes those entries from a pnpm store's ``*-index.json`` package
indexes, leaving a ``.codexify-backup`` copy of each modified index beside it.
It is a **host workaround**, not a release qualification step: see
``docs/dev/frontend-install-workarounds.md``.

Usage::

    python3 scripts/dev/patch_pnpm_store_protected_paths.py <store-dir>

``<store-dir>`` is a pnpm store root, e.g. ``.pnpm-store`` at the repository
root. Omitting it defaults to ``.pnpm-store`` relative to the current
directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

PROTECTED_DIRS = (".vscode", ".idea")
PROTECTED_FILES = (".gitmodules",)
BACKUP_SUFFIX = ".codexify-backup"


def is_protected(path: str) -> bool:
    """Return True when a package-relative path is macOS-protected."""
    parts = path.replace("\\", "/").split("/")
    if not parts:
        return False
    if parts[0] in PROTECTED_DIRS:
        return True
    return parts[-1] in PROTECTED_FILES


def patch_store(store_dir: str) -> int:
    """Patch every package index under ``store_dir``. Returns the patch count."""
    if not os.path.isdir(store_dir):
        print(f"error: store directory not found: {store_dir}", file=sys.stderr)
        return 1

    patched = 0
    scanned = 0
    for root, _dirs, files in os.walk(store_dir):
        for name in files:
            if not name.endswith("-index.json"):
                continue
            index_path = os.path.join(root, name)
            scanned += 1
            try:
                with open(index_path) as handle:
                    data = json.load(handle)
            except (OSError, ValueError):
                continue
            files_map = data.get("files")
            if not isinstance(files_map, dict):
                continue
            removed = [key for key in files_map if is_protected(key)]
            if not removed:
                continue
            backup = index_path + BACKUP_SUFFIX
            if not os.path.exists(backup):
                shutil.copy2(index_path, backup)
            for key in removed:
                del files_map[key]
            with open(index_path, "w") as handle:
                json.dump(data, handle, separators=(",", ":"))
            patched += 1
            print(
                f"patched {data.get('name')}@{data.get('version')}: "
                f"{', '.join(sorted(removed))}"
            )

    print(f"scanned {scanned} package indexes; patched {patched}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "store_dir",
        nargs="?",
        default=".pnpm-store",
        help="pnpm store root to patch (default: .pnpm-store)",
    )
    args = parser.parse_args(argv)
    return patch_store(args.store_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
