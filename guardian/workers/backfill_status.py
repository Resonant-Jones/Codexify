"""
Backfill status helpers.

Stores and exposes lightweight status snapshots for embedding and graph backfill workers.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from guardian.db.models import ChatMessage

try:
    import chromadb  # type: ignore
except Exception:
    chromadb = None  # type: ignore

try:
    from guardian.graph.connection import connect_neo4j
    from guardian.graph.models import MessageNode

    _NEO4J_AVAILABLE = True
except Exception:
    _NEO4J_AVAILABLE = False

logger = logging.getLogger(__name__)

_STATUS_DIR = Path(__file__).resolve().parents[1] / "logs"


def _ensure_status_dir() -> None:
    """Ensure the status directory exists for snapshot persistence."""
    _STATUS_DIR.mkdir(parents=True, exist_ok=True)


def _status_path(worker: str) -> Path:
    """Return the on-disk status file path for a worker."""
    _ensure_status_dir()
    return _STATUS_DIR / f"{worker}_backfill_status.json"


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


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


def read_status_snapshot(worker: str) -> dict[str, Any]:
    """Return the last status snapshot for a worker, if present."""
    path = _status_path(worker)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("[backfill-status] failed to read %s", path)
        return {}


def write_status_snapshot(worker: str, snapshot: dict[str, Any]) -> None:
    """Persist a status snapshot to disk."""
    path = _status_path(worker)
    payload = dict(snapshot)
    payload["updated_at"] = _utc_now()
    # Use a temp file + replace to avoid partial writes on interruption.
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def update_status_snapshot(
    worker: str, updates: dict[str, Any]
) -> dict[str, Any]:
    """Merge updates into the worker status snapshot and persist it."""
    snapshot = read_status_snapshot(worker)
    snapshot.update(updates)
    write_status_snapshot(worker, snapshot)
    return snapshot


def _open_db_session():
    """Open a short-lived SQLAlchemy session for status queries."""
    engine = create_engine(_resolve_database_url(), future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


def _count_total_messages() -> int | None:
    """Return the total number of chat messages in Postgres."""
    try:
        db = _open_db_session()
        try:
            return int(
                db.execute(select(func.count(ChatMessage.id))).scalar() or 0
            )
        finally:
            db.close()
    except Exception as exc:
        logger.warning("[backfill-status] failed to count messages: %s", exc)
        return None


def _count_chroma_embeddings() -> tuple[int | None, str]:
    """Return the embedding count from Chroma when available."""
    store = os.getenv("CODEXIFY_VECTOR_STORE", "faiss").strip().lower()
    if store != "chroma":
        return None, "vector_store_not_chroma"
    if chromadb is None:
        return None, "chromadb_unavailable"
    chroma_path = os.getenv("CODEXIFY_CHROMA_PATH", "./.chroma")
    collection = os.getenv("CODEXIFY_COLLECTION", "codexify_vault")
    try:
        client = chromadb.PersistentClient(path=chroma_path)
        coll = client.get_or_create_collection(name=collection)
        return int(coll.count()), "chroma_collection"
    except Exception as exc:
        logger.warning("[backfill-status] chroma count failed: %s", exc)
        return None, "chroma_error"


def _count_graph_messages() -> tuple[int | None, str]:
    """Return the message node count from Neo4j when available."""
    if not _NEO4J_AVAILABLE:
        return None, "neo4j_unavailable"
    try:
        connect_neo4j()
        return int(MessageNode.nodes.count()), "neo4j"
    except Exception as exc:
        logger.warning("[backfill-status] neo4j count failed: %s", exc)
        return None, "neo4j_error"


def get_embedding_backfill_status() -> dict[str, Any]:
    """Return a combined status snapshot + live counts for embedding backfill."""
    snapshot = read_status_snapshot("embedding")
    total_messages = _count_total_messages()
    embedded_count, source = _count_chroma_embeddings()
    if embedded_count is None:
        # Fall back to the last run's processed count when Chroma is unavailable.
        embedded_count = snapshot.get("items_processed")
        if embedded_count is not None:
            source = "last_run"
    remaining: int | None = None
    if total_messages is not None and embedded_count is not None:
        remaining = max(total_messages - int(embedded_count), 0)
    return {
        **snapshot,
        "worker": "embedding",
        "total_messages": total_messages,
        "messages_embedded": embedded_count,
        "messages_remaining": remaining,
        "counts_source": source,
    }


def get_graph_backfill_status() -> dict[str, Any]:
    """Return a combined status snapshot + live counts for graph backfill."""
    snapshot = read_status_snapshot("graph")
    total_messages = _count_total_messages()
    graph_count, source = _count_graph_messages()
    remaining: int | None = None
    if total_messages is not None and graph_count is not None:
        remaining = max(total_messages - int(graph_count), 0)
    return {
        **snapshot,
        "worker": "graph",
        "total_messages": total_messages,
        "messages_embedded": graph_count,
        "messages_remaining": remaining,
        "counts_source": source,
    }


def get_backfill_status() -> dict[str, Any]:
    """Return a combined status payload for all backfill workers."""
    return {
        "embedding": get_embedding_backfill_status(),
        "graph": get_graph_backfill_status(),
        "generated_at": _utc_now(),
    }
