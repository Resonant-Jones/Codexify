"""Workspace aggregation routes.

Provides combined thread metadata, linked documents, and a diagnostic snapshot
for Workspace Pane hydration and rehydration.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from guardian.core.chat_db import ChatDB
from guardian.db import models
from guardian.sensors.state import Sensors

logger = logging.getLogger(__name__)

router = APIRouter()


# ── DB init (mirrors other route modules) ────────────────────────────────────
chatlog_db: ChatDB | None = None
_orm_db = None  # Optional ORM session provider; when unavailable, documents list falls back to []


def _collect_thread_documents(thread_id: int) -> list[dict[str, Any]]:
    """Return documents linked to a thread via ThreadDocument relations.

    Safe fallback: returns [] on errors.
    """
    docs: list[dict[str, Any]] = []
    if _orm_db is None:
        return []
    try:
        with _orm_db.get_session() as session:  # type: ignore[union-attr]
            # Verify thread exists (best effort)
            thr = (
                session.query(models.ChatThread).filter_by(id=thread_id).first()
            )
            if not thr:
                return []
            links = (
                session.query(models.ThreadDocument)
                .filter_by(thread_id=thread_id)
                .order_by(models.ThreadDocument.created_at.desc())
                .all()
            )
            for link in links:
                doc = (
                    session.query(models.GeneratedDocument)
                    .filter_by(id=link.document_id)
                    .first()
                )
                if not doc:
                    continue
                docs.append(
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "relation": link.relation,
                        "created_at": (
                            link.created_at.isoformat()
                            if link.created_at
                            else None
                        ),
                    }
                )
    except Exception as e:  # pragma: no cover – defensive
        logger.debug("workspace docs fetch failed: %s", e)
        return []
    return docs


@router.get("/api/workspace/{thread_id}")
def workspace_state(thread_id: int) -> dict[str, Any]:
    """Return workspace data for a thread: metadata, linked documents, diagnostics."""
    try:
        if chatlog_db is None:
            raise HTTPException(
                status_code=500, detail="workspace_not_configured"
            )
        thr = chatlog_db.get_chat_thread(thread_id)
        if not thr:
            raise HTTPException(status_code=404, detail="Thread not found")

        docs = _collect_thread_documents(thread_id)
        sensors = Sensors(chatlog_db)
        diag = sensors.snapshot()

        return {"thread": thr, "documents": docs, "diagnostics": diag}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("workspace_state failed: %s", e)
        raise HTTPException(status_code=500, detail="workspace_state_failed")
