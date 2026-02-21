"""Default project normalization helpers.

This module centralizes the canonical default project identity used by
frontend and backend flows. Legacy naming ("Loose Threads") is treated as an
alias and normalized to the canonical "General" project for user-visible APIs.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, MutableMapping, Sequence

DEFAULT_PROJECT_NAME = "General"
DEFAULT_PROJECT_DESCRIPTION = (
    "Default bucket for unassigned threads and documents"
)
LEGACY_DEFAULT_PROJECT_ALIASES: tuple[str, ...] = ("Loose Threads",)


def normalize_project_name(name: str | None) -> str:
    return " ".join(str(name or "").strip().lower().split())


def _default_name_aliases() -> set[str]:
    names = {DEFAULT_PROJECT_NAME, *LEGACY_DEFAULT_PROJECT_ALIASES}
    return {normalize_project_name(name) for name in names}


def is_default_project_name(name: str | None) -> bool:
    normalized = normalize_project_name(name)
    return bool(normalized) and normalized in _default_name_aliases()


def _coerce_project_id(project: Mapping[str, Any]) -> int | None:
    raw = project.get("id")
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _pick_canonical_default_id(
    projects: Sequence[Mapping[str, Any]]
) -> int | None:
    canonical_name = normalize_project_name(DEFAULT_PROJECT_NAME)
    canonical_id: int | None = None
    fallback_id: int | None = None
    for project in projects:
        pid = _coerce_project_id(project)
        if pid is None:
            continue
        if not is_default_project_name(str(project.get("name") or "")):
            continue
        if (
            normalize_project_name(str(project.get("name") or ""))
            == canonical_name
        ):
            if canonical_id is None or pid < canonical_id:
                canonical_id = pid
            continue
        if fallback_id is None or pid < fallback_id:
            fallback_id = pid
    return canonical_id if canonical_id is not None else fallback_id


def canonicalize_default_project(
    chatlog_db: Any, logger: logging.Logger | None = None
) -> int | None:
    """Ensure a canonical default project exists and return its ID."""
    log = logger or logging.getLogger(__name__)
    if chatlog_db is None:
        return None

    try:
        projects = chatlog_db.list_projects() or []
    except Exception as exc:
        log.warning(
            "[projects] failed to list projects during default resolution: %s",
            exc,
        )
        projects = []

    canonical_id = _pick_canonical_default_id(projects)

    if canonical_id is None:
        try:
            ensured_id = chatlog_db.ensure_project(
                DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_DESCRIPTION
            )
            canonical_id = int(ensured_id)
        except Exception as exc:
            log.warning("[projects] failed to ensure default project: %s", exc)
            return None

    # Best effort: rename canonical alias rows to "General" for a stable display label.
    for project in projects:
        pid = _coerce_project_id(project)
        if pid is None or pid != canonical_id:
            continue
        existing_name = str(project.get("name") or "")
        if normalize_project_name(existing_name) == normalize_project_name(
            DEFAULT_PROJECT_NAME
        ):
            break
        try:
            chatlog_db.update_project(
                canonical_id,
                name=DEFAULT_PROJECT_NAME,
                description=(
                    project.get("description") or DEFAULT_PROJECT_DESCRIPTION
                ),
            )
        except Exception:
            # Ignore races or uniqueness collisions; canonical_id is still usable.
            pass
        break

    return canonical_id


def normalize_projects_for_listing(
    projects: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Return projects with default aliases deduplicated to a single 'General' row."""
    if not projects:
        return []

    canonical_id = _pick_canonical_default_id(projects)
    out: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for project in projects:
        pid = _coerce_project_id(project)
        if pid is not None and pid in seen_ids:
            continue
        name = str(project.get("name") or "")
        is_default = is_default_project_name(name)
        if is_default and canonical_id is not None and pid != canonical_id:
            continue
        normalized: MutableMapping[str, Any] = dict(project)
        if is_default:
            normalized["name"] = DEFAULT_PROJECT_NAME
            if not normalized.get("description"):
                normalized["description"] = DEFAULT_PROJECT_DESCRIPTION
        if pid is not None:
            seen_ids.add(pid)
        out.append(dict(normalized))
    return out
