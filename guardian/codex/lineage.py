from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from guardian.core.dependencies import get_database_dsn

_SessionFactory: sessionmaker | None = None


@dataclass(frozen=True)
class CodexLineageRef:
    source_thread_id: int
    source_message_id: int | None


def _get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory

    dsn = get_database_dsn()
    if not dsn:
        raise RuntimeError(
            "Database DSN not configured; cannot validate codex lineage."
        )
    engine = create_engine(dsn, future=True)
    _SessionFactory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return _SessionFactory


def _set_session_factory(factory: sessionmaker) -> None:
    global _SessionFactory
    _SessionFactory = factory


def reset_session_factory() -> None:
    global _SessionFactory
    _SessionFactory = None


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_lineage(front_matter: dict[str, Any] | None) -> CodexLineageRef:
    fm = front_matter or {}
    if "source_thread_id" in fm:
        source_thread_id = _coerce_int(fm.get("source_thread_id"))
    else:
        source_thread_id = _coerce_int(fm.get("thread_id"))

    if source_thread_id is None:
        raise ValueError("source_thread_id is required for codex entries.")

    if "source_message_id" in fm:
        raw_source_message_id = fm.get("source_message_id")
    elif "message_id" in fm:
        raw_source_message_id = fm.get("message_id")
    else:
        raw_source_message_id = None
    source_message_id = _coerce_int(raw_source_message_id)
    if raw_source_message_id is not None and source_message_id is None:
        raise ValueError("source_message_id must be an integer or null.")
    return CodexLineageRef(
        source_thread_id=source_thread_id,
        source_message_id=source_message_id,
    )


def ensure_lineage_exists(lineage: CodexLineageRef) -> None:
    Session = _get_session_factory()
    with Session() as session:
        thread_row = session.execute(
            text("SELECT id FROM chat_threads WHERE id = :thread_id LIMIT 1"),
            {"thread_id": lineage.source_thread_id},
        ).first()
        if thread_row is None:
            raise LookupError(
                f"source_thread_id {lineage.source_thread_id} was not found."
            )

        if lineage.source_message_id is None:
            return

        message_row = session.execute(
            text(
                """
                SELECT id
                FROM chat_messages
                WHERE id = :message_id AND thread_id = :thread_id
                LIMIT 1
                """
            ),
            {
                "message_id": lineage.source_message_id,
                "thread_id": lineage.source_thread_id,
            },
        ).first()
        if message_row is None:
            raise LookupError(
                "source_message_id {message_id} was not found in thread {thread_id}.".format(
                    message_id=lineage.source_message_id,
                    thread_id=lineage.source_thread_id,
                )
            )


def normalize_front_matter(
    front_matter: dict[str, Any] | None,
) -> tuple[dict[str, Any], CodexLineageRef]:
    lineage = parse_lineage(front_matter)
    ensure_lineage_exists(lineage)

    normalized = dict(front_matter or {})
    normalized["source_thread_id"] = lineage.source_thread_id
    normalized["source_message_id"] = lineage.source_message_id
    normalized.setdefault("thread_id", lineage.source_thread_id)
    normalized.setdefault("message_id", lineage.source_message_id)
    return normalized, lineage


__all__ = [
    "CodexLineageRef",
    "parse_lineage",
    "ensure_lineage_exists",
    "normalize_front_matter",
    "_set_session_factory",
    "reset_session_factory",
]
