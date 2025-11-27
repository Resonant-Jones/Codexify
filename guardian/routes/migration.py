import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from guardian.core.dependencies import (
    _vector_store,
    chatlog_db,
    require_api_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Migration"])


class MigrationStats(BaseModel):
    threads_imported: int
    messages_imported: int


from backend.rag.chatgpt_migration import ingest_chatgpt_export


@router.post("/upload-chatgpt-export", response_model=MigrationStats)
async def upload_chatgpt_export(
    file: UploadFile = File(...),
    user_id: str = Header("default", alias="X-User-Id"),
    api_key: str = Depends(require_api_key),
):
    """
    Import a ChatGPT export file (JSON).
    Creates threads and messages in the database and embeds them in the vector store.
    """
    try:
        content = await file.read()
        stats = ingest_chatgpt_export(content, user_id=user_id)
        return MigrationStats(
            threads_imported=stats["threads"],
            messages_imported=stats["messages"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail="Internal server error")
