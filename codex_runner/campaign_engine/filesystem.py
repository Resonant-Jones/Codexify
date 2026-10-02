"""Physical target traversal and immutable tracked-symlink evidence."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterator


def physical_files(target: Path, *, include_git: bool = False) -> Iterator[Path]:
    """Enumerate regular files without traversing or reading symlink aliases."""
    for directory, dirs, files in os.walk(target, followlinks=False):
        dirs[:] = sorted(
            name for name in dirs
            if (include_git or name != ".git")
            and not (Path(directory) / name).is_symlink()
        )
        for name in sorted(files):
            path = Path(directory) / name
            if (include_git or name != ".git") and not path.is_symlink() and path.is_file():
                yield path


def tracked_symlink_snapshot(target: Path) -> tuple[tuple[str, str, str], ...]:
    """Require exactly the committed links, unchanged and resolved inside target.

    Resolution is identity evidence only. No link target content is read or
    traversed through the alias, and no filesystem permission is inferred.
    """
    actual: dict[str, str] = {}
    for directory, dirs, files in os.walk(target, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                relative = path.relative_to(target)
                # Reject metadata aliases before Git can read through them.
                if ".git" in relative.parts:
                    raise ValueError("symlink in physical Git metadata")
                actual[str(relative)] = os.readlink(path)
        # Inspect physical Git directories for link metadata too. A worktree's
        # regular .git pointer file is never traversed.
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
    tree = subprocess.run(
        ["git", "-C", str(target), "ls-tree", "-rz", "HEAD"],
        capture_output=True, check=True, timeout=10,
    ).stdout
    tracked: dict[str, str] = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, _, oid = metadata.split()
        if mode == b"120000":
            tracked[os.fsdecode(raw_path)] = os.fsdecode(subprocess.run(
                ["git", "-C", str(target), "cat-file", "blob", oid.decode("ascii")],
                capture_output=True, check=True, timeout=10,
            ).stdout)
    if actual != tracked:
        raise ValueError("symlink topology differs from committed target")
    snapshot = []
    for rel, link_target in sorted(actual.items()):
        resolved = (target / rel).resolve(strict=True)
        if not resolved.is_relative_to(target.resolve()):
            raise ValueError("symlink target escapes disposable worktree")
        snapshot.append((rel, link_target, str(resolved.relative_to(target.resolve()))))
    return tuple(snapshot)
