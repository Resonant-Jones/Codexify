"""Default project normalization helpers.

This module centralizes the canonical default project identity used by
frontend and backend flows. Legacy naming ("Loose Threads") is treated as an
alias and normalized to the canonical "General" project for user-visible APIs.
Anything without an explicit project should resolve to that canonical project.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, MutableMapping, Sequence

from guardian.core.project_lifecycle import PROJECT_SYSTEM_ROLE_GENERAL

DEFAULT_PROJECT_NAME = "General"
DEFAULT_PROJECT_DESCRIPTION = (
    "Default project for content without a specified project"
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


def resolve_project_id_or_default(
    chatlog_db: Any,
    project_id: Any,
    logger: logging.Logger | None = None,
) -> int | None:
    """Return a positive project id, falling back to the canonical General project."""
    try:
        parsed = int(project_id)
    except (TypeError, ValueError):
        parsed = None

    if parsed is not None and parsed > 0:
        return parsed

    return canonicalize_default_project(chatlog_db, logger=logger)


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
    role_ids = [
        pid
        for project in projects
        if str(project.get("system_role") or "").strip().lower()
        == PROJECT_SYSTEM_ROLE_GENERAL
        if (pid := _coerce_project_id(project)) is not None
    ]
    if role_ids:
        return min(role_ids)

    canonical_name = normalize_project_name(DEFAULT_PROJECT_NAME)
    canonical_id: int | None = None
    fallback_id: int | None = None
    for project in projects:
        pid = _coerce_project_id(project)
        if pid is None:
            continue
        if project.get("system_role") is not None:
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
    canonical_project = next(
        (
            project
            for project in projects
            if _coerce_project_id(project) == canonical_id
        ),
        None,
    )

    if canonical_id is None:
        try:
            ensured_id = chatlog_db.ensure_project(
                DEFAULT_PROJECT_NAME, DEFAULT_PROJECT_DESCRIPTION
            )
            canonical_id = int(ensured_id)
        except Exception as exc:
            log.warning("[projects] failed to ensure default project: %s", exc)
            return None

    if not canonical_project or str(
        canonical_project.get("system_role") or ""
    ).strip().lower() != PROJECT_SYSTEM_ROLE_GENERAL:
        try:
            chatlog_db.set_project_system_role(
                canonical_id, PROJECT_SYSTEM_ROLE_GENERAL
            )
        except Exception as exc:
            # Compatibility adapters may not expose lifecycle assignment yet.
            log.warning(
                "[projects] failed to assign General system role: %s", exc
            )

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
        role = str(project.get("system_role") or "").strip().lower()
        is_role_default = role == PROJECT_SYSTEM_ROLE_GENERAL
        is_legacy_default = role == "" and is_default_project_name(name)
        is_default = is_role_default or is_legacy_default
        if is_default and canonical_id is not None and pid != canonical_id:
            continue
        normalized: MutableMapping[str, Any] = dict(project)
        if is_legacy_default:
            normalized["name"] = DEFAULT_PROJECT_NAME
            if not normalized.get("description"):
                normalized["description"] = DEFAULT_PROJECT_DESCRIPTION
        if pid is not None:
            seen_ids.add(pid)
        out.append(dict(normalized))
    return out
