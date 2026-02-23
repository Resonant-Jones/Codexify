import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from guardian.core.dependencies import (
    _vector_store,
    chatlog_db,
    get_request_user_id,
    require_api_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Migration"])


class MigrationStats(BaseModel):
    threads_imported: int
    messages_imported: int
    projects_created: Optional[int] = None
    projects_reused: Optional[int] = None
    messages_filtered: Optional[int] = None


from backend.rag.chatgpt_migration import ingest_chatgpt_export


@router.post("/api/upload-chatgpt-export", response_model=MigrationStats)
@router.post("/upload-chatgpt-export", response_model=MigrationStats)
async def upload_chatgpt_export(
    file: UploadFile = File(...),
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """
    Import a ChatGPT export file (JSON).

    Canonical path: /api/upload-chatgpt-export
    Legacy alias: /upload-chatgpt-export
    """
    try:
        content = await file.read()
        stats = ingest_chatgpt_export(content, user_id=user_id)
        return MigrationStats(
            threads_imported=stats["threads_imported"],
            messages_imported=stats["messages_imported"],
            projects_created=stats.get("projects_created"),
            projects_reused=stats.get("projects_reused"),
            messages_filtered=stats.get("messages_filtered"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail="Internal server error")
