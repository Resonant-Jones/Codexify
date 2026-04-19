"""Pure helpers for building derived graph-write candidates."""

from __future__ import annotations

from typing import Any, Dict


def build_graph_write_candidate(
    assistant_message: dict[str, Any],
    thread: dict[str, Any],
    project: dict[str, Any],
) -> dict[str, Any]:
    """Build a graph-write candidate from an assistant message.

    This function is intentionally pure. It does not write to any store,
    infer relationships, or mutate the input records.
    """

    account_id = thread.get("user_id")
    if account_id is None:
        account_id = thread.get("account_id")

    thread_id = thread["id"]
    project_id = project["id"]
    source_id = assistant_message["id"]

    return {
        "idempotency_key": f"graph:{source_id}",
        "source_id": source_id,
        "account_id": account_id,
        "thread_id": thread_id,
        "project_id": project_id,
        "identity_scope": {
            "account_id": account_id,
            "thread_id": thread_id,
            "project_id": project_id,
            "source_id": source_id,
        },
        "content": assistant_message["content"],
        "metadata": {
            "role": assistant_message.get("role"),
            "created_at": assistant_message.get("created_at"),
        },
    }
