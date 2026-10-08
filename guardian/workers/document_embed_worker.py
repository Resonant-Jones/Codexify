"""Document embedding worker for queued document embed tasks."""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import signal
import select
import socket
import struct
import time
from datetime import datetime, timezone
from typing import Any, Callable

from redis.exceptions import TimeoutError as RedisTimeoutError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core.db import GuardianDB
from guardian.core.config import get_settings, resolve_vector_store_runtime
from guardian.core.chat_postgres_deadline import (
    connect_with_query_bounds,
    postgres_operation_scope,
)
from guardian.db.models import UploadedDocument
from guardian.queue.document_embed_queue import (
    QUEUE_NAME,
    dequeue_document_embed,
)
from guardian.protocol_tokens import EmbeddingLifecycleStatus
from guardian.queue.redis_queue import redis_operation_scope
from guardian.services.document_chunking import chunk_document_text
from guardian.vector.store import VectorStore

logger = logging.getLogger(__name__)
_shutdown_requested = False
# Preparation and terminal transactions each get one physical ten-second budget.
# Child reap gets five seconds; idle transport gets two. Compose reserves 40s
# around the maximum 600s execution interval and an additional strict 5s slack.
DOCUMENT_EMBED_FINALIZATION_MARGIN_SECONDS = 40
_DATABASE_OPERATION_SECONDS = 10
_CHILD_REAP_SECONDS = 5


class _WriterNotReaped(RuntimeError):
    """Terminal persistence is forbidden while the document writer survives."""


class _DocumentChannel:
    """Private JSON channel with physical socket deadlines, including writes."""

    def __init__(self, transport: socket.socket) -> None:
        self.transport = transport
        self.deadline: float | None = None

    def _apply_deadline(self) -> None:
        if self.deadline is not None:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("document_embed_execution_bound_exceeded")
            self.transport.settimeout(remaining)

    def send(self, value) -> None:
        self._apply_deadline()
        raw = json.dumps(value).encode()
        self._apply_deadline()
        self.transport.sendall(struct.pack("!I", len(raw)) + raw)

    def _read(self, count: int) -> bytes:
        data = bytearray()
        while len(data) < count:
            self._apply_deadline()
            chunk = self.transport.recv(count - len(data))
            if not chunk:
                raise EOFError
            data.extend(chunk)
        return bytes(data)

    def recv(self):
        size = struct.unpack("!I", self._read(4))[0]
        return json.loads(self._read(size))

    def poll(self, timeout: float) -> bool:
        return bool(select.select([self.transport], [], [], timeout)[0])

    def close(self) -> None:
        self.transport.close()


class _DocumentDB:
    """Worker-local ORM sessions using the existing physically bounded driver."""

    def __init__(self, db_url: str) -> None:
        dsn = "postgresql://" + db_url.split("://", 1)[1]
        self.engine = create_engine(
            "postgresql+psycopg://",
            creator=lambda: connect_with_query_bounds(dsn),
            poolclass=NullPool,
        )
        self.get_session = sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False,
        )


def _embed_document(doc: dict[str, Any], factory: Callable[[], Any]) -> None:
    vector_writer = factory()
    chunks = chunk_document_text(doc["parsed_text"])
    if not chunks:
        raise ValueError("no_chunks")
    _write_document_chunks(
        vector_writer, [chunk.text for chunk in chunks],
        _build_chunk_metadata(doc, chunks),
    )


def _embedding_child(connection, factory) -> None:
    # Container stop signals belong to the parent. Child termination is explicit
    # SIGKILL followed by reap, never a cooperative Python/native cancellation.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    store = None
    try:
        while True:
            doc = connection.recv()
            if doc is None:
                return
            try:
                if store is None:
                    store = factory()
                _embed_document(doc, lambda: store)
                connection.send((True, None))
            except BaseException as exc:
                connection.send((False, (str(exc) or type(exc).__name__)[:1024]))
    except (EOFError, BrokenPipeError):
        return
    finally:
        connection.close()


class _BoundedEmbedding:
    """One private document writer; preserves the existing in-memory FAISS store."""

    def __init__(self, timeout: float, factory=VectorStore) -> None:
        self.timeout = timeout
        self.factory = factory
        self.backend = resolve_vector_store_runtime().backend
        self.process = None
        self.connection = None

    def close(self) -> None:
        process = self.process
        if process is None:
            return
        if process.is_alive():
            try:
                process.kill()
            except ProcessLookupError:
                pass  # Already exited; join still confirms kernel reap.
        process.join(_CHILD_REAP_SECONDS)
        if process.is_alive():
            # Do not acknowledge a terminal document while its writer exists.
            raise _WriterNotReaped("document_embed_writer_not_reaped")
        logger.info(
            "document_embed_writer_reaped pid=%s exitcode=%s",
            process.pid, process.exitcode,
        )
        process.close()
        self.connection.close()
        self.process = self.connection = None

    def __call__(self, doc: dict[str, Any]) -> None:
        try:
            self._run(doc)
        except TimeoutError:
            self.close()
            raise TimeoutError("document_embed_execution_bound_exceeded") from None
        except BaseException:
            self.close()
            raise

    def _run(self, doc: dict[str, Any]) -> None:
        deadline = time.monotonic() + self.timeout
        if self.process is None:
            context = multiprocessing.get_context("spawn")
            parent_socket, child_socket = socket.socketpair()
            self.connection = _DocumentChannel(parent_socket)
            child_connection = _DocumentChannel(child_socket)
            self.process = context.Process(
                target=_embedding_child, args=(child_connection, self.factory),
                daemon=True,
            )
            self.process.start()
            child_connection.close()
        self.connection.deadline = deadline
        try:
            self.connection.send(doc)
        except TimeoutError:
            raise TimeoutError("document_embed_execution_bound_exceeded") from None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.close()
                raise TimeoutError("document_embed_execution_bound_exceeded")
            if self.connection.poll(min(remaining, 0.05)):
                try:
                    ok, error = self.connection.recv()
                except EOFError:
                    self.close()
                    raise RuntimeError("document_embed_writer_exited") from None
                # Reap on shutdown, success or failure before terminal commit.
                # Otherwise a completed child waits only for the NEXT document;
                # no model/vector call for this document remains on its stack.
                if self.backend == "chroma" or _shutdown_requested or not ok:
                    self.close()
                if not ok:
                    raise RuntimeError(error)
                return
            if not self.process.is_alive():
                self.close()
                raise RuntimeError("document_embed_writer_exited")


