"""
Embedding Backfill Worker

Purpose:
--------
Processes canonical chat messages that do not yet have vector embeddings.
“Pending” is defined strictly as: message exists, vector does not.

Design guarantees:
- Idempotent (safe to re-run)
- Side‑effect limited (does not mutate canonical content)
- Crash‑safe (partial progress is acceptable)
- Provider‑agnostic (local / cloud embedders)

Execution model:
- One‑shot batch worker
- May be run manually or at startup
- Exits cleanly when no work remains
"""

import logging
import os
import sys
import time
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.db.models import ChatMessage
from guardian.identity import get_user_id
from guardian.vector.store import VectorStore

logger = logging.getLogger("embedding_backfill")
logging.basicConfig(level=logging.INFO)

DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_BATCHES = None  # Unlimited by default
DEFAULT_SLEEP_SECONDS = 0
EMBED_SCHEMA_VERSION = 1  # explicit schema version for embeddings


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


def _get_env_int(name: str, default: int) -> int:
    """Parse an integer environment override with a safe fallback."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("[backfill] invalid %s=%r; using %s", name, raw, default)
        return default


def _get_env_optional_int(name: str, default: int | None) -> int | None:
    """Parse an optional integer environment override."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("[backfill] invalid %s=%r; using %s", name, raw, default)
        return default


def _get_env_float(name: str, default: float) -> float:
    """Parse a float environment override with a safe fallback."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("[backfill] invalid %s=%r; using %s", name, raw, default)
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    """Parse a boolean environment override with a safe fallback."""
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in ("1", "true", "yes", "y", "on"):
        return True
    if value in ("0", "false", "no", "n", "off"):
        return False
    logger.warning("[backfill] invalid %s=%r; using %s", name, raw, default)
    return default


def _message_already_embedded(
    vector_store: VectorStore, message: ChatMessage
) -> bool:
    """Best-effort check for prior embeddings using vector store metadata."""
    message_id = message.id
    message_id_str = str(message.id)
    embedder = getattr(vector_store, "embedder", None)
    if embedder is None:
        return False

    # Chroma persists metadata; query by message_id when available.
    collection = getattr(embedder, "_chroma_collection", None)
    if collection is not None:
        try:
            result = collection.get(where={"message_id": message_id})
        except Exception:
            return False
        if isinstance(result, dict):
            return bool(result.get("ids"))
        return False

    # FAISS is in-memory; dedupe within the current process if possible.
    metadatas = getattr(embedder, "_metadatas", None)
    if isinstance(metadatas, list):
        for meta in metadatas:
            if str(meta.get("message_id")) == message_id_str:
                return True
    return False


def fetch_unembedded_messages(
    db, vector_store: VectorStore, limit: int, last_seen_id: int
) -> tuple[List[ChatMessage], int]:
    """
    Fetch messages that do not yet have embeddings.
    """
    # Note: "unembedded" is defined externally by the vector store, not the canonical DB.
    if limit <= 0:
        return [], last_seen_id

    pending: List[ChatMessage] = []
    cursor = last_seen_id

    while len(pending) < limit:
        rows = (
            db.query(ChatMessage)
            .filter(ChatMessage.id > cursor)
            .order_by(ChatMessage.id.asc())
            .limit(limit)
            .all()
        )
        if not rows:
            break

        for msg in rows:
            cursor = msg.id
            if not _message_already_embedded(vector_store, msg):
                pending.append(msg)
                if len(pending) >= limit:
                    break

    return pending, cursor


def embed_and_persist(
    messages: List[ChatMessage],
    vector_store: VectorStore,
    dry_run: bool,
):
    """
    Embed messages and add texts into the vector store.
    """
    items = [
        {
            "text": m.content,
            "meta": {
                "message_id": m.id,
                "thread_id": m.thread_id,
                "role": m.role,
                "created_at": m.created_at.isoformat(),
                "source": "canonical",
                "embed_schema_version": EMBED_SCHEMA_VERSION,
            },
        }
        for m in messages
    ]

    if dry_run:
        logger.info(
            f"[backfill][dry-run] Would add {len(messages)} embeddings to vector store"
        )
    else:
        vector_store.add_texts(items)


def run_once():
    user_id = get_user_id()

    batch_size = _get_env_int("EMBED_BATCH_SIZE", DEFAULT_BATCH_SIZE)
    max_batches = _get_env_optional_int(
        "EMBED_MAX_BATCHES", DEFAULT_MAX_BATCHES
    )
    sleep_seconds = _get_env_float("EMBED_SLEEP_SECONDS", DEFAULT_SLEEP_SECONDS)
    dry_run = _get_env_bool("EMBED_DRY_RUN", False)

    logger.info("[backfill] starting embedding backfill worker")
    logger.info(f"[backfill] user_id={user_id}")
    # Log embedding backend details in a provider-agnostic, future-proof way
    vector_backend = os.getenv("CODEXIFY_VECTOR_STORE", "faiss").lower()
    embed_model = os.getenv("EMBED_MODEL", "unknown")
    logger.info(f"[backfill] vector_backend={vector_backend}")
    logger.info(f"[backfill] embed_model={embed_model}")
    logger.info(f"[backfill] batch_size={batch_size}")
    logger.info(
        f"[backfill] max_batches={max_batches if max_batches is not None else 'unlimited'}"
    )
    logger.info(f"[backfill] sleep_seconds={sleep_seconds}")
    logger.info(f"[backfill] dry_run={dry_run}")

    database_url = _resolve_database_url()
    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = SessionLocal()

    vector_store = VectorStore()

    total_embedded = 0
    batch_count = 0
    cursor_id = 0

    while True:
        if max_batches is not None and batch_count >= max_batches:
            logger.info(
                f"[backfill] reached max_batches={max_batches}, stopping"
            )
            break

        pending, cursor_id = fetch_unembedded_messages(
            db, vector_store, batch_size, cursor_id
        )
        if not pending:
            logger.info("[backfill] no more pending messages to embed, exiting")
            break

        batch_count += 1
        logger.info(
            f"[backfill] embedding batch {batch_count} size={len(pending)}"
        )

        try:
            embed_and_persist(pending, vector_store, dry_run)
            # Embedding state is tracked by the vector store, not the canonical message table.
            total_embedded += len(pending)
            logger.info(
                f"[backfill] batch {batch_count} complete, total embedded so far: {total_embedded}"
            )
        except Exception:
            logger.exception("[backfill] batch failed — exiting safely")
            break

        if sleep_seconds > 0:
            logger.info(
                f"[backfill] sleeping for {sleep_seconds} seconds before next batch"
            )
            time.sleep(sleep_seconds)

    db.close()
    logger.info(
        f"[backfill] complete — embedded {total_embedded} messages (dry_run={dry_run})"
    )
    # Note: No DB mutations are performed if dry_run; safe commit boundary.


if __name__ == "__main__":
    try:
        run_once()
    except KeyboardInterrupt:
        logger.info("[backfill] interrupted by user")
        sys.exit(0)
