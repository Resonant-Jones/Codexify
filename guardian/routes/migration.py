import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any, Optional
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator
from starlette.concurrency import run_in_threadpool

from guardian.core.dependencies import (
    chatlog_db,
    get_account_user_id as get_request_user_id,
    require_account_session as require_api_key,
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

from guardian.conversation_origin import ConversationOriginSystem
from guardian.core import dependencies
from guardian.core.auth import (
    reject_mixed_principal_credentials,
    resolve_account_session_subject,
)
from guardian.services.imported_history_evidence import (
    MAX_EXCERPT_BYTES,
    MAX_INSPECTED_MESSAGES,
    MAX_MESSAGES,
    MAX_OFFSET,
    MAX_RESPONSE_BYTES,
    MAX_THREADS,
    EvidenceAccessError,
    EvidenceMetadataError,
    EvidenceReadError,
    EvidenceRequestError,
    ImportedHistoryEvidenceReader,
    InspectionLimits,
)
from guardian.services.imported_history_inspection_access import (
    resolve_inspection_access,
)
from guardian.services.chronicle_interpretation_authorization import (
    ChronicleAuthorizationError,
    ChronicleAuthorizationUnavailable,
    authorize_chronicle_interpretation,
)
from guardian.services.chronicle_model_exposure import ReviewedEvidenceReference
from guardian.services.chronicle_preview import (
    ChroniclePreviewError,
    ChroniclePreviewUnavailable,
    generate_chronicle_preview,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Migration"])


# The existing router/feature boundary owns this operation. Its route class
# sanitizes validation/auth failures as well as service failures, before any
# rejected client input or persisted SQL diagnostics can reach the response.
class _HistoryInspectionRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded_handler(request: Request):
            try:
                response = await handler(request)
            except RequestValidationError:
                response = JSONResponse(
                    status_code=422, content={"detail": "Invalid inspection selection"}
                )
            except HTTPException as exc:
                detail = {
                    400: "Conflicting authentication contexts",
                    401: "Account authentication required",
                    403: "Selected history unavailable",
                    404: "Selected history unavailable",
                    409: "Unsafe history metadata",
                    422: "Invalid inspection selection",
                    500: "Account authentication unavailable",
                    503: "History inspection unavailable",
                }.get(exc.status_code, "History inspection unavailable")
                response = JSONResponse(
                    status_code=exc.status_code, content={"detail": detail}
                )
                # Preserve existing account-auth failure classification headers.
                if exc.headers:
                    response.headers.update(exc.headers)
            except Exception:
                # Authentication storage or unexpected read failures must not
                # disclose diagnostics or lose the inspection cache boundary.
                response = JSONResponse(
                    status_code=503,
                    content={"detail": "History inspection unavailable"},
                )
            response.headers["Cache-Control"] = "no-store"
            return response

        return bounded_handler


_CanonicalId = Annotated[int, Field(strict=True, gt=0, le=2147483647)]


class HistoryInspectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: _CanonicalId
    thread_ids: list[_CanonicalId] = Field(min_length=1, max_length=MAX_THREADS)
    origins: list[ConversationOriginSystem] = Field(min_length=1, max_length=2)
    max_messages: int = Field(strict=True, gt=0, le=MAX_MESSAGES)
    max_inspected_messages: int = Field(strict=True, gt=0, le=MAX_INSPECTED_MESSAGES)
    max_excerpt_bytes: int = Field(strict=True, gt=0, le=MAX_EXCERPT_BYTES)
    max_response_bytes: int = Field(strict=True, gt=0, le=MAX_RESPONSE_BYTES)
    offset: int = Field(strict=True, ge=0, le=MAX_OFFSET)

    @field_validator("thread_ids")
    @classmethod
    def unique_threads(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate thread selection")
        return value

    @field_validator("origins")
    @classmethod
    def imported_origins(cls, value):
        if len(set(value)) != len(value) or any(
            o
            not in (ConversationOriginSystem.OPENAI, ConversationOriginSystem.ANTHROPIC)
            for o in value
        ):
            raise ValueError("Explicit imported origins required")
        return value


class ChronicleAuthorizationRequest(HistoryInspectionRequest):
    purpose: Literal["migration_chronicle_preview"]
    interpretation_consent: bool = Field(strict=True)
    import_treatment: Literal[
        "archive_only", "recallable_archive", "continuity_scaffold"
    ]


class ReviewedEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: _CanonicalId
    message_id: _CanonicalId
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    approve_for_local_chronicle: StrictBool


class ChroniclePreviewRequest(ChronicleAuthorizationRequest):
    reviewed_evidence: list[ReviewedEvidenceRequest] = Field(
        min_length=1, max_length=MAX_MESSAGES
    )

    @field_validator("reviewed_evidence")
    @classmethod
    def unique_reviewed_evidence(cls, value):
        keys = [(item.thread_id, item.message_id) for item in value]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate reviewed evidence")
        return value


def _history_inspection_principal(request: Request) -> dependencies.RequestUserScope:
    """Compose existing account auth, without local developer identity hints."""
    authorization = request.headers.get("Authorization")
    cookie = request.cookies.get("gc_session")
    key = request.headers.get("X-API-Key")
    remote = dependencies.is_private_preview() or dependencies._auth_mode() == "remote"
    reject_mixed_principal_credentials(
        request,
        enabled=True,
        authorization=authorization,
        gc_session=cookie,
        operator_key_values=(key,) if remote else (),
    )
    if "codexify_hosted_room_session" in request.cookies:
        raise HTTPException(status_code=401, detail="Account authentication required")
    subjects = []
    if cookie:
        subjects.append(resolve_account_session_subject(cookie))
    if authorization:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401, detail="Account authentication required"
            )
        # A configured static key is only the existing local-user credential.
        # Every other session selector needs exact account purpose, even locally.
        if remote or not dependencies._valid_local_api_key_candidate(
            None, authorization
        ):
            subjects.append(resolve_account_session_subject(authorization[7:].strip()))
    if len(set(subjects)) > 1:
        raise HTTPException(status_code=401, detail="Account session mismatch")
    if (
        not remote
        and subjects
        and dependencies._valid_local_api_key_candidate(key, authorization)
    ):
        # A local static key and an account session name different credential
        # contexts. Do not let header precedence silently select the local user.
        raise HTTPException(
            status_code=400, detail="Conflicting authentication contexts"
        )
    dependencies.require_account_session(
        credential=dependencies.verify_account_session(
            request, key, authorization, cookie
        )
    )
    scope = dependencies.get_request_user_scope(
        request=request, x_user_id=None, authorization=authorization, gc_session=cookie
    )
    scope = dependencies.get_account_user_scope(
        _account_gate=None, request_user_scope=scope
    )
    if not scope.user_id or (scope.account_id and scope.account_id != scope.user_id):
        raise HTTPException(status_code=401, detail="Account session mismatch")
    if subjects and (scope.subject_id or scope.user_id) != subjects[0]:
        # In remote single-user mode, legacy scope resolution may fall back to
        # the configured user. That fallback cannot impersonate a signed subject.
        raise HTTPException(status_code=401, detail="Account session mismatch")
    # Static-key local authentication binds to get_single_user_id(), never to
    # X-User-Id, DEBUG, LOCAL_DEV or a client-supplied account field.
    if scope.account_id is None:
        scope = dependencies.RequestUserScope(
            user_id=scope.user_id,
            account_id=scope.user_id,
            subject_id=scope.subject_id,
            multi_user_enabled=scope.multi_user_enabled,
        )
    return scope


def inspect_imported_history(
    body: HistoryInspectionRequest,
    principal: dependencies.RequestUserScope = Depends(_history_inspection_principal),
):
    try:
        connect = getattr(chatlog_db, "_connect", None)
        if not callable(connect):
            raise EvidenceReadError("Canonical database unavailable")
        threads, origins = tuple(body.thread_ids), tuple(body.origins)
        authority = resolve_inspection_access(
            connect,
            principal=principal,
            project_id=body.project_id,
            thread_ids=threads,
            origins=origins,
        )
        evidence = ImportedHistoryEvidenceReader(connect).read(
            principal=principal,
            project_id=body.project_id,
            thread_ids=threads,
            origins=origins,
            authority=authority,
            offset=body.offset,
            limits=InspectionLimits(
                body.max_messages,
                body.max_inspected_messages,
                body.max_excerpt_bytes,
                body.max_response_bytes,
            ),
        )
        return Response(content=evidence.to_json(), media_type="application/json")
    except EvidenceRequestError:
        raise HTTPException(
            status_code=422, detail="Invalid inspection selection"
        ) from None
    except EvidenceAccessError:
        raise HTTPException(
            status_code=404, detail="Selected history unavailable"
        ) from None
    except EvidenceMetadataError:
        raise HTTPException(status_code=409, detail="Unsafe history metadata") from None
    except EvidenceReadError:
        raise HTTPException(
            status_code=503, detail="History inspection unavailable"
        ) from None


router.add_api_route(
    "/api/imports/history/inspect",
    inspect_imported_history,
    methods=["POST"],
    route_class_override=_HistoryInspectionRoute,
)


def preview_chronicle(
    body: ChroniclePreviewRequest,
    principal: dependencies.RequestUserScope = Depends(_history_inspection_principal),
):
    """Generate one ephemeral, cited preview after fresh consumption-time checks."""
    try:
        connect = getattr(chatlog_db, "_connect", None)
        if not callable(connect):
            raise ChroniclePreviewError("Preview unavailable")
        limits = InspectionLimits(
            body.max_messages,
            body.max_inspected_messages,
            body.max_excerpt_bytes,
            body.max_response_bytes,
        )
        grant = authorize_chronicle_interpretation(
            connect,
            principal=principal,
            project_id=body.project_id,
            thread_ids=tuple(body.thread_ids),
            origins=tuple(body.origins),
            limits=limits,
            offset=body.offset,
            purpose=body.purpose,
            interpretation_consent=body.interpretation_consent,
            import_treatment=body.import_treatment,
        )
        authority = resolve_inspection_access(
            connect,
            principal=principal,
            project_id=body.project_id,
            thread_ids=tuple(body.thread_ids),
            origins=tuple(body.origins),
        )
        evidence = ImportedHistoryEvidenceReader(connect).read(
            principal=principal,
            project_id=body.project_id,
            thread_ids=tuple(body.thread_ids),
            origins=tuple(body.origins),
            authority=authority,
            offset=body.offset,
            limits=limits,
        )
        result = generate_chronicle_preview(
            grant,
            evidence,
            tuple(
                ReviewedEvidenceReference(
                    item.thread_id,
                    item.message_id,
                    item.digest,
                    item.approve_for_local_chronicle,
                )
                for item in body.reviewed_evidence
            ),
        )
        return JSONResponse(content=result, media_type="application/json")
    except (ChronicleAuthorizationUnavailable, ChroniclePreviewUnavailable):
        raise HTTPException(
            status_code=503, detail="Chronicle preview unavailable"
        ) from None
    except ChronicleAuthorizationError:
        raise HTTPException(
            status_code=403, detail="Chronicle preview unavailable"
        ) from None
    except (ChroniclePreviewError, EvidenceRequestError):
        raise HTTPException(
            status_code=422, detail="Chronicle preview unavailable"
        ) from None
    except (EvidenceAccessError, EvidenceMetadataError):
        raise HTTPException(
            status_code=403, detail="Chronicle preview unavailable"
        ) from None
    except EvidenceReadError:
        raise HTTPException(
            status_code=503, detail="Chronicle preview unavailable"
        ) from None


router.add_api_route(
    "/api/imports/history/chronicle/preview",
    preview_chronicle,
    methods=["POST"],
    route_class_override=_HistoryInspectionRoute,
)


def check_chronicle_interpretation_authorization(
    body: ChronicleAuthorizationRequest,
    principal: dependencies.RequestUserScope = Depends(_history_inspection_principal),
):
    """Check one bounded request; return no evidence and no reusable token."""
    try:
        connect = getattr(chatlog_db, "_connect", None)
        if not callable(connect):
            raise ChronicleAuthorizationUnavailable("Authorization unavailable")
        grant = authorize_chronicle_interpretation(
            connect,
            principal=principal,
            project_id=body.project_id,
            thread_ids=tuple(body.thread_ids),
            origins=tuple(body.origins),
            limits=InspectionLimits(
                body.max_messages,
                body.max_inspected_messages,
                body.max_excerpt_bytes,
                body.max_response_bytes,
            ),
            offset=body.offset,
            purpose=body.purpose,
            interpretation_consent=body.interpretation_consent,
            import_treatment=body.import_treatment,
        )
        # Deliberately project only scope confirmation; the grant is discarded
        # with this call and cannot be presented to a later request.
        return JSONResponse(
            content={
                "authorized": True,
                "scope": {
                    "project_id": grant.project_id,
                    "thread_ids": list(grant.thread_ids),
                    "origins": [origin.value for origin in grant.origins],
                    "max_messages": grant.limits.max_messages,
                    "max_inspected_messages": grant.limits.max_inspected_messages,
                    "max_excerpt_bytes": grant.limits.max_excerpt_bytes,
                    "max_response_bytes": grant.limits.max_response_bytes,
                    "offset": grant.offset,
                    "purpose": grant.purpose,
                    "import_treatment": grant.import_treatment,
                },
            },
            media_type="application/json",
        )
    except EvidenceRequestError:
        raise HTTPException(
            status_code=422, detail="Invalid inspection selection"
        ) from None
    except ChronicleAuthorizationError as exc:
        status = 503 if isinstance(exc, ChronicleAuthorizationUnavailable) else 403
        raise HTTPException(
            status_code=status,
            detail=(
                "Interpretation authorization unavailable"
                if status == 503
                else "Interpretation authorization denied"
            ),
        ) from None


router.add_api_route(
    "/api/imports/history/chronicle/authorization-check",
    check_chronicle_interpretation_authorization,
    methods=["POST"],
    route_class_override=_HistoryInspectionRoute,
)


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
            service.finalize_job, job_id=job_id, user_id=user_id
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
        return await run_in_threadpool(service.get_job, job_id=job_id, user_id=user_id)
    except AccountImportError as exc:
        _raise_account_import_error(exc)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/imports/openai-account/{job_id}/retry")
async def retry_openai_account_import(
    job_id: str,
    user_id: str = Depends(get_request_user_id),
    api_key: str = Depends(require_api_key),
):
    """Retry a failed zero-write account import after verifying staging continuity."""

    _ = api_key
    try:
        service = await run_in_threadpool(_get_account_import_service)
        result = await run_in_threadpool(
            service.retry_failed_account_import,
            job_id=job_id,
            user_id=user_id,
        )
        return JSONResponse(status_code=202, content=result)
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
        return JSONResponse(status_code=error.status_code, content=error.to_payload())

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
        return JSONResponse(status_code=exc.status_code, content=exc.to_payload())
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
        return JSONResponse(status_code=error.status_code, content=error.to_payload())


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
            raise ValueError("Invalid JSON file: unable to parse uploaded content.")

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


@router.post("/api/retry-chatgpt-import-embeddings", response_model=EmbeddingRetryStats)
@router.post("/retry-chatgpt-import-embeddings", response_model=EmbeddingRetryStats)
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
