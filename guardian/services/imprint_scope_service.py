"""
Imprint scope helpers.

These helpers enforce explicit current-user scope resolution for control-plane
write paths and isolate the read-only `default` compatibility fallback.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

import guardian.core.dependencies as core_dependencies
from guardian.cognition.imprints import store as imprint_store

DEFAULT_COMPATIBILITY_USER_ID = "default"


def _normalize_user_id(user_id: str) -> str:
    resolved = str(user_id or "").strip()
    if not resolved:
        raise HTTPException(
            status_code=403, detail="current user could not be resolved"
        )
    return resolved


def _normalize_int(value: Any, field_name: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail=f"{field_name} must be an integer"
        ) from exc


def _thread_value(thread: Any, field_name: str, default: Any = None) -> Any:
    if thread is None:
        return default
    if isinstance(thread, dict):
        return thread.get(field_name, default)
    return getattr(thread, field_name, default)


def _assert_mutation_user_id(user_id: str) -> str:
    resolved = _normalize_user_id(user_id)
    if resolved == DEFAULT_COMPATIBILITY_USER_ID:
        raise HTTPException(
            status_code=403,
            detail="default is read-only compatibility fallback",
        )
    return resolved


def resolve_user_project_scope(
    current_user: str,
    thread_id: int | None = None,
    project_id: int | None = None,
    *,
    chatlog_backend: Any | None = None,
    mutation: bool = False,
) -> tuple[str, int | None, dict[str, Any] | None]:
    """
    Resolve current-user scope and enforce ownership on thread-backed writes.
    """
    resolved_user = (
        _assert_mutation_user_id(current_user)
        if mutation
        else _normalize_user_id(current_user)
    )
    resolved_project = _normalize_int(project_id, "project_id")
    thread: dict[str, Any] | None = None

    if thread_id is None:
        return resolved_user, resolved_project, None

    thread_pk = _normalize_int(thread_id, "thread_id")
    if thread_pk is None:
        raise HTTPException(status_code=400, detail="thread_id is required")

    backend = chatlog_backend or core_dependencies.chatlog_db
    if backend is None or not hasattr(backend, "get_chat_thread"):
        raise HTTPException(
            status_code=403,
            detail="thread scope cannot be established",
        )

    try:
        thread = backend.get_chat_thread(thread_pk)
    except Exception as exc:
        raise HTTPException(
            status_code=403,
            detail="thread scope cannot be established",
        ) from exc

    if not thread:
        raise HTTPException(status_code=404, detail="thread not found")

    thread_user_id = str(_thread_value(thread, "user_id") or "").strip()
    if not thread_user_id:
        raise HTTPException(
            status_code=403,
            detail="thread ownership cannot be established",
        )
    if thread_user_id != resolved_user:
        raise HTTPException(
            status_code=403,
            detail="thread does not belong to the current user",
        )

    thread_project_id = _normalize_int(
        _thread_value(thread, "project_id"), "project_id"
    )
    if resolved_project is None:
        resolved_project = thread_project_id
    elif (
        thread_project_id is not None and thread_project_id != resolved_project
    ):
        raise HTTPException(status_code=403, detail="project scope mismatch")

    return resolved_user, resolved_project, thread


def resolve_owned_imprint_for_mutation(
    current_user: str,
    imprint_id: int,
) -> Any:
    """
    Resolve an imprint for mutation and enforce ownership.
    """
    resolved_user = _assert_mutation_user_id(current_user)
    imprint_pk = _normalize_int(imprint_id, "imprint_id")
    if imprint_pk is None:
        raise HTTPException(status_code=400, detail="imprint_id is required")

    imprint = imprint_store.get_imprint_by_id(imprint_pk)
    if not imprint:
        raise HTTPException(status_code=404, detail="imprint not found")
    if str(imprint.user_id).strip() != resolved_user:
        raise HTTPException(
            status_code=403,
            detail="imprint does not belong to the current user",
        )
    return imprint


def read_user_candidates(current_user: str) -> tuple[str, ...]:
    """
    Return compatibility read candidates for scoped reads.

    `default` is only ever exposed here as a read-only fallback.
    """
    resolved_user = _normalize_user_id(current_user)
    if resolved_user == DEFAULT_COMPATIBILITY_USER_ID:
        return (resolved_user,)
    return (resolved_user, DEFAULT_COMPATIBILITY_USER_ID)


__all__ = [
    "DEFAULT_COMPATIBILITY_USER_ID",
    "read_user_candidates",
    "resolve_owned_imprint_for_mutation",
    "resolve_user_project_scope",
]
