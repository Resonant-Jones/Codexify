"""Startup ingest for bundled Codexify help documents."""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guardian.core.default_project import DEFAULT_PROJECT_NAME
from guardian.db import models
from guardian.protocol_tokens import EmbeddingLifecycleStatus

logger = logging.getLogger(__name__)

BUILTIN_HELP_SOURCE_TAG = "builtin_help"
BUILTIN_HELP_REL_PATH = Path("docs/builtin-help/codexify-guide.md")
BUILTIN_HELP_FILENAME = BUILTIN_HELP_REL_PATH.name
BUILTIN_HELP_TITLE = "Codexify Guide"
BUILTIN_HELP_MIME_TYPE = "text/markdown"
BUILTIN_HELP_DOCUMENT_ID = str(
    uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"{BUILTIN_HELP_SOURCE_TAG}:{BUILTIN_HELP_REL_PATH.as_posix()}",
    )
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_source_path(repo_root: Path | None = None) -> tuple[Path, str]:
    base = repo_root or _repo_root()
    source_path = base / BUILTIN_HELP_REL_PATH
    return source_path, BUILTIN_HELP_REL_PATH.as_posix()


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _vector_metadata(
    *,
    content_hash: str,
    project_id: int,
    source_path: str,
) -> dict[str, Any]:
    namespace = f"project:{project_id}"
    return {
        "content_hash": content_hash,
        "document_id": BUILTIN_HELP_DOCUMENT_ID,
        "filename": BUILTIN_HELP_FILENAME,
        "namespace": namespace,
        "project_id": project_id,
        "project_name": DEFAULT_PROJECT_NAME,
        "scope": DEFAULT_PROJECT_NAME,
        "source_path": source_path,
        "source_tag": BUILTIN_HELP_SOURCE_TAG,
        "title": BUILTIN_HELP_TITLE,
    }


def _ensure_project_document_link(
    session: Any,
    *,
    project_id: int,
    document_id: str,
    attached_by: str | None = None,
) -> bool:
    """Ensure the built-in help document is linked into the project scope."""
    if not project_id or not document_id:
        return False

    existing = (
        session.query(models.ProjectDocumentLink)
        .filter_by(
            project_id=project_id,
            document_id=document_id,
            document_type="uploaded",
        )
        .first()
    )
    if existing:
        changed = False
        if existing.is_enabled is False:
            existing.is_enabled = True
            changed = True
        if (
            attached_by
            and getattr(existing, "attached_by", None) != attached_by
        ):
            existing.attached_by = attached_by
            changed = True
        return changed

    session.add(
        models.ProjectDocumentLink(
            project_id=project_id,
            document_id=document_id,
            document_type="uploaded",
            is_enabled=True,
            attached_by=attached_by,
        )
    )
    return True


def _load_vector_store(vector_store: Any | None) -> Any:
    if vector_store is not None:
        return vector_store

    from guardian.vector.store import VectorStore

    return VectorStore()


