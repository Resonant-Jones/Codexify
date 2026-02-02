"""Secure shareable links API routes for threads and documents."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from guardian.core import event_bus
from guardian.core.db import GuardianDB
from guardian.db import models

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateShareRequest(BaseModel):
    """Request body for creating a share link."""

    target_type: str  # 'thread' or 'document'
    target_id: int
    expires_in_days: int | None = None  # Optional expiry in days


class CreateShareResponse(BaseModel):
    """Response for create share endpoint."""

    ok: bool
    token: str
    url: str
    expires_at: str | None = None


class ShareContentResponse(BaseModel):
    """Response for share retrieval endpoint."""

    ok: bool
    target_type: str
    target_id: int
    content: dict[str, Any]  # Thread or document details


# Module-level database instance (will be set by guardian_api.py)
_db: GuardianDB | None = None


def configure_db(db: GuardianDB) -> None:
    """Configure the database instance for this router."""
    global _db
    _db = db


def _get_db() -> GuardianDB:
    """Get the configured database instance."""
    if _db is None:
        raise RuntimeError("Database not configured for share router")
    return _db


@router.post("/api/share", response_model=CreateShareResponse)
async def create_share_link(request: CreateShareRequest) -> dict[str, Any]:
    """
    Create a secure shareable link for a thread or document.

    The returned token can be used to create a public URL like:
    https://yourdomain.com/share/{token}

    Args:
        request: CreateShareRequest with target_type, target_id, and optional expires_in_days

    Returns:
        CreateShareResponse with secure token and URL

    Raises:
        HTTPException: 400 if invalid target_type, 404 if target not found, 500 on errors
    """
    # Validate target_type
    if request.target_type not in ("thread", "document"):
        logger.warning(f"Invalid target_type: {request.target_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_type must be 'thread' or 'document'",
        )

    try:
        db = _get_db()

        with db.get_session() as session:
            # Verify target exists
            if request.target_type == "thread":
                target = (
                    session.query(models.ChatThread)
                    .filter_by(id=request.target_id)
                    .first()
                )
                if not target:
                    logger.warning(
                        f"Thread {request.target_id} not found for sharing"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Thread {request.target_id} not found",
                    )
            else:  # document
                # Check both GeneratedDocument and UploadedDocument
                target = (
                    session.query(models.GeneratedDocument)
                    .filter_by(id=str(request.target_id))
                    .first()
                )
                if not target:
                    target = (
                        session.query(models.UploadedDocument)
                        .filter_by(id=str(request.target_id))
                        .first()
                    )

                if not target:
                    logger.warning(
                        f"Document {request.target_id} not found for sharing"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Document {request.target_id} not found",
                    )

            # Generate secure token
            token = secrets.token_urlsafe(32)  # 43 chars URL-safe token

            # Calculate expiry if specified
            expires_at = None
            if request.expires_in_days and request.expires_in_days > 0:
                expires_at = datetime.now(UTC) + timedelta(
                    days=request.expires_in_days
                )

            # Create SharedLink record
            share_id = str(uuid.uuid4())
            shared_link = models.SharedLink(
                id=share_id,
                target_type=request.target_type,
                target_id=request.target_id,
                token=token,
                expires_at=expires_at,
            )
            session.add(shared_link)
            session.commit()

            logger.info(
                f"Created share link {share_id} for {request.target_type} {request.target_id}"
            )

            # Emit event (don't let event failures break the response)
            try:
                event_bus.emit_event(
                    topic="share.created",
                    payload={
                        "share_id": share_id,
                        "target_type": request.target_type,
                        "target_id": request.target_id,
                        "token": token,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to emit share.created event: {e}")

            return {
                "ok": True,
                "token": token,
                "url": f"/share/{token}",
                "expires_at": expires_at.isoformat() if expires_at else None,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_share_link: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(e)}",
        )


@router.get("/api/share/{token}", response_model=ShareContentResponse)
async def retrieve_share_content(token: str) -> dict[str, Any]:
    """
    Retrieve content shared via a secure token.

    Returns read-only thread or document content that has been shared.
    Validates that the link has not expired.

    Args:
        token: The secure share token

    Returns:
        ShareContentResponse with target type and content details

    Raises:
        HTTPException: 404 if token not found or expired, 500 on errors
    """
    try:
        db = _get_db()

        with db.get_session() as session:
            # Find share link by token
            shared_link = (
                session.query(models.SharedLink).filter_by(token=token).first()
            )

            if not shared_link:
                logger.warning(f"Share token {token} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Share link not found or has been revoked",
                )

            # Check expiry
            if (
                shared_link.expires_at
                and datetime.now(UTC) > shared_link.expires_at
            ):
                logger.warning(f"Share token {token} has expired")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Share link has expired",
                )

            # Fetch target content
            content = {}

            if shared_link.target_type == "thread":
                thread = (
                    session.query(models.ChatThread)
                    .filter_by(id=shared_link.target_id)
                    .first()
                )

                if not thread:
                    logger.warning(
                        f"Thread {shared_link.target_id} referenced by share token not found"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Shared thread has been deleted",
                    )

                # Fetch messages for this thread
                messages = (
                    session.query(models.ChatMessage)
                    .filter_by(thread_id=thread.id)
                    .order_by(models.ChatMessage.created_at.asc())
                    .all()
                )

                content = {
                    "id": thread.id,
                    "title": thread.title,
                    "summary": thread.summary,
                    "created_at": (
                        thread.created_at.isoformat()
                        if thread.created_at
                        else None
                    ),
                    "updated_at": (
                        thread.updated_at.isoformat()
                        if thread.updated_at
                        else None
                    ),
                    "messages": [
                        {
                            "id": msg.id,
                            "role": msg.role,
                            "content": msg.content,
                            "created_at": (
                                msg.created_at.isoformat()
                                if msg.created_at
                                else None
                            ),
                        }
                        for msg in messages
                    ],
                }

            elif shared_link.target_type == "document":
                # Try GeneratedDocument first
                document = (
                    session.query(models.GeneratedDocument)
                    .filter_by(id=str(shared_link.target_id))
                    .first()
                )

                if not document:
                    # Try UploadedDocument
                    document = (
                        session.query(models.UploadedDocument)
                        .filter_by(id=str(shared_link.target_id))
                        .first()
                    )

                if not document:
                    logger.warning(
                        f"Document {shared_link.target_id} referenced by share token not found"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Shared document has been deleted",
                    )

                # Extract content based on document type
                # Check for GeneratedDocument (has 'content' and 'format' attributes)
                if hasattr(document, "content") and hasattr(document, "format"):
                    content = {
                        "id": document.id,
                        "title": document.title,
                        "content": document.content,
                        "format": document.format,
                        "created_at": (
                            document.created_at.isoformat()
                            if document.created_at
                            else None
                        ),
                        "updated_at": (
                            document.updated_at.isoformat()
                            if document.updated_at
                            else None
                        ),
                    }
                else:  # UploadedDocument (has 'filename' and 'mime_type' attributes)
                    content = {
                        "id": document.id,
                        "filename": document.filename,
                        "filesize": document.filesize,
                        "mime_type": document.mime_type,
                        "src_url": document.src_url,
                        "created_at": (
                            document.created_at.isoformat()
                            if document.created_at
                            else None
                        ),
                        "updated_at": (
                            document.updated_at.isoformat()
                            if document.updated_at
                            else None
                        ),
                    }

            # Emit event (don't let event failures break the response)
            try:
                event_bus.emit_event(
                    topic="share.accessed",
                    payload={
                        "share_id": shared_link.id,
                        "token": token,
                        "target_type": shared_link.target_type,
                        "target_id": shared_link.target_id,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to emit share.accessed event: {e}")

            return {
                "ok": True,
                "target_type": shared_link.target_type,
                "target_id": shared_link.target_id,
                "content": content,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in retrieve_share_content: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve shared content: {str(e)}",
        )
