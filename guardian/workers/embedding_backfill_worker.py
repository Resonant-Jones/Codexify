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

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from guardian.db.models import ChatMessage
from guardian.identity import get_user_id
from guardian.utils.embed_paths import resolve_local_embed_model
from guardian.vector.store import VectorStore
from guardian.workers.backfill_status import update_status_snapshot

logger = logging.getLogger("embedding_backfill")
logging.basicConfig(level=logging.INFO)

DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_BATCHES = None  # Unlimited by default
DEFAULT_SLEEP_SECONDS = 0
EMBED_SCHEMA_VERSION = 1  # explicit schema version for embeddings
_LOCK_PATH = (
    Path(__file__).resolve().parents[1] / "logs" / "embedding_backfill.lock"
)


def _embeddings_backend() -> str:
    return (os.getenv("CODEXIFY_EMBEDDINGS_BACKEND") or "").strip().lower()


def _is_local_embeddings_backend() -> bool:
    return _embeddings_backend() == "local"


def _get_local_embed_model(*, strict: bool) -> str | None:
    model = (os.getenv("LOCAL_EMBED_MODEL") or "").strip()
    if strict:
        if not model:
            raise RuntimeError(
                "LOCAL_EMBED_MODEL is not set; cannot record embedding metadata."
            )
        return resolve_local_embed_model(RuntimeError)
    return model or None


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


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


def _log_event(event: str, **fields: object) -> None:
    """Emit a structured backfill log event."""
    payload = {"event": event, "timestamp": _utc_now(), **fields}
    logger.info("[backfill] %s", json.dumps(payload, sort_keys=True))


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


def count_pending_messages(
    db, vector_store: VectorStore, scan_batch_size: int
) -> int:
    """
    Count pending messages by scanning in batches to avoid loading the full table.
    """
    pending_total = 0
    cursor_id = 0
    while True:
        pending, cursor_id = fetch_unembedded_messages(
            db, vector_store, scan_batch_size, cursor_id
        )
        if not pending:
            break
        pending_total += len(pending)
    return pending_total


def _get_chroma_count(vector_store: VectorStore) -> int | None:
    """Return the current Chroma collection count when available."""
    embedder = getattr(vector_store, "embedder", None)
    collection = getattr(embedder, "_chroma_collection", None)
    if collection is None:
        return None
    try:
        return int(collection.count())
    except Exception:
        return None


def embed_and_persist(
    messages: List[ChatMessage],
    vector_store: VectorStore,
    dry_run: bool,
    embed_model: str,
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
                "namespace": f"thread:{m.thread_id}",
                "role": m.role,
                "created_at": m.created_at.isoformat(),
                "source": "canonical",
                "embed_schema_version": EMBED_SCHEMA_VERSION,
                "embedding_model": embed_model,
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
    if not _acquire_lock(_LOCK_PATH):
        update_status_snapshot(
            "embedding",
            {
                "last_run_at": _utc_now(),
                "last_exit_reason": "locked",
                "error": "embedding_backfill_locked",
            },
        )
        logger.info("[backfill] another embedding worker is active; exiting")
        return 0

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
    embeddings_backend = _embeddings_backend()
    embed_model = _get_local_embed_model(strict=_is_local_embeddings_backend())
    if not embed_model:
        embed_model = embeddings_backend or "unspecified"
        logger.info(
            "[backfill] LOCAL_EMBED_MODEL not set; backend=%s using embedding_model metadata=%s",
            embeddings_backend or "<unset>",
            embed_model,
        )
    logger.info(f"[backfill] vector_backend={vector_backend}")
    logger.info(
        f"[backfill] embeddings_backend={embeddings_backend or '<unset>'}"
    )
    logger.info(f"[backfill] embed_model={embed_model}")
    logger.info(f"[backfill] batch_size={batch_size}")
    logger.info(
        f"[backfill] max_batches={max_batches if max_batches is not None else 'unlimited'}"
    )
    logger.info(f"[backfill] sleep_seconds={sleep_seconds}")
    logger.info(f"[backfill] dry_run={dry_run}")

    db = None
    total_embedded = 0
    batch_count = 0
    cursor_id = 0
    exit_reason = "completed"
    error_message = None
    run_started_at = _utc_now()
    pending_total = None

    try:
        database_url = _resolve_database_url()
        engine = create_engine(database_url, future=True)
        SessionLocal = sessionmaker(
            bind=engine, autoflush=False, autocommit=False
        )
        db = SessionLocal()

        try:
            vector_store = VectorStore()
        except Exception as exc:
            logger.error(
                "[backfill] %s",
                json.dumps(
                    {
                        "event": "embedding_backfill_boot_failure",
                        "error": str(exc),
                    },
                    sort_keys=True,
                ),
            )
            raise

        total_messages = int(db.query(ChatMessage).count())
        chroma_count = _get_chroma_count(vector_store)
        if chroma_count is not None:
            # Prefer a fast count when Chroma persists embeddings.
            pending_total = max(total_messages - chroma_count, 0)
            pending_source = "chroma_count"
        else:
            scan_batch_size = max(batch_size, 250)
            pending_total = count_pending_messages(
                db, vector_store, scan_batch_size
            )
            pending_source = "scan"

        update_status_snapshot(
            "embedding",
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
            logger.info("[backfill] no pending embeddings; exiting")
            exit_reason = "no_work"
        else:
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
                    logger.info(
                        "[backfill] no more pending messages to embed, exiting"
                    )
                    break

                batch_count += 1
                logger.info(
                    f"[backfill] embedding batch {batch_count} size={len(pending)}"
                )

                try:
                    embed_and_persist(
                        pending, vector_store, dry_run, embed_model
                    )
                    # Embedding state is tracked by the vector store, not the canonical message table.
                    total_embedded += len(pending)
                except Exception as exc:
                    logger.exception("[backfill] batch failed — exiting safely")
                    exit_reason = "error"
                    error_message = str(exc)
                    break

                remaining = max(pending_total - total_embedded, 0)
                update_status_snapshot(
                    "embedding",
                    {
                        "items_processed": total_embedded,
                        "items_remaining": remaining,
                    },
                )
                _log_event(
                    "items_processed",
                    items_processed=total_embedded,
                    items_remaining=remaining,
                )

                if sleep_seconds > 0:
                    logger.info(
                        f"[backfill] sleeping for {sleep_seconds} seconds before next batch"
                    )
                    time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        logger.info("[backfill] interrupted by user")
        exit_reason = "interrupted"
    except Exception as exc:
        logger.exception("[backfill] unhandled error")
        exit_reason = "error"
        error_message = str(exc)
    finally:
        if db is not None:
            db.close()
        _release_lock(_LOCK_PATH)

    remaining = None
    if pending_total is not None:
        remaining = max(pending_total - total_embedded, 0)

    final_update = {
        "last_exit_reason": exit_reason,
        "items_processed": total_embedded,
        "error": error_message,
    }
    if remaining is not None:
        final_update["items_remaining"] = remaining
    update_status_snapshot("embedding", final_update)
    _log_event("exit_reason", exit_reason=exit_reason)
    logger.info(
        f"[backfill] complete — embedded {total_embedded} messages (dry_run={dry_run})"
    )
    # Note: No DB mutations are performed if dry_run; safe commit boundary.

    if exit_reason == "error":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run_once())
