"""Document autosave and thread-document linkage API routes."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guardian.core import event_bus
from guardian.core.db import GuardianDB
from guardian.db import models

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.post("/api/documents/autosave", response_model=AutosaveResponse)
async def autosave_document(request: AutosaveRequest) -> Dict[str, Any]:
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
            detail="thread_id is required"
        )

    if not request.content or not request.content.strip():
        logger.warning("Autosave request missing or empty content")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="content is required and cannot be empty"
        )

    try:
        db = _get_db()

        with db.get_session() as session:
            # Verify thread exists
            thread = session.query(models.ChatThread).filter_by(id=request.thread_id).first()
            if not thread:
                logger.warning(f"Thread {request.thread_id} not found for autosave")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread {request.thread_id} not found"
                )

            # Check if autosave document already exists for this thread
            existing_link = session.query(models.ThreadDocument).filter_by(
                thread_id=request.thread_id,
                relation='autosave'
            ).first()

            if existing_link:
                # Update existing document
                document = session.query(models.GeneratedDocument).filter_by(
                    id=existing_link.document_id
                ).first()

                if document:
                    logger.info(f"Updating autosave document {document.id} for thread {request.thread_id}")
                    document.content = request.content
                    document_id = document.id
                else:
                    # Link exists but document is missing - create new document
                    logger.warning(f"Autosave link exists but document missing, creating new one")
                    document_id = str(uuid.uuid4())
                    new_document = models.GeneratedDocument(
                        id=document_id,
                        project_id=thread.project_id,
                        thread_id=request.thread_id,
                        user_id=thread.user_id,
                        title=f"Session notes - {thread.title}",
                        content=request.content,
                        format='md',
                        model='autosave'
                    )
                    session.add(new_document)

                    # Update the link to point to new document
                    existing_link.document_id = document_id
            else:
                # Create new document
                document_id = str(uuid.uuid4())
                logger.info(f"Creating new autosave document {document_id} for thread {request.thread_id}")

                new_document = models.GeneratedDocument(
                    id=document_id,
                    project_id=thread.project_id,
                    thread_id=request.thread_id,
                    user_id=thread.user_id,
                    title=f"Session notes - {thread.title}",
                    content=request.content,
                    format='md',
                    model='autosave'
                )
                session.add(new_document)

                # Create thread-document link
                link = models.ThreadDocument(
                    thread_id=request.thread_id,
                    document_id=document_id,
                    relation='autosave'
                )
                session.add(link)

            session.commit()

        # Emit event (don't let event failures break the response)
        try:
            event_bus.emit_event(
                topic="document.autosave",
                payload={
                    "thread_id": request.thread_id,
                    "document_id": document_id
                }
            )
        except Exception as e:
            logger.error(f"Failed to emit autosave event: {e}")

        return {
            "ok": True,
            "document_id": document_id,
            "relation": "autosave"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in autosave_document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to autosave document: {str(e)}"
        )


@router.get("/api/threads/{thread_id}/documents")
async def get_thread_documents(thread_id: int) -> Dict[str, Any]:
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
            thread = session.query(models.ChatThread).filter_by(id=thread_id).first()
            if not thread:
                logger.warning(f"Thread {thread_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Thread {thread_id} not found"
                )

            # Get all thread-document links
            links = session.query(models.ThreadDocument).filter_by(
                thread_id=thread_id
            ).order_by(models.ThreadDocument.created_at.desc()).all()

            # Fetch document details
            documents = []
            for link in links:
                # Try to find in GeneratedDocument first
                doc = session.query(models.GeneratedDocument).filter_by(id=link.document_id).first()

                if doc:
                    documents.append({
                        "id": doc.id,
                        "title": doc.title,
                        "relation": link.relation,
                        "created_at": link.created_at.isoformat() if link.created_at else None
                    })
                else:
                    # Document not found - log warning but continue
                    logger.warning(
                        f"Document {link.document_id} linked to thread {thread_id} not found"
                    )

            return {
                "ok": True,
                "documents": documents
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_thread_documents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve thread documents: {str(e)}"
        )