def _request_shutdown(signum: int, _frame: Any) -> None:
    global _shutdown_requested
    # Repeated signals leave the active job owned by this worker.
    _shutdown_requested = True


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_db() -> GuardianDB:
    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return _DocumentDB(db_url)


def _load_document(db: GuardianDB, doc_id: str) -> dict[str, Any] | None:
    with db.get_session() as session:
        doc = session.query(UploadedDocument).filter_by(id=doc_id).first()
        if not doc:
            return None
        return {
            "id": doc.id,
            "asset_id": doc.asset_id,
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
    with postgres_operation_scope(_DATABASE_OPERATION_SECONDS), db.get_session() as session:
        changed = session.query(UploadedDocument).filter_by(id=doc_id).update(
            {
                UploadedDocument.embedding_status: status,
                UploadedDocument.embedding_error: error,
                UploadedDocument.embedding_started_at: started_at,
                UploadedDocument.embedding_completed_at: completed_at,
            }
        )
        if changed != 1:
            raise RuntimeError("document_embed_terminal_row_missing")
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
        "media_asset_id": doc.get("asset_id"),
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
    execution: Callable[[dict[str, Any]], None] | None = None,
) -> bool:
    if not payload or not isinstance(payload, dict):
        logger.warning("[document-embed] invalid payload=%r", payload)
        return False
    doc_id = str(payload.get("doc_id") or "").strip()
    if not doc_id:
        logger.warning("[document-embed] missing doc_id payload=%r", payload)
        return False

    db = db or _get_db()
    with postgres_operation_scope(_DATABASE_OPERATION_SECONDS):
        doc = _load_document(db, doc_id)
    if not doc:
        logger.warning("[document-embed] doc not found doc_id=%s", doc_id)
        return False
    if doc.get("embedding_status") == EmbeddingLifecycleStatus.READY.value:
        logger.info("[document-embed] already ready doc_id=%s", doc_id)
        return True

    parsed_text = doc.get("parsed_text")
    if not isinstance(parsed_text, str) or not parsed_text.strip():
        completed_at = _utc_now()
        _update_status(
            db,
            doc_id,
            status=EmbeddingLifecycleStatus.FAILED.value,
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
        status=EmbeddingLifecycleStatus.PROCESSING.value,
        error=None,
        started_at=started_at,
        completed_at=None,
    )

    status = EmbeddingLifecycleStatus.FAILED.value
    error: str | None = None
    try:
        if execution is not None:
            execution(doc)
        elif embedder_factory is None:
            vector_writer = VectorStore()
        else:
            vector_writer = embedder_factory()

        if execution is None:
            chunks = chunk_document_text(parsed_text)
            chunk_texts = [chunk.text for chunk in chunks]
            if not chunk_texts:
                raise ValueError("no_chunks")
            chunk_metas = _build_chunk_metadata(doc, chunks)
            _write_document_chunks(vector_writer, chunk_texts, chunk_metas)
        status = EmbeddingLifecycleStatus.READY.value
        error = None
        logger.info(
            "[document-embed] embedded doc_id=%s chunks=%s",
            doc_id,
            "bounded" if execution is not None else len(chunks),
        )
    except _WriterNotReaped:
        raise
    except BaseException as exc:
        error = str(exc) or exc.__class__.__name__
        logger.warning(
            "[document-embed] embedding failed doc_id=%s err=%s",
            doc_id,
            exc,
        )
    completed_at = _utc_now()
    _update_status(
        db, doc_id, status=status, error=error,
        started_at=started_at, completed_at=completed_at,
    )
    logger.info("document_embed_terminal_ack doc_id=%s status=%s", doc_id, status)
    return status == EmbeddingLifecycleStatus.READY.value


def run_forever() -> None:
    global _shutdown_requested
    _shutdown_requested = False
    signal.signal(signal.SIGTERM, _request_shutdown)
    signal.signal(signal.SIGINT, _request_shutdown)
    timeout = get_settings().DOCUMENT_EMBED_EXECUTION_TIMEOUT_SECONDS
    execution = _BoundedEmbedding(timeout)
    logger.info(
        "[document-embed] worker started queue=%s execution_bound_seconds=%s "
        "finalization_margin_seconds=%s",
        QUEUE_NAME, timeout, DOCUMENT_EMBED_FINALIZATION_MARGIN_SECONDS,
    )
    try:
        while not _shutdown_requested:
            try:
                with redis_operation_scope(2):
                    payload = dequeue_document_embed(block=False)
            except RedisTimeoutError:
                continue
            except Exception as exc:
                logger.warning("[document-embed] dequeue error: %s", type(exc).__name__)
                time.sleep(0.05)
                continue
            if not payload:
                time.sleep(0.05)
                continue
            # A dequeue already in flight when the signal arrives is still
            # owned. Drain this job; never dequeue another after the signal.
            process_document_embed_task(payload, execution=execution)
    finally:
        execution.close()
    logger.info("document_embed_worker_drained")


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
