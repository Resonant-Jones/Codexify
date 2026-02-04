"""Document autosave and thread-document linkage API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from guardian.core import event_bus
from guardian.core.ai_router import chat_with_ai
from guardian.core.db import GuardianDB
from guardian.core.dependencies import require_api_key
from guardian.db import models

logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_DOC_FORMATS = {"markdown", "plain"}
_FORMAT_STORAGE_MAP = {"markdown": "md", "plain": "txt"}
_ALLOWED_LLM_PROVIDERS = {"local", "groq", "openai"}


class AutosaveRequest(BaseModel):
    """Request body for autosave endpoint."""

    thread_id: int
    content: str


class AutosaveResponse(BaseModel):
    """Response for autosave endpoint."""

    ok: bool
    document_id: str
    relation: str


class ThreadDocumentResponse(BaseModel):
    """Response for a single thread document."""

    id: str
    title: str
    relation: str
    created_at: str


class DocumentGenerateRequest(BaseModel):
    """Request body for document generation."""

    thread_id: int | None = None
    project_id: int | None = None
    user_id: str | None = None
    title: str | None = None
    prompt: str
    format: str | None = None
    doc_type: str | None = Field(default=None, alias="type")
    context: str | None = None
    provider: str | None = None
    model: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class DocumentGenerateResponse(BaseModel):
    """Response body for document generation."""

    ok: bool
    document_id: str | None = None
    content: str
    format: str
    title: str | None = None
    provider: str | None = None
    model: str | None = None


# Module-level database instance (will be set by guardian_api.py)
_db: GuardianDB | None = None


def configure_db(db: GuardianDB) -> None:
    """Configure the database instance for this router."""
    global _db
    _db = db


def _get_db() -> GuardianDB:
    """Get the configured database instance."""
    if _db is None:
        raise RuntimeError("Database not configured for documents router")
    return _db


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


@router.post("/api/documents/autosave", response_model=AutosaveResponse)
async def autosave_document(
    request: AutosaveRequest,
    _api_key: str = Depends(require_api_key),
) -> dict[str, Any]:
    """
    Autosave a session document linked to a thread.

    If an autosave document already exists for the thread, it will be updated.
    Otherwise, a new document is created and linked to the thread.

    Args:
        request: AutosaveRequest containing thread_id and content

    Returns:
        AutosaveResponse with document_id and relation type

    Raises:
        HTTPException: 400 if validation fails, 404 if thread not found, 500 on errors
    """
    # Validate inputs
    if not request.thread_id:
        logger.warning("Autosave request missing thread_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="thread_id is required",
        )

    if not request.content or not request.content.strip():
        logger.warning("Autosave request missing or empty content")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content is required and cannot be empty",
        )

    try:
        db = _get_db()

        with db.get_session() as session:
            # Verify thread exists
            thread = (
                session.query(models.ChatThread)
                .filter_by(id=request.thread_id)
                .first()
            )
            if not thread:
                logger.warning(
                    f"Thread {request.thread_id} not found for autosave"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread {request.thread_id} not found",
                )

            # Check if autosave document already exists for this thread
            existing_link = (
                session.query(models.ThreadDocument)
                .filter_by(thread_id=request.thread_id, relation="autosave")
                .first()
            )

            if existing_link:
                # Update existing document
                document = (
                    session.query(models.GeneratedDocument)
                    .filter_by(id=existing_link.document_id)
                    .first()
                )

                if document:
                    logger.info(
                        f"Updating autosave document {document.id} for thread {request.thread_id}"
                    )
                    document.content = request.content
                    document_id = document.id
                else:
                    # Link exists but document is missing - create new document
                    logger.warning(
                        f"Autosave link exists but document missing, creating new one"
                    )
                    document_id = str(uuid.uuid4())
                    new_document = models.GeneratedDocument(
                        id=document_id,
                        project_id=thread.project_id,
                        thread_id=request.thread_id,
                        user_id=thread.user_id,
                        title=f"Session notes - {thread.title}",
                        content=request.content,
                        format="md",
                        model="autosave",
                    )
                    session.add(new_document)

                    # Update the link to point to new document
                    existing_link.document_id = document_id
            else:
                # Create new document
                document_id = str(uuid.uuid4())
                logger.info(
                    f"Creating new autosave document {document_id} for thread {request.thread_id}"
                )

                new_document = models.GeneratedDocument(
                    id=document_id,
                    project_id=thread.project_id,
                    thread_id=request.thread_id,
                    user_id=thread.user_id,
                    title=f"Session notes - {thread.title}",
                    content=request.content,
                    format="md",
                    model="autosave",
                )
                session.add(new_document)

                # Create thread-document link
                link = models.ThreadDocument(
                    thread_id=request.thread_id,
                    document_id=document_id,
                    relation="autosave",
                )
                session.add(link)

            session.commit()

        # Emit event (don't let event failures break the response)
        try:
            event_bus.emit_event(
                topic="document.autosave",
                payload={
                    "thread_id": request.thread_id,
                    "document_id": document_id,
                },
            )
        except Exception as e:
            logger.error(f"Failed to emit autosave event: {e}")

        return {"ok": True, "document_id": document_id, "relation": "autosave"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in autosave_document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to autosave document: {str(e)}",
        )


@router.post("/api/documents/generate", response_model=DocumentGenerateResponse)
async def generate_document(
    request: DocumentGenerateRequest,
    _api_key: str = Depends(require_api_key),
) -> dict[str, Any]:
    """Generate a document draft using the configured LLM backend."""
    prompt = _normalize_optional_text(request.prompt)
    if not prompt:
        logger.warning("Document generation request missing prompt")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="prompt is required and cannot be empty",
        )

    if request.thread_id is None or request.thread_id <= 0:
        logger.warning("Document generation request missing thread_id")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="thread_id is required",
        )

    title = _normalize_optional_text(request.title)
    context = _normalize_optional_text(request.context)

    format_hint = _normalize_optional_text(request.format or request.doc_type)
    format_hint = (format_hint or "markdown").lower()
    if format_hint not in _ALLOWED_DOC_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format must be one of: markdown, plain",
        )

    provider = _normalize_optional_text(request.provider)
    if provider:
        provider = provider.lower()
        if provider not in _ALLOWED_LLM_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="provider must be one of: local, groq, openai",
            )

    model = _normalize_optional_text(request.model)
    model_name = model or provider or "default"

    system_content = "You are a document generation assistant. " + (
        "Return markdown formatted content."
        if format_hint == "markdown"
        else "Return plain text without markdown formatting."
    )
    user_lines = []
    if title:
        user_lines.append(f"Title: {title}")
    if context:
        user_lines.append(f"Context: {context}")
    user_lines.append(f"Prompt: {prompt}")
    user_content = "\n".join(user_lines)

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]

    try:
        content = str(chat_with_ai(messages, model=model, provider=provider))
    except HTTPException as exc:
        logger.error("Document generation failed: %s", exc.detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document generation failed. Please try again later.",
        ) from exc
    except Exception as exc:
        logger.error("Document generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document generation failed. Please try again later.",
        ) from exc

    document_id: str | None = None
    try:
        db = _get_db()
        with db.get_session() as session:
            thread = (
                session.query(models.ChatThread)
                .filter_by(id=request.thread_id)
                .first()
            )
            if not thread:
                logger.warning(
                    "Thread %s not found for document generation",
                    request.thread_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread {request.thread_id} not found",
                )

            document_id = str(uuid.uuid4())
            resolved_title = (
                title
                or _normalize_optional_text(getattr(thread, "title", None))
                or "Generated document"
            )
            generated_document = models.GeneratedDocument(
                id=document_id,
                project_id=thread.project_id,
                thread_id=thread.id,
                user_id=thread.user_id or request.user_id,
                title=resolved_title,
                content=content,
                format=_FORMAT_STORAGE_MAP[format_hint],
                model=model_name,
            )
            session.add(generated_document)

            link = models.ThreadDocument(
                thread_id=thread.id,
                document_id=document_id,
                relation="attached",
            )
            session.add(link)
            session.commit()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to persist generated document: %s", exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist generated document.",
        ) from exc

    return {
        "ok": True,
        "document_id": document_id,
        "content": content,
        "format": format_hint,
        "title": title,
        "provider": provider,
        "model": model,
    }


@router.get("/api/threads/{thread_id}/documents")
async def get_thread_documents(thread_id: int) -> dict[str, Any]:
    """
    Get all documents linked to a thread.

    Returns documents with their relation types (autosave, attached, reference).
    Documents are ordered by creation date (newest first).

    Args:
        thread_id: The thread ID to get documents for

    Returns:
        Dict with 'ok' status and 'documents' array

    Raises:
        HTTPException: 404 if thread not found
    """
    try:
        db = _get_db()

        with db.get_session() as session:
            # Verify thread exists
            thread = (
                session.query(models.ChatThread).filter_by(id=thread_id).first()
            )
            if not thread:
                logger.warning(f"Thread {thread_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread {thread_id} not found",
                )

            # Get all thread-document links
            links = (
                session.query(models.ThreadDocument)
                .filter_by(thread_id=thread_id)
                .order_by(models.ThreadDocument.created_at.desc())
                .all()
            )

            # Fetch document details
            documents = []
            for link in links:
                # Try to find in GeneratedDocument first
                doc = (
                    session.query(models.GeneratedDocument)
                    .filter_by(id=link.document_id)
                    .first()
                )

                if doc:
                    documents.append(
                        {
                            "id": doc.id,
                            "title": doc.title,
                            "relation": link.relation,
                            "created_at": (
                                link.created_at.isoformat()
                                if link.created_at
                                else None
                            ),
                        }
                    )
                else:
                    # Document not found - log warning but continue
                    logger.warning(
                        f"Document {link.document_id} linked to thread {thread_id} not found"
                    )

            return {"ok": True, "documents": documents}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_thread_documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve thread documents: {str(e)}",
        )
