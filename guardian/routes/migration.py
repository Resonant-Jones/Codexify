import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from guardian.core.dependencies import (
    chatlog_db,
    get_request_user_id,
    require_api_key,
)
from guardian.services.account_restore import (
    AccountRestoreError,
    AccountRestoreService,
)
from guardian.services.openai_account_import import (
    AccountImportError,
    OpenAIAccountImportService,
    StagedImportFile,
    normalize_import_relative_path,
)
from backend.rag.openai_export_adapter import (
    diagnose_openai_export_path,
    import_openai_export_path,
)
from backend.rag.chatgpt_migration import (
    ingest_chatgpt_export,
    ingest_claude_export,
)
from backend.rag.chatgpt_migration import (
    retry_chatgpt_import_embeddings as retry_chatgpt_import_embeddings_service,
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


class AccountImportCreateRequest(BaseModel):
    total_file_count: int = Field(gt=0)
    total_byte_count: int = Field(ge=0)
    source_system: str = "openai"


def _get_account_import_service() -> OpenAIAccountImportService:
    return OpenAIAccountImportService()


def _raise_account_import_error(exc: AccountImportError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": str(exc)},
    ) from exc


@router.post("/api/imports/openai-account")
async def create_openai_account_import(
    request: AccountImportCreateRequest,
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """Create an account-owned durable staged import job."""

    _ = api_key
    try:
        service = await run_in_threadpool(_get_account_import_service)
        return await run_in_threadpool(
            service.create_job,
            user_id=user_id,
            total_file_count=request.total_file_count,
            total_byte_count=request.total_byte_count,
            source_system=request.source_system,
        )
    except AccountImportError as exc:
        _raise_account_import_error(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/imports/openai-account/{job_id}/files")
async def upload_openai_account_import_batch(
    job_id: str,
    files: list[UploadFile] = File(...),
    relative_paths: list[str] = Form(...),
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """Stage one bounded batch while preserving caller-supplied relative paths."""

    _ = api_key
    if len(files) != len(relative_paths):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "upload_path_count_mismatch",
                "message": "Every uploaded file requires one matching relative path.",
            },
        )
    staged_files: list[StagedImportFile] = []
    batch_bytes = 0
    try:
        service = await run_in_threadpool(_get_account_import_service)
        if not files or len(files) > service.limits.max_batch_files:
            raise AccountImportError(
                "Upload batch file count is outside configured limits.",
                code="batch_file_limit_exceeded",
                status_code=413,
            )
        normalized_paths = [
            normalize_import_relative_path(path) for path in relative_paths
        ]
        for upload, relative_path in zip(files, normalized_paths):
            file_bytes = 0
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                file_bytes += len(chunk)
                batch_bytes += len(chunk)
                if file_bytes > service.limits.max_file_bytes:
                    raise AccountImportError(
                        "An import file exceeds the configured per-file limit.",
                        code="file_size_limit_exceeded",
                        status_code=413,
                    )
                if batch_bytes > service.limits.max_batch_bytes:
                    raise AccountImportError(
                        "Upload batch exceeds the configured byte limit.",
                        code="batch_size_limit_exceeded",
                        status_code=413,
                    )
            await upload.seek(0)
            staged_files.append(
                StagedImportFile(
                    relative_path=relative_path,
                    content_type=upload.content_type,
                    stream=upload.file,
                )
            )
        return await run_in_threadpool(
            service.stage_files,
            job_id=job_id,
            user_id=user_id,
            files=staged_files,
        )
    except AccountImportError as exc:
        _raise_account_import_error(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/imports/openai-account/{job_id}/commit")
async def commit_openai_account_import(
    job_id: str,
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """Finalize a complete staged upload and accept it into the worker queue."""

    _ = api_key
    try:
        service = await run_in_threadpool(_get_account_import_service)
        return await run_in_threadpool(
            service.finalize_job,
            job_id=job_id, user_id=user_id
        )
    except AccountImportError as exc:
        _raise_account_import_error(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/imports/openai-account/{job_id}")
async def get_openai_account_import(
    job_id: str,
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """Read one account-owned import job and its bounded diagnostics."""

    _ = api_key
    try:
        service = await run_in_threadpool(_get_account_import_service)
        return await run_in_threadpool(
            service.get_job,
            job_id=job_id, user_id=user_id
        )
    except AccountImportError as exc:
        _raise_account_import_error(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


def _safe_upload_basename(filename: str | None, fallback: str) -> str:
    if not filename:
        return fallback
    normalized = filename.replace("\\", "/")
    name = Path(normalized).name.strip()
    return name or fallback


def _is_openai_dat_upload(filename: str | None) -> bool:
    name = _safe_upload_basename(filename, "")
    return Path(name).suffix.lower() == ".dat"


def _has_importable_openai_conversation(report: Any) -> bool:
    return any(
        record.conversation_candidate
        and record.detected_kind in {"json_object", "json_array", "jsonl"}
        for record in report.inventory.files
    )


def _to_migration_stats(stats: dict[str, Any]) -> MigrationStats:
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


def _import_openai_dat_upload(
    content: bytes,
    *,
    filename: str | None,
    user_id: str,
) -> dict[str, Any]:
    safe_name = _safe_upload_basename(filename, "openai-export-upload.dat")
    with TemporaryDirectory(prefix="codexify-openai-upload-") as tmpdir:
        upload_path = Path(tmpdir) / safe_name
        upload_path.write_bytes(content)

        report = diagnose_openai_export_path(upload_path)
        if (
            report.inventory.detected_format != "sharded"
            or not _has_importable_openai_conversation(report)
        ):
            raise ValueError(
                "Unsupported OpenAI .dat upload: the single uploaded .dat file "
                "is not a readable JSON/JSONL conversation shard. Full sharded "
                "export folders cannot be represented by this upload route; use "
                "the path-based OpenAI export import tool for folder imports."
            )

        stats = import_openai_export_path(upload_path, user_id=user_id)
        if (
            int(stats.get("conversation_records", 0)) <= 0
            and int(stats.get("threads_imported", 0)) <= 0
            and int(stats.get("messages_imported", 0)) <= 0
        ):
            raise ValueError(
                "OpenAI .dat upload did not contain importable conversation records."
            )
        return stats


@router.post("/api/upload-chatgpt-export", response_model=MigrationStats)
@router.post("/upload-chatgpt-export", response_model=MigrationStats)
async def upload_chatgpt_export(
    file: UploadFile = File(...),
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """
    Import a ChatGPT, Claude, or single-file OpenAI conversation export.

    Auto-detects format: ChatGPT exports (with 'mapping' field) or
    Claude exports (with 'chat_messages' field). Modern OpenAI .dat uploads
    are diagnosed and imported through the OpenAI export adapter.

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

        if _is_openai_dat_upload(file.filename):
            return _to_migration_stats(
                _import_openai_dat_upload(
                    content,
                    filename=file.filename,
                    user_id=user_id,
                )
            )

        # Parse and detect export format
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(
                "Invalid JSON file: unable to parse uploaded content."
            )

        # Auto-detect export format without guessing unsupported shapes.
        export_format = _detect_export_format_parsed(parsed)

        if export_format == "claude":
            stats = ingest_claude_export(content, user_id=user_id)
        elif export_format == "chatgpt":
            stats = ingest_chatgpt_export(content, user_id=user_id)
        else:
            raise ValueError(
                "Unsupported or ambiguous migration upload. Expected a legacy "
                "ChatGPT conversations JSON export, a Claude JSON export, or "
                "a modern OpenAI .dat conversation shard."
            )

        return _to_migration_stats(stats)
    except HTTPException:
        # Re-raise HTTPExceptions without catching them
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
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
