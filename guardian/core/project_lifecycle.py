"""Authoritative lifecycle rules for durable Project containers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


PROJECT_SYSTEM_ROLE_GENERAL = "general"
PROJECT_SYSTEM_ROLE_IMPORTS = "imports"
PROJECT_SYSTEM_ROLES = frozenset(
    {PROJECT_SYSTEM_ROLE_GENERAL, PROJECT_SYSTEM_ROLE_IMPORTS}
)

PROJECT_MUST_BE_ARCHIVED_BEFORE_DELETE = (
    "project_must_be_archived_before_delete"
)
PROJECT_SYSTEM_CONTAINER_IMMUTABLE = "project_system_container_immutable"


class ProjectLifecycleError(ValueError):
    """Stable lifecycle rejection surfaced by core and HTTP layers."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def project_value(project: Any, field: str) -> Any:
    if isinstance(project, Mapping):
        return project.get(field)
    return getattr(project, field, None)


def normalize_project_system_role(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in PROJECT_SYSTEM_ROLES else None


def project_system_role(project: Any) -> str | None:
    return normalize_project_system_role(project_value(project, "system_role"))


def project_archived_at(project: Any) -> datetime | str | None:
    return project_value(project, "archived_at")


def require_mutable_project_container(project: Any) -> None:
    """Reject archive/restore/delete attempts against built-in containers."""
    if project_system_role(project) is not None:
        raise ProjectLifecycleError(
            PROJECT_SYSTEM_CONTAINER_IMMUTABLE,
            "Built-in Project containers cannot be archived or deleted.",
        )


def require_project_deletable(project: Any) -> None:
    """Require an ordinary Project to be archived before permanent deletion."""
    require_mutable_project_container(project)
    if project_archived_at(project) is None:
        raise ProjectLifecycleError(
            PROJECT_MUST_BE_ARCHIVED_BEFORE_DELETE,
            "Project must be archived before it can be deleted.",
        )
