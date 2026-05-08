import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from guardian.core.dependencies import (
    _vector_store,
    chatlog_db,
    get_request_user_id,
    require_api_key,
)
from guardian.services.account_restore import (
    AccountRestoreError,
    AccountRestoreService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Migration"])


class MigrationStats(BaseModel):
    threads_imported: int
    messages_imported: int
    projects_created: Optional[int] = None
    projects_reused: Optional[int] = None
    messages_filtered: Optional[int] = None
    embedding_candidates: int = 0
    embeddings_persisted: int = 0
    embeddings_failed: int = 0
    embedding_coverage_degraded: bool = False


class EmbeddingRetryStats(BaseModel):
    embedding_candidates: int = 0
    embeddings_persisted: int = 0
    embeddings_failed: int = 0
    embedding_coverage_degraded: bool = False


@router.post("/api/imports/account/metadata")
@router.post("/imports/account/metadata")
async def import_account_metadata(
    file: UploadFile = File(...),
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """
    Import a canonical Codexify account export ZIP as a metadata-only restore.

    This slice restores relational metadata and links only. Blob write-back is
    not implemented here.
    """
    _ = api_key

    if chatlog_db is None:
        error = AccountRestoreError(
            "Account database is not available",
            code="restore_backend_unavailable",
            status_code=503,
            validated=False,
            notes=[
                "Metadata restore is unavailable until the account database is configured.",
            ],
        )
        return JSONResponse(
            status_code=error.status_code, content=error.to_payload()
        )

    try:
        chunks = bytearray()
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            chunks.extend(chunk)

        service = AccountRestoreService(chatlog_db)
        report = service.restore_from_zip(bytes(chunks), user_id=user_id)
        return report
    except AccountRestoreError as exc:
        return JSONResponse(
            status_code=exc.status_code, content=exc.to_payload()
        )
    except Exception:
        logger.exception("Account metadata restore failed")
        error = AccountRestoreError(
            "Unexpected account metadata restore failure",
            code="account_restore_unexpected_error",
            status_code=500,
            validated=False,
            notes=[
                "The archive was not restored.",
            ],
        )
        return JSONResponse(
            status_code=error.status_code, content=error.to_payload()
        )


from backend.rag.chatgpt_migration import (
    ingest_chatgpt_export,
    ingest_claude_export,
)
from backend.rag.chatgpt_migration import (
    retry_chatgpt_import_embeddings as retry_chatgpt_import_embeddings_service,
)


def _detect_export_format_parsed(data: Any) -> str:
    """Auto-detect whether content is a ChatGPT or Claude export format.
    Takes already-parsed JSON data (dict or list).
    """
    # ChatGPT exports are a list (or dict with 'mapping' in first item)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "mapping" in item:
                    return "chatgpt"
                # Claude exports have 'chat_messages' in each conversation
                if "chat_messages" in item:
                    return "claude"
    elif isinstance(data, dict):
        if "mapping" in data:
            return "chatgpt"
        if "chat_messages" in data:
            return "claude"
        # Check nested conversations/threads/chats/data
        convs = (
            data.get("conversations")
            or data.get("threads")
            or data.get("chats")
            or data.get("data")
        )
        if isinstance(convs, list):
            for item in convs:
                if isinstance(item, dict):
                    if "chat_messages" in item:
                        return "claude"
                    if "mapping" in item:
                        return "chatgpt"
    return "unknown"


@router.post("/api/upload-chatgpt-export", response_model=MigrationStats)
@router.post("/upload-chatgpt-export", response_model=MigrationStats)
async def upload_chatgpt_export(
    file: UploadFile = File(...),
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """
    Import a ChatGPT or Claude export file (JSON).

    Auto-detects format: ChatGPT exports (with 'mapping' field) or
    Claude exports (with 'chat_messages' field).

    Canonical path: /api/upload-chatgpt-export
    Legacy alias: /upload-chatgpt-export
    """
    try:
        # Read the upload in bounded chunks to avoid a single large read.
        chunks = bytearray()
        while True:
            chunk = await file.read(1024 * 1024)  # 1MB chunks
            if not chunk:
                break
            chunks.extend(chunk)

        content = bytes(chunks)

        # Parse and detect export format
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(
                "Invalid JSON file: unable to parse uploaded content."
            )

        # Auto-detect export format (default to ChatGPT for backward compatibility)
        export_format = _detect_export_format_parsed(parsed)
        if export_format == "unknown":
            export_format = "chatgpt"

        if export_format == "claude":
            stats = ingest_claude_export(content, user_id=user_id)
        elif export_format == "chatgpt":
            stats = ingest_chatgpt_export(content, user_id=user_id)
        else:
            raise ValueError(
                "Unrecognized export format. Expected a ChatGPT export (with 'mapping' field) "
                "or a Claude export (with 'chat_messages' field)."
            )

        return MigrationStats(
            threads_imported=stats["threads_imported"],
            messages_imported=stats["messages_imported"],
            projects_created=stats.get("projects_created"),
            projects_reused=stats.get("projects_reused"),
            messages_filtered=stats.get("messages_filtered"),
            embedding_candidates=int(stats.get("embedding_candidates", 0)),
            embeddings_persisted=int(stats.get("embeddings_persisted", 0)),
            embeddings_failed=int(stats.get("embeddings_failed", 0)),
            embedding_coverage_degraded=bool(
                stats.get("embedding_coverage_degraded", False)
            ),
        )
    except HTTPException:
        # Re-raise HTTPExceptions without catching them
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Migration failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/api/retry-chatgpt-import-embeddings", response_model=EmbeddingRetryStats
)
@router.post(
    "/retry-chatgpt-import-embeddings", response_model=EmbeddingRetryStats
)
async def retry_chatgpt_import_embeddings(
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """
    Retry embedding persistence for ChatGPT-imported messages that are pending
    or previously failed embedding writes.

    Canonical path: /api/retry-chatgpt-import-embeddings
    Legacy alias: /retry-chatgpt-import-embeddings
    """
    try:
        stats = retry_chatgpt_import_embeddings_service(user_id=user_id)
        return EmbeddingRetryStats(
            embedding_candidates=int(stats.get("embedding_candidates", 0)),
            embeddings_persisted=int(stats.get("embeddings_persisted", 0)),
            embeddings_failed=int(stats.get("embeddings_failed", 0)),
            embedding_coverage_degraded=bool(
                stats.get("embedding_coverage_degraded", False)
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ChatGPT embedding retry failed")
        raise HTTPException(status_code=500, detail="Internal server error")
