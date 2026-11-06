"""Shared read-path containment authority for repository-scoped file access.

This module owns the *reuse* of the containment rules that
``guardian/core/repository_search.py`` already applied when it searched a
Project's repository. The rules are extracted here, unchanged in behaviour, so
that a native command-bus tool can resolve a contained file without importing
the search engine (and with it, its Git subprocess surface) and without
creating a second, parallel containment authority.

Rules:

* a relative path is joined onto the authorized root and must resolve *inside*
  that root;
* a symlink at the candidate path is refused outright rather than followed;
* the resolved target must be a regular file;
* well-known sensitive filenames (``.env``, key material) are refused by name.

Every caller supplies the root. Resolving that root from a Project and an
authenticated account is :mod:`guardian.core.repository_authority`'s job, not
this module's.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

__all__ = [
    "MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS",
    "is_sensitive_path",
    "resolve_contained_regular_file",
]

#: Maximum length of a repository-relative path accepted by containment checks.
MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS = 512

_SENSITIVE_BASENAMES = frozenset(
    {
        ".env",
        ".netrc",
        ".npmrc",
        ".pypirc",
        ".git-credentials",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
    }
)

_SENSITIVE_SUFFIXES = (
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".jks",
    ".keystore",
)


def is_sensitive_path(relative_path: str) -> bool:
    """Return whether a repository-relative path names a sensitive file."""

    basename = PurePosixPath(relative_path).name.casefold()
    return (
        basename in _SENSITIVE_BASENAMES
        or basename.startswith(".env.")
        or basename.endswith(_SENSITIVE_SUFFIXES)
    )


def resolve_contained_regular_file(
    root: Path, relative_path: str
) -> tuple[Path | None, bool]:
    """Return a contained regular file and whether a symlink was rejected.

    ``(None, True)`` means the candidate was a symlink and was refused without
    being followed. ``(None, False)`` means the candidate was missing, escaped
    the root, or was not a regular file.
    """

    normalized = str(relative_path or "").strip()
    if not normalized or len(normalized) > MAX_REPOSITORY_RELATIVE_PATH_CHARACTERS:
        return None, False
    if PurePosixPath(normalized).is_absolute():
        return None, False

    candidate = root.joinpath(*PurePosixPath(normalized).parts)
    try:
        if candidate.is_symlink():
            return None, True
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None, False
    if not resolved.is_file():
        return None, False
    return resolved, False