def ingest_builtin_help_document(
    guardian_db: Any,
    *,
    vector_store: Any | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Upsert the bundled help document into the document table and vector store."""
    if guardian_db is None:
        return {
            "status": "skipped",
            "reason": "guardian_db_unavailable",
            "document_id": BUILTIN_HELP_DOCUMENT_ID,
            "source_path": BUILTIN_HELP_REL_PATH.as_posix(),
        }

    source_path, rel_path = _resolve_source_path(repo_root)
    if not source_path.exists():
        logger.info(
            "[builtin-help] skipped missing source file path=%s", source_path
        )
        return {
            "status": "skipped",
            "reason": "missing_source_file",
            "document_id": BUILTIN_HELP_DOCUMENT_ID,
            "source_path": rel_path,
        }

    content = source_path.read_text(encoding="utf-8")
    content_hash = _content_hash(content)
    now = datetime.now(timezone.utc)
    project_id = int(guardian_db.ensure_default_project())
    vector_store = _load_vector_store(vector_store)
    source_bytes = len(content.encode("utf-8"))

    with guardian_db.get_session() as session:
        document = (
            session.query(models.UploadedDocument)
            .filter_by(id=BUILTIN_HELP_DOCUMENT_ID)
            .first()
        )

        document_is_fresh = (
            document is not None
            and getattr(document, "deleted_at", None) is None
            and getattr(document, "parsed_text", None) == content
            and int(getattr(document, "project_id", 0) or 0) == project_id
            and str(getattr(document, "source_tag", "") or "").strip().lower()
            == BUILTIN_HELP_SOURCE_TAG
            and str(getattr(document, "src_url", "") or "").strip() == rel_path
            and str(getattr(document, "embedding_status", "") or "")
            .strip()
            .lower()
            == EmbeddingLifecycleStatus.READY.value
        )

        if document_is_fresh:
            link_changed = _ensure_project_document_link(
                session,
                project_id=project_id,
                document_id=BUILTIN_HELP_DOCUMENT_ID,
                attached_by=BUILTIN_HELP_SOURCE_TAG,
            )
            if link_changed:
                session.commit()
                logger.info(
                    "[builtin-help] link repaired doc_id=%s path=%s",
                    BUILTIN_HELP_DOCUMENT_ID,
                    rel_path,
                )
                return {
                    "status": "updated",
                    "document_id": BUILTIN_HELP_DOCUMENT_ID,
                    "source_path": rel_path,
                    "source_tag": BUILTIN_HELP_SOURCE_TAG,
                    "content_hash": content_hash,
                    "project_id": project_id,
                    "vector_written": False,
                }
            logger.info(
                "[builtin-help] already present doc_id=%s path=%s",
                BUILTIN_HELP_DOCUMENT_ID,
                rel_path,
            )
            return {
                "status": "already_present",
                "document_id": BUILTIN_HELP_DOCUMENT_ID,
                "source_path": rel_path,
                "source_tag": BUILTIN_HELP_SOURCE_TAG,
                "content_hash": content_hash,
                "project_id": project_id,
                "vector_written": False,
            }

        if document is None:
            document = models.UploadedDocument(
                id=BUILTIN_HELP_DOCUMENT_ID,
                project_id=project_id,
                thread_id=None,
                user_id=None,
                filename=BUILTIN_HELP_FILENAME,
                filesize=source_bytes,
                mime_type=BUILTIN_HELP_MIME_TYPE,
                src_url=rel_path,
                source_tag=BUILTIN_HELP_SOURCE_TAG,
                parsed_text=content,
                embedding_status=EmbeddingLifecycleStatus.PROCESSING.value,
                embedding_error=None,
                embedding_started_at=now,
                embedding_completed_at=None,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            session.add(document)
            _ensure_project_document_link(
                session,
                project_id=project_id,
                document_id=BUILTIN_HELP_DOCUMENT_ID,
                attached_by=BUILTIN_HELP_SOURCE_TAG,
            )
            operation = "created"
        else:
            document.project_id = project_id
            document.thread_id = None
            document.user_id = None
            document.filename = BUILTIN_HELP_FILENAME
            document.filesize = source_bytes
            document.mime_type = BUILTIN_HELP_MIME_TYPE
            document.src_url = rel_path
            document.source_tag = BUILTIN_HELP_SOURCE_TAG
            document.parsed_text = content
            document.embedding_status = (
                EmbeddingLifecycleStatus.PROCESSING.value
            )
            document.embedding_error = None
            document.embedding_started_at = now
            document.embedding_completed_at = None
            document.deleted_at = None
            document.updated_at = now
            _ensure_project_document_link(
                session,
                project_id=project_id,
                document_id=BUILTIN_HELP_DOCUMENT_ID,
                attached_by=BUILTIN_HELP_SOURCE_TAG,
            )
            operation = "updated"

        session.commit()

    metadata = _vector_metadata(
        content_hash=content_hash,
        project_id=project_id,
        source_path=rel_path,
    )

    try:
        vector_store.add_texts(
            [
                {
                    "id": BUILTIN_HELP_DOCUMENT_ID,
                    "text": content,
                    "meta": metadata,
                }
            ]
        )
    except Exception as exc:
        failed_at = datetime.now(timezone.utc)
        with guardian_db.get_session() as session:
            document = (
                session.query(models.UploadedDocument)
                .filter_by(id=BUILTIN_HELP_DOCUMENT_ID)
                .first()
            )
            if document is not None:
                document.embedding_status = (
                    EmbeddingLifecycleStatus.FAILED.value
                )
                document.embedding_error = str(exc) or exc.__class__.__name__
                document.embedding_completed_at = failed_at
                document.updated_at = failed_at
                session.commit()
        logger.warning(
            "[builtin-help] vector ingest failed doc_id=%s err=%s",
            BUILTIN_HELP_DOCUMENT_ID,
            exc,
        )
        raise

    completed_at = datetime.now(timezone.utc)
    with guardian_db.get_session() as session:
        document = (
            session.query(models.UploadedDocument)
            .filter_by(id=BUILTIN_HELP_DOCUMENT_ID)
            .first()
        )
        if document is not None:
            document.embedding_status = EmbeddingLifecycleStatus.READY.value
            document.embedding_error = None
            document.embedding_completed_at = completed_at
            document.updated_at = completed_at
            session.commit()

    logger.info(
        "[builtin-help] %s doc_id=%s path=%s hash=%s",
        operation,
        BUILTIN_HELP_DOCUMENT_ID,
        rel_path,
        content_hash,
    )
    return {
        "status": operation,
        "document_id": BUILTIN_HELP_DOCUMENT_ID,
        "source_path": rel_path,
        "source_tag": BUILTIN_HELP_SOURCE_TAG,
        "content_hash": content_hash,
        "project_id": project_id,
        "vector_written": True,
    }
