"""Document embedding worker for queued document embed tasks."""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable

from redis.exceptions import TimeoutError as RedisTimeoutError

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core.db import GuardianDB
from guardian.db.models import UploadedDocument
from guardian.queue.document_embed_queue import (
    QUEUE_NAME,
    dequeue_document_embed,
)
from guardian.services.document_chunking import chunk_document_text
from guardian.vector.store import VectorStore

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_db() -> GuardianDB:
    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return GuardianDB(db_url)


def _load_document(db: GuardianDB, doc_id: str) -> dict[str, Any] | None:
    with db.get_session() as session:
        doc = session.query(UploadedDocument).filter_by(id=doc_id).first()
        if not doc:
            return None
        return {
            "id": doc.id,
            "parsed_text": doc.parsed_text,
            "filename": doc.filename,
            "user_id": doc.user_id,
            "project_id": doc.project_id,
            "thread_id": doc.thread_id,
            "embedding_status": doc.embedding_status,
        }


def _update_status(
    db: GuardianDB,
    doc_id: str,
    *,
    status: str,
    error: str | None,
    started_at: datetime | None,
    completed_at: datetime | None,
) -> None:
    with db.get_session() as session:
        session.query(UploadedDocument).filter_by(id=doc_id).update(
            {
                UploadedDocument.embedding_status: status,
                UploadedDocument.embedding_error: error,
                UploadedDocument.embedding_started_at: started_at,
                UploadedDocument.embedding_completed_at: completed_at,
            }
        )
        session.commit()


def _build_chunk_metadata(
    doc: dict[str, Any],
    chunks: list,
) -> list[dict[str, Any]]:
    # Build base metadata with original values, then filter out None keys
    # ChromaDB doesn't accept null values in metadata
    base = {
        "source": "document",
        "filename": doc.get("filename"),
        "doc_id": doc.get("id"),
        "user_id": doc.get("user_id"),
        "project_id": doc.get("project_id"),
        "thread_id": doc.get("thread_id"),
        "timestamp": _utc_now().isoformat(),
    }
    # Filter out None-valued keys - ChromaDB requires non-null primitives
    base = {k: v for k, v in base.items() if v is not None}

    # Ensure numeric fields are proper types when present
    if "project_id" in base and base["project_id"] is not None:
        base["project_id"] = int(base["project_id"])
    if "thread_id" in base and base["thread_id"] is not None:
        base["thread_id"] = int(base["thread_id"])

    return [
        {
            **base,
            "chunk_index": getattr(chunk, "index", index),
            "chunk_count": len(chunks),
        }
        for index, chunk in enumerate(chunks)
    ]


def _write_document_chunks(
    vector_writer: Any,
    chunk_texts: list[str],
    chunk_metas: list[dict[str, Any]],
) -> None:
    if hasattr(vector_writer, "add_texts"):
        vector_writer.add_texts(
            [
                {"text": text, "meta": meta}
                for text, meta in zip(chunk_texts, chunk_metas)
            ]
        )
        return
    vector_writer.embed_and_index(chunk_texts, metadatas=chunk_metas)


def process_document_embed_task(
    payload: dict[str, Any] | None,
    *,
    db: GuardianDB | None = None,
    embedder_factory: Callable[[], Any] | None = None,
) -> bool:
    if not payload or not isinstance(payload, dict):
        logger.warning("[document-embed] invalid payload=%r", payload)
        return False
    doc_id = str(payload.get("doc_id") or "").strip()
    if not doc_id:
        logger.warning("[document-embed] missing doc_id payload=%r", payload)
        return False

    db = db or _get_db()
    doc = _load_document(db, doc_id)
    if not doc:
        logger.warning("[document-embed] doc not found doc_id=%s", doc_id)
        return False
    if doc.get("embedding_status") == "ready":
        logger.info("[document-embed] already ready doc_id=%s", doc_id)
        return True

    parsed_text = doc.get("parsed_text")
    if not isinstance(parsed_text, str) or not parsed_text.strip():
        completed_at = _utc_now()
        _update_status(
            db,
            doc_id,
            status="failed",
            error="parsed_text_missing",
            started_at=None,
            completed_at=completed_at,
        )
        logger.warning("[document-embed] missing parsed text doc_id=%s", doc_id)
        return False

    started_at = _utc_now()
    _update_status(
        db,
        doc_id,
        status="processing",
        error=None,
        started_at=started_at,
        completed_at=None,
    )

    status = "failed"
    error: str | None = None
    try:
        if embedder_factory is None:
            vector_writer = VectorStore()
        else:
            vector_writer = embedder_factory()

        chunks = chunk_document_text(parsed_text)
        chunk_texts = [chunk.text for chunk in chunks]
        if not chunk_texts:
            raise ValueError("no_chunks")

        chunk_metas = _build_chunk_metadata(doc, chunks)
        _write_document_chunks(vector_writer, chunk_texts, chunk_metas)
        status = "ready"
        error = None
        logger.info(
            "[document-embed] embedded doc_id=%s chunks=%s",
            doc_id,
            len(chunks),
        )
    except Exception as exc:
        error = str(exc)
        logger.warning(
            "[document-embed] embedding failed doc_id=%s err=%s",
            doc_id,
            exc,
        )

    completed_at = _utc_now()
    _update_status(
        db,
        doc_id,
        status=status,
        error=error,
        started_at=started_at,
        completed_at=completed_at,
    )
    return status == "ready"


def run_forever() -> None:
    try:
        shared_vector_store = VectorStore()
    except Exception as exc:
        logger.error(
            "[document-embed] %s",
            json.dumps(
                {
                    "event": "document_embed_worker_boot_failure",
                    "queue": QUEUE_NAME,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
        )
        raise SystemExit(1) from exc

    shared_factory = lambda: shared_vector_store
    logger.info("[document-embed] worker started queue=%s", QUEUE_NAME)
    while True:
        try:
            payload = dequeue_document_embed(block=True, timeout=5)
        except RedisTimeoutError:
            logger.debug("[document-embed] redis idle timeout; continuing")
            continue
        except Exception as exc:
            logger.warning(
                "[document-embed] dequeue error; continuing: %s", exc
            )
            time.sleep(1.0)
            continue

        if not payload:
            continue
        try:
            process_document_embed_task(
                payload, embedder_factory=shared_factory
            )
        except Exception as exc:
            logger.warning(
                "[document-embed] task failed payload=%s err=%s",
                payload,
                exc,
            )


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
