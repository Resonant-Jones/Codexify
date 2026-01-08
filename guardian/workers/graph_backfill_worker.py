"""
Graph Backfill Worker

Purpose:
Populate Neo4j with *structural* graph data derived from canonical Postgres rows.
This worker intentionally avoids semantic inference. It encodes only topology.

Idempotent by design.
Safe to re-run.
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.db import models
from guardian.graph.connection import connect_neo4j
from guardian.graph.models import MessageNode, ThreadNode, UserNode
from guardian.workers.backfill_status import update_status_snapshot

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
_LOCK_PATH = (
    Path(__file__).resolve().parents[1] / "logs" / "graph_backfill.lock"
)


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def _log_event(event: str, **fields: object) -> None:
    """Emit a structured backfill log event."""
    payload = {"event": event, "timestamp": _utc_now(), **fields}
    logger.info("[graph-backfill] %s", json.dumps(payload, sort_keys=True))


def _acquire_lock(path: Path) -> bool:
    """Best-effort lock to prevent overlapping backfill runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release_lock(path: Path) -> None:
    """Release the backfill lock if owned by this process."""
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _resolve_database_url() -> str:
    """Return the configured database URL for offline workers."""
    candidates = (
        os.getenv("GUARDIAN_DATABASE_URL"),
        os.getenv("DATABASE_URL"),
        os.getenv("GUARDIAN_DB_URL"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    raise RuntimeError(
        "Database DSN not configured. Set GUARDIAN_DATABASE_URL or DATABASE_URL."
    )


def _iter_threads(db) -> Iterable[models.ChatThread]:
    return db.query(models.ChatThread).all()


def backfill_graph(batch_size: int = 500) -> int:
    if not _acquire_lock(_LOCK_PATH):
        update_status_snapshot(
            "graph",
            {
                "last_run_at": _utc_now(),
                "last_exit_reason": "locked",
                "error": "graph_backfill_locked",
            },
        )
        logger.info("[GraphBackfill] another graph worker is active; exiting")
        return 0

    logger.info("[GraphBackfill] starting structural graph backfill")

    exit_reason = "completed"
    error_message = None
    run_started_at = _utc_now()
    total_messages = None
    pending_total = None
    processed_total = 0

    db = None
    try:
        engine = create_engine(_resolve_database_url(), future=True)
        SessionLocal = sessionmaker(
            bind=engine, autoflush=False, autocommit=False
        )
        db = SessionLocal()

        connect_neo4j()

        total_messages = int(db.query(models.ChatMessage).count())
        try:
            # Prefer a quick graph count when Neo4j is available.
            graph_count = int(MessageNode.nodes.count())
            pending_total = max(total_messages - graph_count, 0)
            pending_source = "neo4j_count"
        except Exception:
            pending_total = total_messages
            pending_source = "db_total"

        update_status_snapshot(
            "graph",
            {
                "last_run_at": run_started_at,
                "last_exit_reason": None,
                "items_pending": pending_total,
                "items_processed": 0,
                "items_remaining": pending_total,
                "total_messages": total_messages,
                "items_pending_source": pending_source,
            },
        )
        _log_event(
            "items_pending",
            items_pending=pending_total,
            total_messages=total_messages,
            items_pending_source=pending_source,
        )

        if pending_total == 0:
            logger.info("[GraphBackfill] no pending graph work; exiting")
            exit_reason = "no_work"
        else:
            threads = _iter_threads(db)

            for thread in threads:
                user_node = UserNode.get_or_create({"user_id": thread.user_id})[
                    0
                ]
                thread_node = ThreadNode.get_or_create(
                    {"thread_id": str(thread.id)}
                )[0]

                messages = (
                    db.query(models.ChatMessage)
                    .filter(models.ChatMessage.thread_id == thread.id)
                    .order_by(models.ChatMessage.created_at.asc())
                    .all()
                )

                for msg in messages:
                    raw_msg_node = MessageNode.get_or_create(
                        {
                            "message_id": str(msg.id),
                            "content": msg.content,
                            "created_at": msg.created_at,
                        }
                    )
                    msg_node = (
                        raw_msg_node[0]
                        if isinstance(raw_msg_node, list)
                        else raw_msg_node
                    )
                    if not isinstance(msg_node, MessageNode):
                        raise TypeError(
                            f"Expected MessageNode, got {type(msg_node)}"
                        )
                    if not msg_node.user.is_connected(user_node):
                        msg_node.user.connect(user_node)
                    if not msg_node.thread.is_connected(thread_node):
                        msg_node.thread.connect(thread_node)
                    processed_total += 1

                # Update status after each thread so progress is visible in logs.
                remaining = (
                    max(pending_total - processed_total, 0)
                    if pending_total is not None
                    else None
                )
                update_status_snapshot(
                    "graph",
                    {
                        "items_processed": processed_total,
                        "items_remaining": remaining,
                    },
                )
                _log_event(
                    "items_processed",
                    items_processed=processed_total,
                    items_remaining=remaining,
                )

            logger.info("[GraphBackfill] completed successfully")

    except KeyboardInterrupt:
        logger.info("[GraphBackfill] interrupted by user")
        exit_reason = "interrupted"
    except Exception as exc:
        logger.exception("[GraphBackfill] failed")
        exit_reason = "error"
        error_message = str(exc)
    finally:
        if db is not None:
            db.close()
        _release_lock(_LOCK_PATH)

    remaining = (
        max(pending_total - processed_total, 0)
        if pending_total is not None
        else None
    )
    final_update = {
        "last_exit_reason": exit_reason,
        "items_processed": processed_total,
        "error": error_message,
    }
    if remaining is not None:
        final_update["items_remaining"] = remaining
    update_status_snapshot("graph", final_update)
    _log_event("exit_reason", exit_reason=exit_reason)

    if exit_reason == "error":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(backfill_graph())
