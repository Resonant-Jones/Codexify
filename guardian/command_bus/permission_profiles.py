"""Dispatch-time permission profile evaluation for command/tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from guardian.security.path_guard import PathGuardError, validate_write_path

CommandClass = Literal[
    "read",
    "write",
    "shell",
    "network",
    "connector",
    "memory",
    "document",
    "artifact",
    "admin",
]

FilesystemAccess = Literal["none", "read_only", "write_scoped"]


@dataclass(frozen=True)
class PermissionProfile:
    profile_id: str
    actor_id: str
    subject_id: str
    task_id: str
    project_id: str | None = None
    thread_id: str | None = None
    allowed_command_classes: tuple[CommandClass | str, ...] = ()
    denied_command_classes: tuple[CommandClass | str, ...] = ()
    allowed_command_ids: tuple[str, ...] = ()
    denied_command_ids: tuple[str, ...] = ()
    filesystem_access: FilesystemAccess = "none"
    allowed_write_roots: tuple[Path, ...] = ()
    shell_allowed: bool = False
    shell_read_only: bool = True
    allowed_shell_commands: tuple[str, ...] = ()
    network_allowed: bool = False
    connector_allowed: bool = False


@dataclass(frozen=True)
class PermissionProfileRequest:
    actor_id: str
    subject_id: str
    task_id: str
    command_id: str
    command_class: CommandClass | str
    project_id: str | None = None
    thread_id: str | None = None
    requested_write_paths: tuple[Path | str, ...] = ()
    uses_shell: bool = False
    shell_command: str | None = None
    shell_mutates: bool = False
    uses_network: bool = False
    uses_connector: bool = False


@dataclass(frozen=True)
class PermissionProfileDecision:
    allowed: bool
    code: str
    reason: str


def evaluate_permission_profile(
    profile: PermissionProfile | None,
    request: PermissionProfileRequest,
) -> PermissionProfileDecision:
    if profile is None:
        return _deny("missing_profile", "permission profile is required")

    actor_id = _required_value(request.actor_id)
    if actor_id is None:
        return _deny("missing_actor", "actor_id is required")

    subject_id = _required_value(request.subject_id)
    if subject_id is None:
        return _deny("missing_subject", "subject_id is required")

    task_id = _required_value(request.task_id)
    if task_id is None:
        return _deny("missing_task", "task_id is required")

    command_id = _required_value(request.command_id)
    if command_id is None:
        return _deny("missing_command_id", "command_id is required")

    command_class = _required_value(request.command_class)
    if command_class is None:
        return _deny("missing_command_class", "command_class is required")

    if actor_id != _required_value(profile.actor_id):
        return _deny("actor_mismatch", "request actor_id does not match profile")

    if subject_id != _required_value(profile.subject_id):
        return _deny(
            "subject_mismatch",
            "request subject_id does not match profile",
        )

    if task_id != _required_value(profile.task_id):
        return _deny("task_mismatch", "request task_id does not match profile")

    if profile.project_id is not None and request.project_id != profile.project_id:
        return _deny(
            "project_scope_mismatch",
            "request project_id is outside profile scope",
        )

    if profile.thread_id is not None and request.thread_id != profile.thread_id:
        return _deny(
            "thread_scope_mismatch",
            "request thread_id is outside profile scope",
        )

    denied_command_ids = {
        value.strip() for value in profile.denied_command_ids if value.strip()
    }
    if command_id in denied_command_ids:
        return _deny("command_id_denied", "command_id is denied by profile")

    denied_command_classes = {
        str(value).strip()
        for value in profile.denied_command_classes
        if str(value).strip()
    }
    if command_class in denied_command_classes:
        return _deny(
            "command_class_denied",
            "command_class is denied by profile",
        )

    allowed_command_ids = {
        value.strip() for value in profile.allowed_command_ids if value.strip()
    }
    if allowed_command_ids and command_id not in allowed_command_ids:
        return _deny(
            "command_id_not_allowed",
            "command_id is not in profile allow list",
        )

    allowed_command_classes = {
        str(value).strip()
        for value in profile.allowed_command_classes
        if str(value).strip()
    }
    if allowed_command_classes and command_class not in allowed_command_classes:
        return _deny(
            "command_class_not_allowed",
            "command_class is not in profile allow list",
        )

    if request.requested_write_paths:
        if profile.filesystem_access != "write_scoped":
            return _deny(
                "filesystem_denied",
                "filesystem write access is not write_scoped",
            )
        if not profile.allowed_write_roots:
            return _deny(
                "filesystem_denied",
                "allowed_write_roots is required for write requests",
            )
        for requested_path in request.requested_write_paths:
            if not _is_path_within_allowed_roots(profile, requested_path):
                return _deny(
                    "path_out_of_scope",
                    f"requested write path is outside scope: {requested_path}",
                )

    if request.uses_shell:
        if not profile.shell_allowed:
            return _deny("shell_denied", "shell access is not allowed")

        allowed_shell_commands = {
            value.strip()
            for value in profile.allowed_shell_commands
            if value.strip()
        }
        requested_shell_command = _required_value(request.shell_command)
        if (
            allowed_shell_commands
            and requested_shell_command not in allowed_shell_commands
        ):
            return _deny(
                "shell_command_not_allowed",
                "shell command is not in profile allow list",
            )

        if profile.shell_read_only and request.shell_mutates:
            return _deny(
                "shell_mutation_denied",
                "shell mutation is denied in read-only shell mode",
            )

    if request.uses_network and not profile.network_allowed:
        return _deny("network_denied", "network access is not allowed")

    if request.uses_connector and not profile.connector_allowed:
        return _deny("connector_denied", "connector access is not allowed")

    return PermissionProfileDecision(
        allowed=True,
        code="allowed",
        reason="request allowed by permission profile",
    )


def _required_value(value: object) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None


def _is_path_within_allowed_roots(
    profile: PermissionProfile, requested_path: Path | str
) -> bool:
    scope_kind, scope_id = _resolve_path_scope(profile)
    for allowed_root in profile.allowed_write_roots:
        try:
            validate_write_path(
                requested_path=requested_path,
                allowed_root=allowed_root,
                scope_kind=scope_kind,
                scope_id=scope_id,
            )
            return True
        except PathGuardError:
            continue
    return False


def _resolve_path_scope(
    profile: PermissionProfile,
) -> tuple[
    Literal[
        "thread",
        "project",
        "workspace",
        "memory",
        "artifact",
        "sandbox",
        "document",
    ],
    str,
]:
    if profile.thread_id:
        return ("thread", profile.thread_id)
    if profile.project_id:
        return ("project", profile.project_id)
    return ("sandbox", profile.task_id)


def _deny(code: str, reason: str) -> PermissionProfileDecision:
    return PermissionProfileDecision(allowed=False, code=code, reason=reason)


__all__ = [
    "CommandClass",
    "FilesystemAccess",
    "PermissionProfile",
    "PermissionProfileDecision",
    "PermissionProfileRequest",
    "evaluate_permission_profile",
]
