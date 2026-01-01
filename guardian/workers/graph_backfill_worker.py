"""
Graph Backfill Worker

Purpose:
Populate Neo4j with *structural* graph data derived from canonical Postgres rows.
This worker intentionally avoids semantic inference. It encodes only topology.

Idempotent by design.
Safe to re-run.
"""

import logging
import os
from typing import Iterable

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.db import models
from guardian.graph.connection import connect_neo4j
from guardian.graph.models import MessageNode, ThreadNode, UserNode

logger = logging.getLogger(__name__)


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


def backfill_graph(batch_size: int = 500) -> None:
    engine = create_engine(_resolve_database_url(), future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()

    logger.info("[GraphBackfill] starting structural graph backfill")

    try:
        connect_neo4j()

        threads = _iter_threads(db)

        for thread in threads:
            user_node = UserNode.get_or_create({"user_id": thread.user_id})[0]
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

        logger.info("[GraphBackfill] completed successfully")

    except Exception:
        logger.exception("[GraphBackfill] failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    backfill_graph()
