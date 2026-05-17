"""Shared path guard for write containment checks.

This module provides a fail-closed primitive that validates a candidate write
path under an allowed root while defending against lexical traversal and
symlink-based escapes.
"""

from __future__ import annotations

import errno
import os
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISLNK
from typing import Literal

ScopeKind = Literal[
    "thread",
    "project",
    "workspace",
    "memory",
    "artifact",
    "sandbox",
    "document",
]


@dataclass(frozen=True)
class ValidatedPath:
    requested_path: str
    normalized_path: Path
    resolved_parent_path: Path
    allowed_root: Path
    scope_kind: ScopeKind
    scope_id: str


class PathGuardError(ValueError):
    """Raised when write-path validation fails."""

    code: str

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


_ERR_INVALID_SCOPE_ID = "PATH_GUARD_INVALID_SCOPE_ID"
_ERR_INVALID_ALLOWED_ROOT = "PATH_GUARD_INVALID_ALLOWED_ROOT"
_ERR_ALLOWED_ROOT_NOT_FOUND = "PATH_GUARD_ALLOWED_ROOT_NOT_FOUND"
_ERR_ALLOWED_ROOT_NOT_DIRECTORY = "PATH_GUARD_ALLOWED_ROOT_NOT_DIRECTORY"
_ERR_NULL_BYTE = "PATH_GUARD_NULL_BYTE"
_ERR_PATH_TRAVERSAL = "PATH_GUARD_PATH_TRAVERSAL"
_ERR_DANGLING_SYMLINK = "PATH_GUARD_DANGLING_SYMLINK"
_ERR_SYMLINK_LOOP = "PATH_GUARD_SYMLINK_LOOP"
_ERR_UNVERIFIABLE = "PATH_GUARD_UNVERIFIABLE"
_ERR_SYMLINK_ESCAPE = "PATH_GUARD_SYMLINK_ESCAPE"


def _normalize_candidate_path(
    requested_path: str | Path, root: Path
) -> tuple[str, Path]:
    requested_text = str(requested_path)
    if "\x00" in requested_text:
        raise PathGuardError(
            f"Requested path contains a null byte: {requested_text!r}",
            code=_ERR_NULL_BYTE,
        )

    raw_candidate = Path(requested_text)
    if raw_candidate.is_absolute():
        base = raw_candidate
    else:
        base = root / raw_candidate

    # Lexical normalization only: collapse ".." and "." without requiring the
    # path to exist and without canonicalizing through symlink resolution.
    normalized = Path(os.path.normpath(str(base)))
    return requested_text, normalized


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_deepest_existing(path: Path) -> Path:
    """Resolve a path via the deepest existing ancestor.

    When the final target path does not yet exist, walk upward until an
    existing ancestor is found, resolve it (including symlinks), then rejoin
    the non-existing tail.
    """

    tail: list[str] = []
    current = path

    while True:
        try:
            resolved_current = current.resolve(strict=True)
            rebuilt = resolved_current
            for segment in reversed(tail):
                rebuilt = rebuilt / segment
            return rebuilt
        except FileNotFoundError:
            # Distinguish "missing path segment" from "dangling symlink".
            try:
                stat_result = current.lstat()
            except FileNotFoundError:
                pass
            else:
                if S_ISLNK(stat_result.st_mode):
                    raise PathGuardError(
                        f"Dangling symlink blocks containment verification: {current}",
                        code=_ERR_DANGLING_SYMLINK,
                    )
            parent = current.parent
            if parent == current:
                raise PathGuardError(
                    f"Could not resolve an existing ancestor for: {path}",
                    code=_ERR_UNVERIFIABLE,
                )
            tail.append(current.name)
            current = parent
        except RuntimeError as exc:
            raise PathGuardError(
                f"Symlink loop detected while resolving: {current}",
                code=_ERR_SYMLINK_LOOP,
            ) from exc
        except OSError as exc:
            if exc.errno in {errno.ENOTDIR, errno.ENAMETOOLONG}:
                parent = current.parent
                if parent == current:
                    raise PathGuardError(
                        f"Could not resolve an existing ancestor for: {path}",
                        code=_ERR_UNVERIFIABLE,
                    ) from exc
                tail.append(current.name)
                current = parent
                continue
            if exc.errno == errno.ELOOP:
                raise PathGuardError(
                    f"Symlink loop detected while resolving: {current}",
                    code=_ERR_SYMLINK_LOOP,
                ) from exc
            raise PathGuardError(
                f"Failed to verify path containment ({exc}): {current}",
                code=_ERR_UNVERIFIABLE,
            ) from exc


def validate_write_path(
    requested_path: str | Path,
    allowed_root: str | Path,
    *,
    scope_kind: ScopeKind,
    scope_id: str,
) -> ValidatedPath:
    """Validate that a requested write path remains inside an allowed root.

    This function is fail-closed:
    - rejects lexical traversal outside the root
    - rejects symlink escapes outside the root
    - rejects dangling symlink and unresolvable states
    - never creates files/directories or mutates filesystem state
    """

    normalized_scope_id = str(scope_id or "").strip()
    if not normalized_scope_id:
        raise PathGuardError(
            "scope_id must be a non-empty string",
            code=_ERR_INVALID_SCOPE_ID,
        )

    raw_root = Path(str(allowed_root))
    if str(raw_root).strip() == "":
        raise PathGuardError(
            "allowed_root must be a non-empty path",
            code=_ERR_INVALID_ALLOWED_ROOT,
        )

    lexical_root = Path(os.path.abspath(str(raw_root)))
    try:
        resolved_root = raw_root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise PathGuardError(
            f"allowed_root does not exist: {raw_root}",
            code=_ERR_ALLOWED_ROOT_NOT_FOUND,
        ) from exc
    except OSError as exc:
        raise PathGuardError(
            f"failed to resolve allowed_root: {raw_root}",
            code=_ERR_UNVERIFIABLE,
        ) from exc

    if not resolved_root.is_dir():
        raise PathGuardError(
            f"allowed_root is not a directory: {resolved_root}",
            code=_ERR_ALLOWED_ROOT_NOT_DIRECTORY,
        )

    requested_text, normalized_path = _normalize_candidate_path(
        requested_path,
        lexical_root,
    )

    # First pass: lexical containment catches obvious traversal.
    if not _is_within(normalized_path, lexical_root):
        raise PathGuardError(
            f"Path escapes allowed root: {requested_text!r}",
            code=_ERR_PATH_TRAVERSAL,
        )

    # Second pass: resolve deepest existing ancestor to catch symlink escapes.
    resolved_candidate = _resolve_deepest_existing(normalized_path)
    if not _is_within(resolved_candidate, resolved_root):
        raise PathGuardError(
            f"Path escapes allowed root via symlink resolution: {requested_text!r}",
            code=_ERR_SYMLINK_ESCAPE,
        )

    return ValidatedPath(
        requested_path=requested_text,
        normalized_path=normalized_path,
        resolved_parent_path=resolved_candidate.parent,
        allowed_root=resolved_root,
        scope_kind=scope_kind,
        scope_id=normalized_scope_id,
    )


__all__ = [
    "PathGuardError",
    "ScopeKind",
    "ValidatedPath",
    "validate_write_path",
]
