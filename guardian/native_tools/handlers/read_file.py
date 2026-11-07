"""In-process handler for the native ``native::fs::read_file`` command.

The handler resolves its own authority. It never accepts a filesystem root from
the caller: the Project scope is taken from the invoke's server-side scope
argument, and the root is re-derived by resolving that Project's repository
binding **for the authenticated account**. A caller that forges a scope it
does not own therefore fails closed at the binding resolver rather than
reading a foreign tree.

Everything else the handler needs is bounded here, because a tool result is
injected into the model's context whole.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from guardian.command_bus.contracts import InvokeArguments
from guardian.core.repository_containment import (
    is_sensitive_path,
    resolve_contained_regular_file,
)
from guardian.core.repository_session import read_only_session_factory

__all__ = [
    "MAX_FILE_BYTES",
    "MAX_FILE_LINES",
    "NativeToolError",
    "execute_read_file",
]

#: Maximum bytes read from one file in a single call.
MAX_FILE_BYTES = 131_072

#: Maximum lines returned in a single call.
MAX_FILE_LINES = 1_000

_DEFAULT_START_LINE = 1

_BINARY_SNIFF_BYTES = 4_096


class NativeToolError(ValueError):
    """Raised when a native tool request cannot be satisfied safely.

    The message is written for a model and never carries filesystem paths,
    database detail, or the resolved root.
    """


def execute_read_file(
    *,
    arguments: InvokeArguments,
    auth_subject: str | None,
) -> dict[str, Any]:
    """Read one project file as bounded, line-numbered text."""

    body = _body(arguments)
    relative_path = _required_text(body.get("path"), "path")
    start_line = _optional_positive_int(body.get("start_line"), "start_line")
    limit = _optional_positive_int(body.get("limit"), "limit")
    project_id = _scope_project_id(body.get("scope"))

    root = _resolve_canonical_root(
        auth_subject=auth_subject,
        project_id=project_id,
    )

    if is_sensitive_path(relative_path):
        raise NativeToolError("the requested path names a sensitive file")
    resolved, rejected_symlink = resolve_contained_regular_file(root, relative_path)
    if rejected_symlink:
        raise NativeToolError("the requested path is a symlink and was refused")
    if resolved is None:
        raise NativeToolError(
            "the requested path is not a readable file inside the authorized project"
        )

    return _read_bounded(
        resolved,
        relative_path=relative_path,
        start_line=start_line or _DEFAULT_START_LINE,
        limit=limit or MAX_FILE_LINES,
    )


def _read_bounded(
    resolved: Path,
    *,
    relative_path: str,
    start_line: int,
    limit: int,
) -> dict[str, Any]:
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise NativeToolError("the requested file could not be inspected") from exc
    if size > MAX_FILE_BYTES:
        raise NativeToolError(
            f"the requested file is larger than the {MAX_FILE_BYTES}-byte read limit"
        )

    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise NativeToolError("the requested file could not be read") from exc

    if "\x00" in text[:_BINARY_SNIFF_BYTES]:
        raise NativeToolError("the requested file is not text")

    lines = text.splitlines()
    total_lines = len(lines)
    first_index = max(start_line - 1, 0)
    selected = lines[first_index : first_index + limit]
    rendered = "".join(
        f"{first_index + offset + 1}\t{line}\n" for offset, line in enumerate(selected)
    )
    remaining = max(total_lines - first_index - len(selected), 0)
    return {
        "path": relative_path,
        "content": rendered,
        "start_line": first_index + 1,
        "end_line": first_index + len(selected),
        "total_lines": total_lines,
        "returned_lines": len(selected),
        "truncated": remaining > 0,
    }


def _resolve_canonical_root(
    *,
    auth_subject: str | None,
    project_id: int,
) -> Path:
    """Resolve the authorized repository root for one account and Project."""

    account_id = str(auth_subject or "").strip()
    if not account_id:
        raise NativeToolError("an authenticated account is required")

    chatlog_db = _chatlog_db()
    if chatlog_db is None:
        raise NativeToolError("no repository authority store is available")
    get_session = read_only_session_factory(chatlog_db)
    if not callable(get_session):
        raise NativeToolError("no repository authority session is available")

    from guardian.core.repository_authority import (
        resolve_project_repository_binding,
    )

    try:
        with get_session() as session:
            binding = resolve_project_repository_binding(
                session,
                authenticated_account_id=account_id,
                project_id=project_id,
            )
    except Exception as exc:
        raise NativeToolError(
            "the project could not be resolved for the authenticated account"
        ) from exc
    return binding.canonical_root


def _chatlog_db() -> Any:
    """Return the application's read authority store, if one is configured."""

    from guardian.core import dependencies

    return getattr(dependencies, "chatlog_db", None)


def _body(arguments: InvokeArguments) -> Mapping[str, Any]:
    body = getattr(arguments, "body", None)
    if body is None:
        return {}
    if isinstance(body, Mapping):
        return body
    raise NativeToolError("the request body must be an object")


def _required_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise NativeToolError(f"{field_name} is required")
    return text


def _optional_positive_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise NativeToolError(f"{field_name} must be an integer")
    if value < 1:
        raise NativeToolError(f"{field_name} must be positive")
    return value


def _scope_project_id(scope: Any) -> int:
    if not isinstance(scope, Mapping):
        raise NativeToolError("the request carries no authorized project scope")
    project_id = scope.get("project_id")
    if isinstance(project_id, bool) or not isinstance(project_id, int):
        raise NativeToolError("the request carries no authorized project scope")
    if project_id <= 0:
        raise NativeToolError("the request carries no authorized project scope")
    return project_id
