"""
Media & TTS API routes for Codexify.

Handles:
- Image uploads (user-uploaded)
- Document uploads (user-uploaded)
- Image generation tracking (AI-generated)
- Document generation tracking (AI-generated)
- TTS synthesis and tracking
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.default_project import (
    DEFAULT_PROJECT_NAME,
    canonicalize_default_project,
    is_default_project_name,
)
from guardian.core.dependencies import (
    RequestUserScope,
    get_request_user_scope,
    get_single_user_id,
    verify_api_key,
)
from guardian.core.media_signing import extract_media_path, sign_media_url
from guardian.core.storage import create_storage_from_env
from guardian.db.models import (
    ChatThread,
    GeneratedDocument,
    GeneratedImage,
    MediaAsset,
    Project,
    ProjectDocumentLink,
    ThreadDocument,
    TTSOutput,
    UploadedDocument,
    UploadedImage,
)
from guardian.image_gen.router import ImageGenRouter
from guardian.queue.document_embed_queue import enqueue_document_embed
from guardian.services.document_parsers import (
    DocxTextExtractionError,
    PdfTextExtractionError,
    extract_docx_text,
    extract_pdf_text,
)
from guardian.services.media_identity import (
    compute_content_hash,
    compute_identity,
    display_title_for_asset,
    ensure_asset_alias,
    find_existing_asset,
    find_first_seen_timestamp,
)
from guardian.services.media_identity import (
    resolve_asset as resolve_asset_from_aliases,
)
from guardian.services.media_identity import source_label_from_filename, utcnow
from guardian.protocol_tokens import EmbeddingLifecycleStatus

logger = logging.getLogger(__name__)
_TRUTHY_VALUES = {"1", "true", "yes", "on"}
_GENERIC_UPLOAD_ERROR = "Upload failed. Please try again."
_IMAGE_THREAD_ID_REQUIRED_ERROR = "thread_id_required"
_IMAGE_THREAD_ID_REQUIRED_MESSAGE = "thread_id is required for image uploads."


def _is_pytest() -> bool:
    return "pytest" in sys.modules or os.getenv("PYTEST_CURRENT_TEST")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in _TRUTHY_VALUES


def _media_feature_enabled(flag_name: str) -> bool:
    if _env_bool("CODEXIFY_BETA_CORE_ONLY", default=False):
        return False
    return _env_bool(flag_name, default=True)


def _require_media_feature(flag_name: str, feature_label: str) -> None:
    if _media_feature_enabled(flag_name):
        return
    logger.warning("[media] %s quarantined (flag=%s)", feature_label, flag_name)
    raise HTTPException(status_code=404, detail="Not Found")


def _require_media_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    if _is_pytest() and not x_api_key and not authorization:
        return "test-bypass"
    return verify_api_key(
        request=request, x_api_key=x_api_key, authorization=authorization
    )


router = APIRouter(dependencies=[Depends(_require_media_api_key)])

# Initialize storage manager
storage = create_storage_from_env()


# =========================
# Pydantic Models
# =========================


class ImageUploadResponse(BaseModel):
    id: str
    src_url: str
    filename: str
    filesize: int
    mime_type: str
    media_kind: str = Field(default="image")
    source_tag: Optional[str] = None
    created_at: str


class DocumentUploadResponse(BaseModel):
    id: str
    document_id: str
    media_asset_id: str | None = None
    project_id: int
    thread_id: Optional[int] = None
    src_url: str
    filename: str
    filesize: int
    mime_type: str
    source_tag: Optional[str] = None
    parsed_text: Optional[str] = None
    embedding_status: Optional[str] = None
    embedding_error: Optional[str] = None
    embedding_started_at: Optional[str] = None
    embedding_completed_at: Optional[str] = None
    created_at: str


class DocumentDetailResponse(BaseModel):
    id: str
    document_id: str
    media_asset_id: str | None = None
    project_id: int
    thread_id: Optional[int] = None
    src_url: str
    filename: str
    filesize: int
    mime_type: str
    source_tag: Optional[str] = None
    content: Optional[str] = None
    parsed_text: Optional[str] = None
    embedding_status: Optional[str] = None
    embedding_error: Optional[str] = None
    embedding_started_at: Optional[str] = None
    embedding_completed_at: Optional[str] = None
    created_at: str


class DocumentArtifactResponse(BaseModel):
    """A document artifact projected for the Documents workspace."""

    id: str
    document_id: str
    artifact_type: str
    title: str
    filename: str | None = None
    format: str | None = None
    project_id: int | None = None
    thread_id: int | None = None
    thread_ids: list[int] = Field(default_factory=list)
    thread_title: str | None = None
    thread_titles: list[str] = Field(default_factory=list)
    relation: str | None = None
    relations: list[str] = Field(default_factory=list)
    src_url: str | None = None
    filesize: int | None = None
    mime_type: str | None = None
    source_tag: str | None = None
    embedding_status: str | None = None
    embedding_error: str | None = None
    embedding_started_at: str | None = None
    embedding_completed_at: str | None = None
    created_at: str | None = None


class DocumentArtifactListResponse(BaseModel):
    documents: list[DocumentArtifactResponse]
    count: int


class DocumentArtifactDetailResponse(DocumentArtifactResponse):
    """A document artifact with previewable content when available."""

    media_asset_id: str | None = None
    content: str | None = None
    parsed_text: str | None = None


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt for image generation")
    model: str = Field(default="dall-e-3", description="Model to use")
    project_id: Optional[int] = None
    thread_id: Optional[int] = None
    user_id: str = Field(default="default")


class ImageGenerationResponse(BaseModel):
    id: str
    src_url: str
    prompt: str
    model: str
    created_at: str


class TTSSynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    voice: Optional[str] = Field(None, description="Voice ID")
    provider: Optional[str] = Field(
        None, description="TTS provider (elevenlabs, google, local)"
    )
    project_id: Optional[int] = None
    thread_id: Optional[int] = None
    user_id: Optional[str] = None


class TTSOutputResponse(BaseModel):
    id: int
    src_url: Optional[str]
    text: str
    voice: Optional[str]
    provider: Optional[str]
    duration_seconds: Optional[float]
    created_at: str


class MediaResolveResponse(BaseModel):
    asset_id: str
    src_url: str
    display_title: str
    media_kind: str
    provenance: str
    source_tag: str
    created_at: str
    ingested_at: str


# =========================
# Helper Functions
# =========================


def _get_db() -> GuardianDB:
    """Get the Guardian media database connection.

    Media routes require a SQLAlchemy session (via GuardianDB.get_session). In
    some parts of the codebase there are other DB-like adapters (e.g.
    PostgresChatLogDB) that do not expose `get_session()`. This helper must
    *always* return a GuardianDB instance.
    """

    resolved = load_guardian_db_from_env()

    # Be defensive: if env loading returns a DB-like adapter that does not
    # support SQLAlchemy sessions, ignore it and fall back to GuardianDB.
    if resolved is not None:
        if isinstance(resolved, GuardianDB):
            return resolved
        if hasattr(resolved, "get_session"):
            # Some older call sites may return a compatible object; accept it.
            return resolved  # type: ignore[return-value]
        logger.error(
            "load_guardian_db_from_env() returned incompatible db type for media routes: %s",
            type(resolved),
        )

    db_url = os.getenv("DATABASE_URL") or DEFAULT_PG_DSN
    return GuardianDB(db_url)


def _normalize_source_tag(tag: Optional[str], source_tag: Optional[str]) -> str:
    """Normalize incoming tag values for media records."""
    candidate = (tag or source_tag or "uploaded").strip().lower()
    return candidate or "uploaded"


_PROJECT_OWNER_SENTINEL = "__codexify_project_owner__"


def _request_account_id(request_user_scope: RequestUserScope) -> str:
    account_id = str(
        getattr(request_user_scope, "account_id", "") or ""
    ).strip()
    return account_id or get_single_user_id()


def _is_multi_user_scope(request_user_scope: RequestUserScope) -> bool:
    return bool(getattr(request_user_scope, "multi_user_enabled", False))


def _resolve_effective_user_id(
    raw_user_id: str | None,
    request_user_scope: RequestUserScope,
    *,
    default_when_blank: str | None = None,
) -> str | None:
    requested_user_id = str(raw_user_id or "").strip()
    if requested_user_id.lower() == "default":
        requested_user_id = ""
    if _is_multi_user_scope(request_user_scope):
        account_id = _request_account_id(request_user_scope)
        if requested_user_id and requested_user_id != account_id:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Requested user_id does not match the authenticated account"
                ),
            )
        return account_id
    return requested_user_id or default_when_blank


def _row_value(row: Any, field: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(field)
    return getattr(row, field, None)


def _decode_project_description(description: Any) -> tuple[str | None, str]:
    text = str(description or "")
    if not text:
        return None, ""

    try:
        payload = json.loads(text)
    except Exception:
        return None, text

    if not isinstance(payload, dict) or not payload.get(
        _PROJECT_OWNER_SENTINEL
    ):
        return None, text

    owner_id = str(payload.get("owner_user_id") or "").strip() or None
    decoded_description = str(payload.get("description") or "")
    return owner_id, decoded_description


def _normalize_project_row(project: Any) -> dict[str, Any]:
    row = dict(project or {})
    owner_id = str(row.get("owner_user_id") or row.get("user_id") or "").strip()
    decoded_owner_id, description = _decode_project_description(
        row.get("description")
    )
    if decoded_owner_id:
        owner_id = decoded_owner_id
    if owner_id:
        row["description"] = description
        row["owner_user_id"] = owner_id
    return row


def _project_owner_id(project: Any) -> str:
    row = _normalize_project_row(project)
    return str(row.get("owner_user_id") or row.get("user_id") or "").strip()


def _project_is_visible_to_scope(
    project: Any,
    request_user_scope: RequestUserScope,
) -> bool:
    if not _is_multi_user_scope(request_user_scope):
        return True

    account_id = _request_account_id(request_user_scope)
    row = _normalize_project_row(project)
    owner_id = str(row.get("owner_user_id") or row.get("user_id") or "").strip()
    if owner_id:
        return owner_id == account_id
    return is_default_project_name(str(row.get("name") or ""))


def _get_project_record(db, project_id: int) -> dict[str, Any] | None:
    projects: list[dict[str, Any]] = []
    if hasattr(db, "list_projects"):
        try:
            projects = db.list_projects() or []
        except Exception:
            projects = []
    if not projects and hasattr(db, "get_session"):
        try:
            with db.get_session() as session:
                rows = session.query(Project).all()
                projects = [_normalize_project_row(row) for row in rows]
        except Exception:
            projects = []

    for project in projects:
        row = _normalize_project_row(project)
        try:
            row_id = int(row.get("id"))
        except (TypeError, ValueError):
            continue
        if row_id == int(project_id):
            return row
    return None


def _require_project_account_scope(
    db,
    project_id: int,
    request_user_scope: RequestUserScope,
) -> dict[str, Any]:
    project = _get_project_record(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if _is_multi_user_scope(request_user_scope):
        account_id = _request_account_id(request_user_scope)
        owner_id = str(
            project.get("owner_user_id") or project.get("user_id") or ""
        ).strip()
        if owner_id and owner_id != account_id:
            raise HTTPException(
                status_code=403,
                detail=("Project does not belong to the authenticated account"),
            )
        if not owner_id and not is_default_project_name(
            str(project.get("name") or "")
        ):
            raise HTTPException(
                status_code=403,
                detail=("Project does not belong to the authenticated account"),
            )

    return project


def _require_thread_account_scope(
    db,
    thread_id: int,
    request_user_scope: RequestUserScope,
) -> Any:
    try:
        with db.get_session() as session:
            thread = (
                session.query(ChatThread)
                .filter(ChatThread.id == thread_id)
                .first()
            )
    except Exception:
        thread = None

    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    if _is_multi_user_scope(request_user_scope):
        account_id = _request_account_id(request_user_scope)
        owner_id = str(_row_value(thread, "user_id") or "").strip()
        if owner_id != account_id:
            raise HTTPException(
                status_code=403,
                detail=("Thread does not belong to the authenticated account"),
            )

    return thread


def _media_row_is_owned_by_scope(
    row: Any,
    request_user_scope: RequestUserScope,
) -> bool:
    if not _is_multi_user_scope(request_user_scope):
        return True
    account_id = _request_account_id(request_user_scope)
    owner_id = str(_row_value(row, "user_id") or "").strip()
    return owner_id == account_id


def _require_uploaded_image_account_scope(
    db,
    image_id: str,
    request_user_scope: RequestUserScope,
) -> UploadedImage:
    with db.get_session() as session:
        image = session.query(UploadedImage).filter_by(id=image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    if not _media_row_is_owned_by_scope(image, request_user_scope):
        raise HTTPException(
            status_code=403,
            detail="Image does not belong to the authenticated account",
        )
    return image


def _require_generated_image_account_scope(
    db,
    image_id: str,
    request_user_scope: RequestUserScope,
) -> GeneratedImage:
    with db.get_session() as session:
        image = session.query(GeneratedImage).filter_by(id=image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    if not _media_row_is_owned_by_scope(image, request_user_scope):
        raise HTTPException(
            status_code=403,
            detail="Image does not belong to the authenticated account",
        )
    return image


def _require_uploaded_document_account_scope(
    db,
    document_identity: str,
    request_user_scope: RequestUserScope,
) -> UploadedDocument:
    identity = str(document_identity or "").strip()
    if not identity:
        raise HTTPException(status_code=404, detail="Document not found")

    with db.get_session() as session:
        document = (
            session.query(UploadedDocument)
            .filter(
                UploadedDocument.deleted_at.is_(None),
                or_(
                    UploadedDocument.id == identity,
                    UploadedDocument.asset_id == identity,
                ),
            )
            .order_by(
                (UploadedDocument.id == identity).desc(),
                UploadedDocument.created_at.desc(),
            )
            .first()
        )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not _media_row_is_owned_by_scope(document, request_user_scope):
        raise HTTPException(
            status_code=403,
            detail="Document does not belong to the authenticated account",
        )
    return document


def _require_tts_account_scope(
    db,
    tts_id: int,
    request_user_scope: RequestUserScope,
) -> TTSOutput:
    with db.get_session() as session:
        tts_output = session.query(TTSOutput).filter_by(id=tts_id).first()
    if not tts_output:
        raise HTTPException(status_code=404, detail="Audio not found")
    if not _media_row_is_owned_by_scope(tts_output, request_user_scope):
        raise HTTPException(
            status_code=403,
            detail="Audio does not belong to the authenticated account",
        )
    return tts_output


def _asset_visible_to_scope(
    db,
    session,
    asset: MediaAsset,
    request_user_scope: RequestUserScope,
) -> bool:
    if not _is_multi_user_scope(request_user_scope):
        return True

    account_id = _request_account_id(request_user_scope)
    asset_owner = str(_row_value(asset, "user_id") or "").strip()
    if asset_owner == account_id:
        return True

    asset_id = str(_row_value(asset, "id") or "").strip()
    if not asset_id:
        return False

    for model in (UploadedImage, UploadedDocument, GeneratedImage):
        visible = (
            session.query(model)
            .filter_by(asset_id=asset_id, user_id=account_id)
            .first()
        )
        if visible is not None:
            return True

    return False


def _signed_src_url(src_url: str | None) -> str:
    return sign_media_url((src_url or "").strip())


def _storage_src_path(src_url: str | None) -> str:
    return extract_media_path((src_url or "").strip())


def _compute_identity_with_existing_asset(
    *,
    session,
    project_id: int,
    media_kind: str,
    provenance: str,
    file_data: bytes,
    human_label: str,
    original_filename: str | None,
    mime_type: str | None,
):
    content_hash = compute_content_hash(file_data)
    first_seen_at = find_first_seen_timestamp(
        session,
        project_id=project_id,
        media_kind=media_kind,
        provenance=provenance,
        content_hash=content_hash,
        fallback=utcnow(),
    )
    identity = compute_identity(
        file_data=file_data,
        media_kind=media_kind,
        provenance=provenance,
        human_label=human_label,
        original_filename=original_filename,
        mime_type=mime_type,
        first_seen_at=first_seen_at,
        content_hash=content_hash,
    )
    existing_asset = find_existing_asset(
        session,
        project_id=project_id,
        media_kind=media_kind,
        provenance=provenance,
        content_hash=content_hash,
    )
    return identity, existing_asset


def _coerce_optional_positive_int(value: int | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _upload_error_detail(code: str, message: str) -> dict[str, str]:
    return {"error": code, "message": message}


def _request_id_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return str(request_id)
    header_id = request.headers.get("X-Request-ID")
    if header_id:
        return str(header_id)
    return None


def _extract_constraint_name(exc: BaseException) -> str | None:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name:
        return str(constraint_name)
    return None


def _log_upload_failure(
    *,
    route: str,
    request: Request | None,
    exc: BaseException,
    project_id: int | None,
    thread_id: int | None,
) -> None:
    logger.exception(
        "[media] upload_failed route=%s request_id=%s thread_id=%s project_id=%s constraint=%s error_class=%s",
        route,
        _request_id_from_request(request),
        thread_id,
        project_id,
        _extract_constraint_name(exc),
        exc.__class__.__name__,
    )


def _resolve_upload_context(
    db, incoming_project_id: int | None, thread_id: int | None = None
) -> tuple[int, int | None]:
    explicit_project_id = _coerce_optional_positive_int(incoming_project_id)
    normalized_thread_id = _coerce_optional_positive_int(thread_id)

    thread = None
    try:
        with db.get_session() as session:
            if normalized_thread_id is not None:
                thread = (
                    session.query(ChatThread)
                    .filter(ChatThread.id == normalized_thread_id)
                    .first()
                )
                if thread is None:
                    raise HTTPException(
                        status_code=400,
                        detail=_upload_error_detail(
                            "invalid_thread_id",
                            "Invalid thread reference.",
                        ),
                    )

            if explicit_project_id is not None:
                project = (
                    session.query(Project)
                    .filter(Project.id == explicit_project_id)
                    .first()
                )
                if project is None:
                    raise HTTPException(
                        status_code=400,
                        detail=_upload_error_detail(
                            "invalid_project_id",
                            "Invalid project reference.",
                        ),
                    )
                return explicit_project_id, normalized_thread_id
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.debug(
            "[media] Failed to resolve upload context for thread=%s project=%s: %s",
            normalized_thread_id,
            explicit_project_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail=_upload_error_detail("upload_failed", _GENERIC_UPLOAD_ERROR),
        ) from exc

    thread_project_id = _coerce_optional_positive_int(
        getattr(thread, "project_id", None)
    )
    if thread_project_id is not None:
        return thread_project_id, normalized_thread_id

    fallback_project_id = canonicalize_default_project(db, logger=logger)
    fallback_project_id = _coerce_optional_positive_int(fallback_project_id)
    if fallback_project_id is None:
        raise HTTPException(
            status_code=500,
            detail=_upload_error_detail("upload_failed", _GENERIC_UPLOAD_ERROR),
        )
    return fallback_project_id, normalized_thread_id


def _resolve_document_project_id(
    db, incoming_project_id: int | None, thread_id: int | None = None
) -> int:
    resolved_project_id, _resolved_thread_id = _resolve_upload_context(
        db, incoming_project_id, thread_id
    )
    return resolved_project_id


def _create_media_asset(
    *,
    session,
    project_id: int,
    thread_id: int | None,
    user_id: str | None,
    media_kind: str,
    provenance: str,
    source_tag: str,
    src_url: str,
    mime_type: str | None,
    filesize: int | None,
    identity,
) -> MediaAsset:
    asset = MediaAsset(
        id=str(uuid.uuid4()),
        project_id=project_id,
        thread_id=thread_id,
        user_id=user_id,
        media_kind=media_kind,
        provenance=provenance,
        source_tag=source_tag,
        content_hash=identity.content_hash,
        deterministic_id=identity.deterministic_id,
        normalized_slug=identity.normalized_slug,
        system_name=identity.system_name,
        storage_prefix=identity.storage_prefix,
        src_url=src_url,
        mime_type=mime_type,
        filesize=filesize,
    )
    session.add(asset)
    # Ensure the asset row is flushed so FK-dependent inserts (e.g., media_aliases)
    # can safely reference it before the transaction is committed.
    session.flush()
    return asset


def _find_uploaded_image_for_asset(
    session, asset_id: str
) -> UploadedImage | None:
    return (
        session.query(UploadedImage)
        .filter(
            UploadedImage.asset_id == asset_id,
            UploadedImage.deleted_at.is_(None),
        )
        .order_by(UploadedImage.created_at.desc())
        .first()
    )


def _find_uploaded_document_for_asset(
    session, asset_id: str
) -> UploadedDocument | None:
    return (
        session.query(UploadedDocument)
        .filter(
            UploadedDocument.asset_id == asset_id,
            UploadedDocument.deleted_at.is_(None),
        )
        .order_by(UploadedDocument.created_at.desc())
        .first()
    )


def _ensure_thread_document_link(
    session,
    *,
    thread_id: int | None,
    document_id: str,
    relation: str = "attached",
) -> bool:
    normalized_thread_id = _coerce_optional_positive_int(thread_id)
    normalized_document_id = str(document_id or "").strip()
    if normalized_thread_id is None or not normalized_document_id:
        return False

    existing_link = (
        session.query(ThreadDocument)
        .filter_by(
            thread_id=normalized_thread_id,
            document_id=normalized_document_id,
            relation=relation,
        )
        .first()
    )
    if existing_link is not None:
        return False

    session.add(
        ThreadDocument(
            thread_id=normalized_thread_id,
            document_id=normalized_document_id,
            relation=relation,
        )
    )
    return True


def _ensure_project_document_link(
    session,
    *,
    project_id: int | None,
    document_id: str,
    document_type: str = "uploaded",
    attached_by: str | None = None,
) -> bool:
    normalized_project_id = _coerce_optional_positive_int(project_id)
    normalized_document_id = str(document_id or "").strip()
    normalized_document_type = str(document_type or "uploaded").strip().lower()
    if normalized_document_type.startswith("gen"):
        normalized_document_type = "generated"
    else:
        normalized_document_type = "uploaded"

    if normalized_project_id is None or not normalized_document_id:
        return False

    existing_link = (
        session.query(ProjectDocumentLink)
        .filter_by(
            project_id=normalized_project_id,
            document_id=normalized_document_id,
            document_type=normalized_document_type,
        )
        .first()
    )
    if existing_link is not None:
        updated = False
        if existing_link.is_enabled is False:
            existing_link.is_enabled = True
            updated = True
        if (
            attached_by
            and getattr(existing_link, "attached_by", None) != attached_by
        ):
            existing_link.attached_by = attached_by
            updated = True
        return updated

    session.add(
        ProjectDocumentLink(
            project_id=normalized_project_id,
            document_id=normalized_document_id,
            document_type=normalized_document_type,
            attached_by=attached_by,
        )
    )
    return True


def _document_upload_response_from_row(
    document: UploadedDocument,
    *,
    fallback_project_id: int,
    requested_thread_id: int | None,
) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        id=document.id,
        document_id=document.id,
        media_asset_id=document.asset_id,
        project_id=int(document.project_id or fallback_project_id),
        thread_id=(
            requested_thread_id
            if requested_thread_id is not None
            else document.thread_id
        ),
        src_url=_signed_src_url(document.src_url),
        filename=document.filename,
        filesize=document.filesize,
        mime_type=document.mime_type,
        source_tag=document.source_tag,
        parsed_text=document.parsed_text,
        embedding_status=document.embedding_status,
        embedding_error=document.embedding_error,
        embedding_started_at=(
            document.embedding_started_at.isoformat()
            if document.embedding_started_at
            else None
        ),
        embedding_completed_at=(
            document.embedding_completed_at.isoformat()
            if document.embedding_completed_at
            else None
        ),
        created_at=(
            document.created_at.isoformat()
            if document.created_at
            else datetime.now(timezone.utc).isoformat()
        ),
    )


def _document_detail_response_from_row(
    document: UploadedDocument,
    *,
    fallback_project_id: int,
) -> DocumentDetailResponse:
    return DocumentDetailResponse(
        id=document.id,
        document_id=document.id,
        media_asset_id=document.asset_id,
        project_id=int(document.project_id or fallback_project_id),
        thread_id=document.thread_id,
        src_url=_signed_src_url(document.src_url),
        filename=document.filename,
        filesize=document.filesize,
        mime_type=document.mime_type,
        source_tag=document.source_tag,
        content=document.parsed_text,
        parsed_text=document.parsed_text,
        embedding_status=document.embedding_status,
        embedding_error=document.embedding_error,
        embedding_started_at=(
            document.embedding_started_at.isoformat()
            if document.embedding_started_at
            else None
        ),
        embedding_completed_at=(
            document.embedding_completed_at.isoformat()
            if document.embedding_completed_at
            else None
        ),
        created_at=(
            document.created_at.isoformat()
            if document.created_at
            else datetime.now(timezone.utc).isoformat()
        ),
    )


def _find_generated_image_for_asset(
    session, asset_id: str
) -> GeneratedImage | None:
    return (
        session.query(GeneratedImage)
        .filter(
            GeneratedImage.asset_id == asset_id,
            GeneratedImage.deleted_at.is_(None),
        )
        .order_by(GeneratedImage.created_at.desc())
        .first()
    )


# =========================
# Image Upload Routes
# =========================


@router.post(
    "/upload/image", response_model=ImageUploadResponse, tags=["media"]
)
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(default=None),
    thread_id: Optional[int] = Form(default=None),
    user_id: str = Form(default="default"),
    tag: Optional[str] = Form(default=None),
    source_tag: Optional[str] = Form(default=None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Upload an image file.

    Accepts: PNG, JPG, JPEG, WebP
    Stores in: /media/images/
    """
    normalized_thread_id = _coerce_optional_positive_int(thread_id)
    if normalized_thread_id is None:
        raise HTTPException(
            status_code=422,
            detail=_upload_error_detail(
                _IMAGE_THREAD_ID_REQUIRED_ERROR,
                _IMAGE_THREAD_ID_REQUIRED_MESSAGE,
            ),
        )

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, detail=f"Invalid file type: {file.content_type}"
        )

    try:
        # Read file data
        file_data = await file.read()
        filesize = len(file_data)
        filename = file.filename or "upload"
        effective_tag = _normalize_source_tag(tag, source_tag)
        effective_user_id = _resolve_effective_user_id(
            user_id,
            request_user_scope,
            default_when_blank=_request_account_id(request_user_scope),
        )
        human_label = source_label_from_filename(
            filename, fallback="uploaded-image"
        )
        db = _get_db()
        explicit_project_id = _coerce_optional_positive_int(project_id)
        explicit_thread_id = normalized_thread_id
        if explicit_project_id is not None:
            _require_project_account_scope(
                db, explicit_project_id, request_user_scope
            )
        _require_thread_account_scope(
            db, explicit_thread_id, request_user_scope
        )
        resolved_project_id, resolved_thread_id = _resolve_upload_context(
            db, project_id, thread_id
        )

        # First pass: dedupe before any storage write.
        with db.get_session() as session:
            identity, existing_asset = _compute_identity_with_existing_asset(
                session=session,
                project_id=resolved_project_id,
                media_kind="image",
                provenance="uploaded",
                file_data=file_data,
                human_label=human_label,
                original_filename=filename,
                mime_type=file.content_type,
            )
            if existing_asset:
                ensure_asset_alias(
                    session,
                    asset_id=existing_asset.id,
                    alias=filename,
                    alias_type="original_name",
                )
                existing = _find_uploaded_image_for_asset(
                    session, existing_asset.id
                )
                if existing and _media_row_is_owned_by_scope(
                    existing, request_user_scope
                ):
                    if not existing.source_tag:
                        existing.source_tag = effective_tag
                    session.commit()
                    return ImageUploadResponse(
                        id=existing.id,
                        src_url=_signed_src_url(existing.src_url),
                        filename=existing.filename,
                        filesize=existing.filesize,
                        mime_type=existing.mime_type,
                        source_tag=existing.source_tag,
                        created_at=(
                            existing.created_at.isoformat()
                            if existing.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    )

                # Backfill link for legacy content when asset exists but origin row does not.
                linked_image = UploadedImage(
                    id=str(uuid.uuid4()),
                    asset_id=existing_asset.id,
                    project_id=resolved_project_id,
                    thread_id=resolved_thread_id,
                    user_id=effective_user_id,
                    src_url=existing_asset.src_url,
                    filename=filename,
                    filesize=filesize or (existing_asset.filesize or 0),
                    mime_type=file.content_type
                    or existing_asset.mime_type
                    or "image/png",
                    source_tag=effective_tag,
                )
                session.add(linked_image)
                session.commit()
                return ImageUploadResponse(
                    id=linked_image.id,
                    src_url=_signed_src_url(linked_image.src_url),
                    filename=linked_image.filename,
                    filesize=linked_image.filesize,
                    mime_type=linked_image.mime_type,
                    source_tag=linked_image.source_tag,
                    created_at=(
                        linked_image.created_at.isoformat()
                        if linked_image.created_at
                        else datetime.now(timezone.utc).isoformat()
                    ),
                )

        canonical_path = f"{identity.storage_prefix}{identity.system_name}"

        # Upload to storage
        src_url = storage.upload_file(
            file_data, canonical_path, content_type=file.content_type
        )

        image_id = str(uuid.uuid4())  # Origin row ID

        # Second pass: create asset + origin row, tolerate races.
        with db.get_session() as session:
            try:
                (
                    identity,
                    existing_asset,
                ) = _compute_identity_with_existing_asset(
                    session=session,
                    project_id=resolved_project_id,
                    media_kind="image",
                    provenance="uploaded",
                    file_data=file_data,
                    human_label=human_label,
                    original_filename=filename,
                    mime_type=file.content_type,
                )
                if existing_asset:
                    ensure_asset_alias(
                        session,
                        asset_id=existing_asset.id,
                        alias=filename,
                        alias_type="original_name",
                    )
                    existing = _find_uploaded_image_for_asset(
                        session, existing_asset.id
                    )
                    if existing and _media_row_is_owned_by_scope(
                        existing, request_user_scope
                    ):
                        if not existing.source_tag:
                            existing.source_tag = effective_tag
                        session.commit()
                        return ImageUploadResponse(
                            id=existing.id,
                            src_url=_signed_src_url(existing.src_url),
                            filename=existing.filename,
                            filesize=existing.filesize,
                            mime_type=existing.mime_type,
                            source_tag=existing.source_tag,
                            created_at=(
                                existing.created_at.isoformat()
                                if existing.created_at
                                else datetime.now(timezone.utc).isoformat()
                            ),
                        )
                    linked_image = UploadedImage(
                        id=image_id,
                        asset_id=existing_asset.id,
                        project_id=resolved_project_id,
                        thread_id=resolved_thread_id,
                        user_id=effective_user_id,
                        src_url=existing_asset.src_url,
                        filename=filename,
                        filesize=filesize or (existing_asset.filesize or 0),
                        mime_type=file.content_type
                        or existing_asset.mime_type
                        or "image/png",
                        source_tag=effective_tag,
                    )
                    session.add(linked_image)
                    session.commit()
                    return ImageUploadResponse(
                        id=linked_image.id,
                        src_url=_signed_src_url(linked_image.src_url),
                        filename=linked_image.filename,
                        filesize=linked_image.filesize,
                        mime_type=linked_image.mime_type,
                        source_tag=linked_image.source_tag,
                        created_at=(
                            linked_image.created_at.isoformat()
                            if linked_image.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    )

                asset = _create_media_asset(
                    session=session,
                    project_id=resolved_project_id,
                    thread_id=resolved_thread_id,
                    user_id=effective_user_id,
                    media_kind="image",
                    provenance="uploaded",
                    source_tag=effective_tag,
                    src_url=src_url,
                    mime_type=file.content_type,
                    filesize=filesize,
                    identity=identity,
                )
                ensure_asset_alias(
                    session,
                    asset_id=asset.id,
                    alias=filename,
                    alias_type="original_name",
                )
                uploaded_image = UploadedImage(
                    id=image_id,
                    asset_id=asset.id,
                    project_id=resolved_project_id,
                    thread_id=resolved_thread_id,
                    user_id=effective_user_id,
                    src_url=src_url,
                    filename=filename,
                    filesize=filesize,
                    mime_type=file.content_type or "image/png",
                    source_tag=effective_tag,
                )
                session.add(uploaded_image)
                session.commit()
            except IntegrityError:
                session.rollback()
                (
                    identity,
                    existing_asset,
                ) = _compute_identity_with_existing_asset(
                    session=session,
                    project_id=resolved_project_id,
                    media_kind="image",
                    provenance="uploaded",
                    file_data=file_data,
                    human_label=human_label,
                    original_filename=filename,
                    mime_type=file.content_type,
                )
                if existing_asset:
                    ensure_asset_alias(
                        session,
                        asset_id=existing_asset.id,
                        alias=filename,
                        alias_type="original_name",
                    )
                    existing = _find_uploaded_image_for_asset(
                        session, existing_asset.id
                    )
                    if existing and _media_row_is_owned_by_scope(
                        existing, request_user_scope
                    ):
                        session.commit()
                        return ImageUploadResponse(
                            id=existing.id,
                            src_url=_signed_src_url(existing.src_url),
                            filename=existing.filename,
                            filesize=existing.filesize,
                            mime_type=existing.mime_type,
                            source_tag=existing.source_tag,
                            created_at=(
                                existing.created_at.isoformat()
                                if existing.created_at
                                else datetime.now(timezone.utc).isoformat()
                            ),
                        )
                    linked_image = UploadedImage(
                        id=str(uuid.uuid4()),
                        asset_id=existing_asset.id,
                        project_id=resolved_project_id,
                        thread_id=resolved_thread_id,
                        user_id=effective_user_id,
                        src_url=existing_asset.src_url,
                        filename=filename,
                        filesize=filesize or (existing_asset.filesize or 0),
                        mime_type=file.content_type
                        or existing_asset.mime_type
                        or "image/png",
                        source_tag=effective_tag,
                    )
                    session.add(linked_image)
                    session.commit()
                    return ImageUploadResponse(
                        id=linked_image.id,
                        src_url=_signed_src_url(linked_image.src_url),
                        filename=linked_image.filename,
                        filesize=linked_image.filesize,
                        mime_type=linked_image.mime_type,
                        source_tag=linked_image.source_tag,
                        created_at=(
                            linked_image.created_at.isoformat()
                            if linked_image.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    )
                raise

        logger.info(
            "Image uploaded: %s (%s bytes) by user %s project_id=%s thread_id=%s",
            filename,
            filesize,
            effective_user_id,
            resolved_project_id,
            resolved_thread_id,
        )

        return ImageUploadResponse(
            id=image_id,
            src_url=_signed_src_url(src_url),
            filename=filename,
            filesize=filesize,
            mime_type=file.content_type,
            source_tag=effective_tag,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as exc:
        _log_upload_failure(
            route="/api/media/upload/image",
            request=request,
            exc=exc,
            project_id=_coerce_optional_positive_int(project_id),
            thread_id=_coerce_optional_positive_int(thread_id),
        )
        raise HTTPException(
            status_code=500,
            detail=_upload_error_detail("upload_failed", _GENERIC_UPLOAD_ERROR),
        ) from exc


@router.get("/images/{image_id}", tags=["media"])
async def get_image(
    image_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Get an uploaded image by ID."""
    db = _get_db()

    image = _require_uploaded_image_account_scope(
        db, image_id, request_user_scope
    )

    # Download from storage
    try:
        file_data = storage.download_file(_storage_src_path(image.src_url))
        return StreamingResponse(
            iter([file_data]),
            media_type=image.mime_type,
            headers={
                "Content-Disposition": f"inline; filename={image.filename}"
            },
        )
    except Exception as e:
        logger.error(f"Failed to retrieve image {image_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image")


@router.delete("/images/{image_id}", tags=["media"])
async def delete_image(
    image_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Soft delete an uploaded image."""
    db = _get_db()

    image = _require_uploaded_image_account_scope(
        db, image_id, request_user_scope
    )

    with db.get_session() as session:
        image = session.query(UploadedImage).filter_by(id=image_id).first()
        if not image:
            raise HTTPException(status_code=404, detail="Image not found")
        image.deleted_at = datetime.now(timezone.utc)
        session.commit()

        logger.info(f"Image {image_id} soft-deleted")
        return {"ok": True, "message": "Image deleted"}


# =========================
# Document Upload Routes
# =========================


@router.post(
    "/upload/document", response_model=DocumentUploadResponse, tags=["media"]
)
@router.post(
    "/upload/file",
    response_model=DocumentUploadResponse,
    tags=["media"],
    deprecated=True,
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    project_id: Optional[int] = Form(default=None),
    thread_id: Optional[int] = Form(default=None),
    user_id: str = Form(default="default"),
    tag: Optional[str] = Form(default=None),
    source_tag: Optional[str] = Form(default=None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Upload a document file.

    Accepts: PDF, DOCX, TXT, MD
    Stores in: /media/documents/
    Extracts text for full-text search
    """
    # Validate file type
    allowed_types = [
        "application/pdf",
        "text/plain",
        "text/markdown",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document type: {file.content_type}",
        )

    try:
        # Read file data
        file_data = await file.read()
        filesize = len(file_data)
        filename = file.filename or "upload"
        effective_tag = _normalize_source_tag(tag, source_tag)
        effective_user_id = _resolve_effective_user_id(
            user_id,
            request_user_scope,
            default_when_blank=_request_account_id(request_user_scope),
        )
        human_label = source_label_from_filename(
            filename, fallback="uploaded-document"
        )

        db = _get_db()
        explicit_project_id = _coerce_optional_positive_int(project_id)
        explicit_thread_id = _coerce_optional_positive_int(thread_id)
        if explicit_project_id is not None:
            _require_project_account_scope(
                db, explicit_project_id, request_user_scope
            )
        if explicit_thread_id is not None:
            _require_thread_account_scope(
                db, explicit_thread_id, request_user_scope
            )
        resolved_project_id, resolved_thread_id = _resolve_upload_context(
            db, project_id, thread_id
        )

        # First pass: dedupe before storage write.
        with db.get_session() as session:
            identity, existing_asset = _compute_identity_with_existing_asset(
                session=session,
                project_id=resolved_project_id,
                media_kind="document",
                provenance="uploaded",
                file_data=file_data,
                human_label=human_label,
                original_filename=filename,
                mime_type=file.content_type,
            )
            if existing_asset:
                ensure_asset_alias(
                    session,
                    asset_id=existing_asset.id,
                    alias=filename,
                    alias_type="original_name",
                )
                existing = _find_uploaded_document_for_asset(
                    session, existing_asset.id
                )
                if existing and _media_row_is_owned_by_scope(
                    existing, request_user_scope
                ):
                    if not existing.source_tag:
                        existing.source_tag = effective_tag
                    _ensure_thread_document_link(
                        session,
                        thread_id=resolved_thread_id,
                        document_id=existing.id,
                        relation="attached",
                    )
                    _ensure_project_document_link(
                        session,
                        project_id=resolved_project_id,
                        document_id=existing.id,
                        document_type="uploaded",
                        attached_by=effective_user_id,
                    )
                    session.commit()
                    return _document_upload_response_from_row(
                        existing,
                        fallback_project_id=resolved_project_id,
                        requested_thread_id=resolved_thread_id,
                    )

        canonical_path = f"{identity.storage_prefix}{identity.system_name}"

        # Upload to storage
        src_url = storage.upload_file(
            file_data, canonical_path, content_type=file.content_type
        )

        # Extract text for document embedding.
        parsed_text = None
        if (
            file.content_type == "text/plain"
            or file.content_type == "text/markdown"
        ):
            try:
                parsed_text = file_data.decode("utf-8")
            except:
                logger.warning(f"Failed to decode text from {file.filename}")
        elif file.content_type == "application/pdf":
            try:
                parsed_text = extract_pdf_text(file_data)
            except PdfTextExtractionError as exc:
                logger.warning(
                    "PDF extraction failed for %s: %s", file.filename, exc
                )
            except Exception as exc:
                logger.warning(
                    "PDF extraction errored for %s: %s", file.filename, exc
                )
        elif (
            file.content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            try:
                parsed_text = extract_docx_text(file_data)
            except DocxTextExtractionError as exc:
                logger.warning(
                    "DOCX extraction failed for %s: %s", file.filename, exc
                )
            except Exception as exc:
                logger.warning(
                    "DOCX extraction errored for %s: %s", file.filename, exc
                )

        embedding_status = EmbeddingLifecycleStatus.PENDING.value
        embedding_error = None
        embedding_started_at = None
        embedding_completed_at = None
        if not parsed_text:
            embedding_status = EmbeddingLifecycleStatus.FAILED.value
            embedding_error = "parsed_text_missing"
            embedding_completed_at = datetime.now(timezone.utc)

        doc_id = str(uuid.uuid4())  # Origin row ID
        asset_metadata: dict[str, str | int | None] = {}

        # Second pass: create asset + origin row, tolerate races.
        with db.get_session() as session:
            try:
                (
                    identity,
                    existing_asset,
                ) = _compute_identity_with_existing_asset(
                    session=session,
                    project_id=resolved_project_id,
                    media_kind="document",
                    provenance="uploaded",
                    file_data=file_data,
                    human_label=human_label,
                    original_filename=filename,
                    mime_type=file.content_type,
                )
                if existing_asset:
                    ensure_asset_alias(
                        session,
                        asset_id=existing_asset.id,
                        alias=filename,
                        alias_type="original_name",
                    )
                    existing = _find_uploaded_document_for_asset(
                        session, existing_asset.id
                    )
                    if existing:
                        if not existing.source_tag:
                            existing.source_tag = effective_tag
                        _ensure_thread_document_link(
                            session,
                            thread_id=resolved_thread_id,
                            document_id=existing.id,
                            relation="attached",
                        )
                    if existing and _media_row_is_owned_by_scope(
                        existing, request_user_scope
                    ):
                        _ensure_thread_document_link(
                            session,
                            thread_id=resolved_thread_id,
                            document_id=existing.id,
                            relation="attached",
                        )
                        _ensure_project_document_link(
                            session,
                            project_id=resolved_project_id,
                            document_id=existing.id,
                            document_type="uploaded",
                            attached_by=effective_user_id,
                        )
                        session.commit()
                        return _document_upload_response_from_row(
                            existing,
                            fallback_project_id=resolved_project_id,
                            requested_thread_id=resolved_thread_id,
                        )
                    linked_doc = UploadedDocument(
                        id=doc_id,
                        asset_id=existing_asset.id,
                        project_id=resolved_project_id,
                        thread_id=resolved_thread_id,
                        user_id=effective_user_id,
                        src_url=existing_asset.src_url,
                        filename=filename,
                        filesize=filesize or (existing_asset.filesize or 0),
                        mime_type=file.content_type
                        or existing_asset.mime_type
                        or "application/octet-stream",
                        source_tag=effective_tag,
                        parsed_text=parsed_text,
                        embedding_status=embedding_status,
                        embedding_error=embedding_error,
                        embedding_started_at=embedding_started_at,
                        embedding_completed_at=embedding_completed_at,
                    )
                    session.add(linked_doc)
                    _ensure_thread_document_link(
                        session,
                        thread_id=resolved_thread_id,
                        document_id=linked_doc.id,
                        relation="attached",
                    )
                    _ensure_project_document_link(
                        session,
                        project_id=resolved_project_id,
                        document_id=linked_doc.id,
                        document_type="uploaded",
                        attached_by=effective_user_id,
                    )
                    session.commit()
                    src_url = linked_doc.src_url
                    asset_metadata = {
                        "asset_id": existing_asset.id,
                        "deterministic_id": existing_asset.deterministic_id,
                        "system_name": existing_asset.system_name,
                        "normalized_slug": existing_asset.normalized_slug,
                        "media_kind": existing_asset.media_kind,
                        "provenance": existing_asset.provenance,
                        "source_tag": existing_asset.source_tag,
                        "content_hash": existing_asset.content_hash,
                    }
                else:
                    asset = _create_media_asset(
                        session=session,
                        project_id=resolved_project_id,
                        thread_id=resolved_thread_id,
                        user_id=effective_user_id,
                        media_kind="document",
                        provenance="uploaded",
                        source_tag=effective_tag,
                        src_url=src_url,
                        mime_type=file.content_type,
                        filesize=filesize,
                        identity=identity,
                    )
                    ensure_asset_alias(
                        session,
                        asset_id=asset.id,
                        alias=filename,
                        alias_type="original_name",
                    )
                    uploaded_doc = UploadedDocument(
                        id=doc_id,
                        asset_id=asset.id,
                        project_id=resolved_project_id,
                        thread_id=resolved_thread_id,
                        user_id=effective_user_id,
                        src_url=src_url,
                        filename=filename,
                        filesize=filesize,
                        mime_type=file.content_type
                        or "application/octet-stream",
                        source_tag=effective_tag,
                        parsed_text=parsed_text,
                        embedding_status=embedding_status,
                        embedding_error=embedding_error,
                        embedding_started_at=embedding_started_at,
                        embedding_completed_at=embedding_completed_at,
                    )
                    session.add(uploaded_doc)
                    _ensure_thread_document_link(
                        session,
                        thread_id=resolved_thread_id,
                        document_id=uploaded_doc.id,
                        relation="attached",
                    )
                    _ensure_project_document_link(
                        session,
                        project_id=resolved_project_id,
                        document_id=uploaded_doc.id,
                        document_type="uploaded",
                        attached_by=effective_user_id,
                    )
                    session.commit()
                    asset_metadata = {
                        "asset_id": asset.id,
                        "deterministic_id": asset.deterministic_id,
                        "system_name": asset.system_name,
                        "normalized_slug": asset.normalized_slug,
                        "media_kind": asset.media_kind,
                        "provenance": asset.provenance,
                        "source_tag": asset.source_tag,
                        "content_hash": asset.content_hash,
                    }
            except IntegrityError:
                session.rollback()
                (
                    identity,
                    existing_asset,
                ) = _compute_identity_with_existing_asset(
                    session=session,
                    project_id=resolved_project_id,
                    media_kind="document",
                    provenance="uploaded",
                    file_data=file_data,
                    human_label=human_label,
                    original_filename=filename,
                    mime_type=file.content_type,
                )
                if existing_asset:
                    ensure_asset_alias(
                        session,
                        asset_id=existing_asset.id,
                        alias=filename,
                        alias_type="original_name",
                    )
                    existing = _find_uploaded_document_for_asset(
                        session, existing_asset.id
                    )
                    if existing and _media_row_is_owned_by_scope(
                        existing, request_user_scope
                    ):
                        _ensure_thread_document_link(
                            session,
                            thread_id=resolved_thread_id,
                            document_id=existing.id,
                            relation="attached",
                        )
                        _ensure_project_document_link(
                            session,
                            project_id=resolved_project_id,
                            document_id=existing.id,
                            document_type="uploaded",
                            attached_by=effective_user_id,
                        )
                        session.commit()
                        return _document_upload_response_from_row(
                            existing,
                            fallback_project_id=resolved_project_id,
                            requested_thread_id=resolved_thread_id,
                        )

                    linked_doc = UploadedDocument(
                        id=doc_id,
                        asset_id=existing_asset.id,
                        project_id=resolved_project_id,
                        thread_id=resolved_thread_id,
                        user_id=effective_user_id,
                        src_url=existing_asset.src_url,
                        filename=filename,
                        filesize=filesize or (existing_asset.filesize or 0),
                        mime_type=file.content_type
                        or existing_asset.mime_type
                        or "application/octet-stream",
                        source_tag=effective_tag,
                        parsed_text=parsed_text,
                        embedding_status=embedding_status,
                        embedding_error=embedding_error,
                        embedding_started_at=embedding_started_at,
                        embedding_completed_at=embedding_completed_at,
                    )
                    session.add(linked_doc)
                    _ensure_thread_document_link(
                        session,
                        thread_id=resolved_thread_id,
                        document_id=linked_doc.id,
                        relation="attached",
                    )
                    _ensure_project_document_link(
                        session,
                        project_id=resolved_project_id,
                        document_id=linked_doc.id,
                        document_type="uploaded",
                        attached_by=effective_user_id,
                    )
                    session.commit()
                    src_url = linked_doc.src_url
                    asset_metadata = {
                        "asset_id": existing_asset.id,
                        "deterministic_id": existing_asset.deterministic_id,
                        "system_name": existing_asset.system_name,
                        "normalized_slug": existing_asset.normalized_slug,
                        "media_kind": existing_asset.media_kind,
                        "provenance": existing_asset.provenance,
                        "source_tag": existing_asset.source_tag,
                        "content_hash": existing_asset.content_hash,
                    }
                else:
                    raise

        logger.info(
            f"Document uploaded: {filename} ({filesize} bytes) by user {effective_user_id}"
        )

        # --- Embedding (RAG) ---
        if parsed_text:
            try:
                enqueue_document_embed(
                    doc_id,
                    origin="api:media.upload",
                    metadata={
                        "filename": filename,
                        "mime_type": file.content_type,
                        "user_id": effective_user_id,
                        "project_id": resolved_project_id,
                        "thread_id": resolved_thread_id,
                        **asset_metadata,
                    },
                )
                logger.info(
                    "Document queued for embedding: %s (doc_id=%s)",
                    file.filename,
                    doc_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to enqueue embedding for %s: %s",
                    file.filename,
                    e,
                )
                embedding_status = EmbeddingLifecycleStatus.FAILED.value
                embedding_error = str(e)
                embedding_completed_at = datetime.now(timezone.utc)
                with db.get_session() as session:
                    session.query(UploadedDocument).filter_by(id=doc_id).update(
                        {
                            UploadedDocument.embedding_status: embedding_status,
                            UploadedDocument.embedding_error: embedding_error,
                            UploadedDocument.embedding_started_at: embedding_started_at,
                            UploadedDocument.embedding_completed_at: embedding_completed_at,
                        }
                    )
                    session.commit()

        return DocumentUploadResponse(
            id=doc_id,
            document_id=doc_id,
            media_asset_id=str(asset_metadata.get("asset_id") or "") or None,
            project_id=resolved_project_id,
            thread_id=resolved_thread_id,
            src_url=_signed_src_url(src_url),
            filename=filename,
            filesize=filesize,
            mime_type=file.content_type,
            source_tag=effective_tag,
            parsed_text=parsed_text,
            embedding_status=embedding_status,
            embedding_error=embedding_error,
            embedding_started_at=(
                embedding_started_at.isoformat()
                if embedding_started_at
                else None
            ),
            embedding_completed_at=(
                embedding_completed_at.isoformat()
                if embedding_completed_at
                else None
            ),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    except HTTPException:
        raise
    except Exception as exc:
        _log_upload_failure(
            route="/api/media/upload/document",
            request=request,
            exc=exc,
            project_id=_coerce_optional_positive_int(project_id),
            thread_id=_coerce_optional_positive_int(thread_id),
        )
        raise HTTPException(
            status_code=500,
            detail=_upload_error_detail("upload_failed", _GENERIC_UPLOAD_ERROR),
        ) from exc


# =========================
# Image Generation Routes
# =========================


@router.post(
    "/generate/image",
    response_model=ImageGenerationResponse,
    tags=["generation"],
)
async def generate_image(
    request: ImageGenerationRequest,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Generate an image using the configured AI provider.

    Calls the image generation provider (OpenAI DALL-E, Stability AI, or local),
    saves the generated image bytes to storage, and tracks in the database.
    """
    _require_media_feature(
        "CODEXIFY_ENABLE_MEDIA_GENERATION_ROUTES",
        "image generation",
    )
    db = _get_db()
    image_id = str(uuid.uuid4())
    project_id = request.project_id or 1
    thread_id = request.thread_id or 1
    effective_user_id = _resolve_effective_user_id(
        request.user_id,
        request_user_scope,
        default_when_blank="default",
    )
    if _coerce_optional_positive_int(request.project_id) is not None:
        _require_project_account_scope(
            db,
            _coerce_optional_positive_int(request.project_id) or 0,
            request_user_scope,
        )
    if _coerce_optional_positive_int(request.thread_id) is not None:
        _require_thread_account_scope(
            db,
            _coerce_optional_positive_int(request.thread_id) or 0,
            request_user_scope,
        )
    prompt_alias = (request.prompt or "").strip()
    if not prompt_alias:
        prompt_alias = "Generated image"

    try:
        # Generate image using configured provider
        image_bytes = ImageGenRouter.generate(
            prompt=request.prompt,
            model=request.model,
        )

        with db.get_session() as session:
            identity, existing_asset = _compute_identity_with_existing_asset(
                session=session,
                project_id=project_id,
                media_kind="image",
                provenance="generated",
                file_data=image_bytes,
                human_label=prompt_alias,
                original_filename=None,
                mime_type="image/png",
            )
            if existing_asset:
                ensure_asset_alias(
                    session,
                    asset_id=existing_asset.id,
                    alias=prompt_alias,
                    alias_type="prompt",
                )
                existing = _find_generated_image_for_asset(
                    session, existing_asset.id
                )
                if existing and _media_row_is_owned_by_scope(
                    existing, request_user_scope
                ):
                    session.commit()
                    return ImageGenerationResponse(
                        id=existing.id,
                        src_url=_signed_src_url(existing.src_url),
                        prompt=existing.prompt,
                        model=existing.model,
                        created_at=(
                            existing.created_at.isoformat()
                            if existing.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    )
                linked = GeneratedImage(
                    id=image_id,
                    asset_id=existing_asset.id,
                    project_id=project_id,
                    thread_id=thread_id,
                    user_id=effective_user_id,
                    src_url=existing_asset.src_url,
                    prompt=request.prompt,
                    model=request.model,
                )
                session.add(linked)
                session.commit()
                return ImageGenerationResponse(
                    id=linked.id,
                    src_url=_signed_src_url(linked.src_url),
                    prompt=linked.prompt,
                    model=linked.model,
                    created_at=(
                        linked.created_at.isoformat()
                        if linked.created_at
                        else datetime.now(timezone.utc).isoformat()
                    ),
                )

        filename = f"{identity.storage_prefix}{identity.system_name}"
        src_url = storage.upload_file(
            image_bytes, filename, content_type="image/png"
        )

        logger.info(f"Image generated: {request.prompt[:50]}... -> {src_url}")

    except HTTPException:
        # Re-raise HTTP exceptions (missing provider config, etc.)
        raise
    except Exception as exc:
        logger.exception(
            f"Image generation failed: {request.prompt[:50]}... error={exc}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {str(exc)}",
        )

    # Track generated image with canonical identity
    with db.get_session() as session:
        try:
            identity, existing_asset = _compute_identity_with_existing_asset(
                session=session,
                project_id=project_id,
                media_kind="image",
                provenance="generated",
                file_data=image_bytes,
                human_label=prompt_alias,
                original_filename=None,
                mime_type="image/png",
            )
            if existing_asset:
                ensure_asset_alias(
                    session,
                    asset_id=existing_asset.id,
                    alias=prompt_alias,
                    alias_type="prompt",
                )
                existing = _find_generated_image_for_asset(
                    session, existing_asset.id
                )
                if existing and _media_row_is_owned_by_scope(
                    existing, request_user_scope
                ):
                    session.commit()
                    return ImageGenerationResponse(
                        id=existing.id,
                        src_url=_signed_src_url(existing.src_url),
                        prompt=existing.prompt,
                        model=existing.model,
                        created_at=(
                            existing.created_at.isoformat()
                            if existing.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    )
                generated_image = GeneratedImage(
                    id=image_id,
                    asset_id=existing_asset.id,
                    project_id=project_id,
                    thread_id=thread_id,
                    user_id=effective_user_id,
                    src_url=existing_asset.src_url,
                    prompt=request.prompt,
                    model=request.model,
                )
                session.add(generated_image)
                session.commit()
                src_url = generated_image.src_url
            else:
                asset = _create_media_asset(
                    session=session,
                    project_id=project_id,
                    thread_id=thread_id,
                    user_id=effective_user_id,
                    media_kind="image",
                    provenance="generated",
                    source_tag="generated",
                    src_url=src_url,
                    mime_type="image/png",
                    filesize=len(image_bytes),
                    identity=identity,
                )
                ensure_asset_alias(
                    session,
                    asset_id=asset.id,
                    alias=prompt_alias,
                    alias_type="prompt",
                )
                generated_image = GeneratedImage(
                    id=image_id,
                    asset_id=asset.id,
                    project_id=project_id,
                    thread_id=thread_id,
                    user_id=effective_user_id,
                    src_url=src_url,
                    prompt=request.prompt,
                    model=request.model,
                )
                session.add(generated_image)
                session.commit()
        except IntegrityError:
            session.rollback()
            identity, existing_asset = _compute_identity_with_existing_asset(
                session=session,
                project_id=project_id,
                media_kind="image",
                provenance="generated",
                file_data=image_bytes,
                human_label=prompt_alias,
                original_filename=None,
                mime_type="image/png",
            )
            if existing_asset:
                ensure_asset_alias(
                    session,
                    asset_id=existing_asset.id,
                    alias=prompt_alias,
                    alias_type="prompt",
                )
                existing = _find_generated_image_for_asset(
                    session, existing_asset.id
                )
                if existing and _media_row_is_owned_by_scope(
                    existing, request_user_scope
                ):
                    session.commit()
                    return ImageGenerationResponse(
                        id=existing.id,
                        src_url=_signed_src_url(existing.src_url),
                        prompt=existing.prompt,
                        model=existing.model,
                        created_at=(
                            existing.created_at.isoformat()
                            if existing.created_at
                            else datetime.now(timezone.utc).isoformat()
                        ),
                    )
            raise

    return ImageGenerationResponse(
        id=image_id,
        src_url=_signed_src_url(src_url),
        prompt=request.prompt,
        model=request.model,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


# =========================
# TTS Routes
# =========================


@router.post("/tts/synthesize", response_model=TTSOutputResponse, tags=["tts"])
async def synthesize_speech(
    request: TTSSynthesizeRequest,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """
    Synthesize speech from text and track in database.

    Uses the existing TTSManager from guardian/tts/.
    """
    _require_media_feature("CODEXIFY_ENABLE_MEDIA_TTS_ROUTES", "tts")
    effective_user_id = _resolve_effective_user_id(
        request.user_id,
        request_user_scope,
        default_when_blank=None,
    )
    try:
        # Import TTS manager
        from guardian.tts.tts_manager import TTSManager

        # Initialize TTS
        tts_manager = TTSManager()

        # Synthesize
        audio_data = tts_manager.synthesize(
            text=request.text,
            voice=request.voice,
            provider_name=request.provider,
        )

        # Generate unique filename
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        filename = f"audio/tts_{timestamp}.wav"

        # Upload to storage
        src_url = storage.upload_file(
            audio_data, filename, content_type="audio/wav"
        )

        # Save to database
        db = _get_db()
        with db.get_session() as session:
            tts_output = TTSOutput(
                project_id=request.project_id,
                thread_id=request.thread_id,
                user_id=effective_user_id,
                text=request.text,
                voice=request.voice,
                provider=request.provider or tts_manager.default_provider,
                src_url=src_url,
                duration_seconds=None,  # TODO: Calculate from audio data
            )
            session.add(tts_output)
            session.commit()
            session.refresh(tts_output)

            logger.info(
                f"TTS synthesized: {len(request.text)} chars, provider={request.provider}"
            )

            return TTSOutputResponse(
                id=tts_output.id,
                src_url=_signed_src_url(src_url),
                text=request.text,
                voice=request.voice,
                provider=request.provider,
                duration_seconds=None,
                created_at=tts_output.created_at.isoformat(),
            )

    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"TTS synthesis failed: {str(e)}"
        )


@router.get("/tts/{tts_id}", tags=["tts"])
async def get_tts_audio(
    tts_id: int,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Get synthesized audio by ID."""
    _require_media_feature("CODEXIFY_ENABLE_MEDIA_TTS_ROUTES", "tts")
    db = _get_db()

    tts_output = _require_tts_account_scope(db, tts_id, request_user_scope)
    if not tts_output.src_url:
        raise HTTPException(status_code=404, detail="Audio not found")

    try:
        audio_data = storage.download_file(
            _storage_src_path(tts_output.src_url)
        )
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f"inline; filename=tts_{tts_id}.wav"
            },
        )
    except Exception as e:
        logger.error(f"Failed to retrieve audio {tts_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve audio")


# =========================
# List/Query Routes
# =========================


@router.get("/resolve", response_model=MediaResolveResponse, tags=["media"])
async def resolve_media_asset(
    project_id: int = Query(...),
    q: str = Query(...),
    kind: Optional[str] = Query(None),
    provenance: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Resolve fuzzy human labels/aliases to a canonical media asset."""
    db = _get_db()
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required")

    normalized_kind = (kind or "").strip().lower() or None
    normalized_provenance = (provenance or "").strip().lower() or None
    normalized_tag = (tag or "").strip().lower() or None

    _require_project_account_scope(db, project_id, request_user_scope)

    with db.get_session() as session:
        asset = resolve_asset_from_aliases(
            session,
            project_id=project_id,
            query=query,
            media_kind=normalized_kind,
            provenance=normalized_provenance,
            source_tag=normalized_tag,
        )
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        if not _asset_visible_to_scope(db, session, asset, request_user_scope):
            raise HTTPException(
                status_code=403,
                detail="Asset does not belong to the authenticated account",
            )

        ingested_at = asset.ingested_at or utcnow()
        display_title = display_title_for_asset(session, asset=asset)
        return MediaResolveResponse(
            asset_id=asset.id,
            src_url=_signed_src_url(asset.src_url),
            display_title=display_title,
            media_kind=asset.media_kind,
            provenance=asset.provenance,
            source_tag=asset.source_tag,
            created_at=ingested_at.isoformat(),
            ingested_at=ingested_at.isoformat(),
        )


@router.get("/images", tags=["media"])
async def list_images(
    project_id: Optional[int] = Query(None),
    thread_id: Optional[int] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    tag: Optional[str] = Query(None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """List uploaded images with optional filters."""
    db = _get_db()
    effective_user_id = _resolve_effective_user_id(
        user_id, request_user_scope, default_when_blank=None
    )
    explicit_project_id = _coerce_optional_positive_int(project_id)
    explicit_thread_id = _coerce_optional_positive_int(thread_id)
    if explicit_project_id is not None:
        _require_project_account_scope(
            db, explicit_project_id, request_user_scope
        )
    if explicit_thread_id is not None:
        _require_thread_account_scope(
            db, explicit_thread_id, request_user_scope
        )

    with db.get_session() as session:
        normalized_tag = tag.strip().lower() if tag else None

        if normalized_tag == "generated":
            query = session.query(GeneratedImage).filter(
                GeneratedImage.deleted_at.is_(None)
            )
            if project_id:
                query = query.filter_by(project_id=project_id)
            if thread_id:
                query = query.filter_by(thread_id=thread_id)
            if effective_user_id:
                query = query.filter_by(user_id=effective_user_id)
            images = (
                query.order_by(GeneratedImage.created_at.desc())
                .limit(limit)
                .all()
            )
            return {
                "images": [
                    {
                        "id": img.id,
                        "project_id": img.project_id,
                        "src_url": _signed_src_url(img.src_url),
                        "filename": img.prompt or "Generated image",
                        "mime_type": None,
                        "filesize": None,
                        "source_tag": "generated",
                        "created_at": (
                            img.created_at.isoformat()
                            if img.created_at
                            else None
                        ),
                    }
                    for img in images
                ],
                "count": len(images),
            }

        query = session.query(UploadedImage).filter(
            UploadedImage.deleted_at.is_(None)
        )

        if project_id:
            query = query.filter_by(project_id=project_id)
        if thread_id:
            query = query.filter_by(thread_id=thread_id)
        if effective_user_id:
            query = query.filter_by(user_id=effective_user_id)
        if normalized_tag:
            if normalized_tag == "uploaded":
                query = query.filter(
                    or_(
                        UploadedImage.source_tag.is_(None),
                        UploadedImage.source_tag == "",
                        UploadedImage.source_tag == "uploaded",
                    )
                )
            else:
                query = query.filter_by(source_tag=normalized_tag)

        images = (
            query.order_by(UploadedImage.created_at.desc()).limit(limit).all()
        )

        return {
            "images": [
                {
                    "id": img.id,
                    "project_id": img.project_id,
                    "src_url": _signed_src_url(img.src_url),
                    "filename": img.filename,
                    "mime_type": img.mime_type,
                    "filesize": img.filesize,
                    "source_tag": img.source_tag,
                    "created_at": (
                        img.created_at.isoformat() if img.created_at else None
                    ),
                }
                for img in images
            ],
            "count": len(images),
        }


def _isoformat_optional(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _normalize_document_artifact_type(value: Any) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized.startswith("gen"):
        return "generated"
    if normalized.startswith("up") or normalized in {"file", "document"}:
        return "uploaded"
    return None


def _query_document_artifact_rows(
    session,
    model,
    *,
    project_id: int | None = None,
    thread_id: int | None = None,
    document_ids: set[str] | None = None,
    user_id: str | None = None,
) -> list[Any]:
    """Load visible document rows for one source model."""
    if document_ids is not None and not document_ids:
        return []

    query = session.query(model).filter(model.deleted_at.is_(None))
    if project_id is not None:
        query = query.filter_by(project_id=project_id)
    if thread_id is not None:
        query = query.filter_by(thread_id=thread_id)
    if document_ids is not None:
        query = query.filter(model.id.in_(sorted(document_ids)))
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query.all()


def _query_document_artifact_thread_links(
    session,
    thread_ids: set[int],
) -> list[ThreadDocument]:
    if not thread_ids:
        return []

    query = session.query(ThreadDocument)
    if len(thread_ids) == 1:
        query = query.filter_by(thread_id=next(iter(thread_ids)))
    else:
        query = query.filter(ThreadDocument.thread_id.in_(sorted(thread_ids)))
    return query.order_by(ThreadDocument.created_at.desc()).all()


def _query_document_artifact_project_threads(
    session,
    project_id: int,
    user_id: str | None,
) -> list[Any]:
    query = session.query(ChatThread).filter_by(project_id=project_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    return query.all()


def _document_artifact_payload(
    row: Any,
    artifact_type: str,
    *,
    fallback_project_id: int | None = None,
    scope_thread_id: int | None = None,
    thread_titles: dict[int, str] | None = None,
    link_metadata: list[dict[str, Any]] | None = None,
    include_content: bool = False,
) -> dict[str, Any]:
    """Project one generated/uploaded row into the Documents API contract."""
    normalized_type = _normalize_document_artifact_type(artifact_type) or "uploaded"
    document_id = str(_row_value(row, "id") or "").strip()
    direct_project_id = _coerce_optional_positive_int(
        _row_value(row, "project_id")
    )
    resolved_project_id = direct_project_id or fallback_project_id
    direct_thread_id = _coerce_optional_positive_int(_row_value(row, "thread_id"))
    links = link_metadata or []

    thread_ids: list[int] = []

    def append_thread_id(value: Any) -> None:
        normalized = _coerce_optional_positive_int(value)
        if normalized is not None and normalized not in thread_ids:
            thread_ids.append(normalized)

    if scope_thread_id is not None:
        append_thread_id(scope_thread_id)
    else:
        append_thread_id(direct_thread_id)
    for link in links:
        append_thread_id(link.get("thread_id"))

    relations: list[str] = []
    link_created_at: list[str] = []
    for link in links:
        relation = str(link.get("relation") or "").strip()
        if relation and relation not in relations:
            relations.append(relation)
        created_at = _isoformat_optional(link.get("created_at"))
        if created_at:
            link_created_at.append(created_at)

    primary_thread_id = (
        scope_thread_id
        if scope_thread_id is not None
        else direct_thread_id or (thread_ids[0] if thread_ids else None)
    )
    normalized_thread_titles = thread_titles or {}
    resolved_thread_titles = [
        normalized_thread_titles[thread_id]
        for thread_id in thread_ids
        if normalized_thread_titles.get(thread_id)
    ]

    created_at = _isoformat_optional(_row_value(row, "created_at"))
    if not created_at and link_created_at:
        created_at = link_created_at[0]

    if normalized_type == "generated":
        title = str(_row_value(row, "title") or "Generated document").strip()
        filename = None
        document_format = str(_row_value(row, "format") or "").strip() or None
        source_tag = "generated"
        src_url = None
        filesize = None
        mime_type = "text/markdown" if document_format == "md" else "text/plain"
        media_asset_id = None
        embedding_status = None
        embedding_error = None
        embedding_started_at = None
        embedding_completed_at = None
    else:
        filename = str(_row_value(row, "filename") or document_id).strip()
        title = filename or "Untitled"
        document_format = None
        source_tag = _row_value(row, "source_tag")
        src_url = _signed_src_url(_row_value(row, "src_url"))
        filesize = _row_value(row, "filesize")
        mime_type = _row_value(row, "mime_type")
        media_asset_id = _row_value(row, "asset_id")
        embedding_status = _row_value(row, "embedding_status")
        embedding_error = _row_value(row, "embedding_error")
        embedding_started_at = _isoformat_optional(
            _row_value(row, "embedding_started_at")
        )
        embedding_completed_at = _isoformat_optional(
            _row_value(row, "embedding_completed_at")
        )

    payload: dict[str, Any] = {
        "id": document_id,
        "document_id": document_id,
        "artifact_type": normalized_type,
        "title": title,
        "filename": filename,
        "format": document_format,
        "project_id": resolved_project_id,
        "thread_id": primary_thread_id,
        "thread_ids": thread_ids,
        "thread_title": (
            normalized_thread_titles.get(primary_thread_id)
            if primary_thread_id is not None
            else None
        ),
        "thread_titles": resolved_thread_titles,
        "relation": relations[0] if relations else None,
        "relations": relations,
        "src_url": src_url,
        "filesize": filesize,
        "mime_type": mime_type,
        "source_tag": source_tag,
        "embedding_status": embedding_status,
        "embedding_error": embedding_error,
        "embedding_started_at": embedding_started_at,
        "embedding_completed_at": embedding_completed_at,
        "created_at": created_at,
    }

    if include_content:
        content = _row_value(row, "content")
        parsed_text = _row_value(row, "parsed_text")
        if normalized_type == "generated":
            payload["content"] = content
            payload["parsed_text"] = content
        else:
            payload["content"] = parsed_text
            payload["parsed_text"] = parsed_text
        payload["media_asset_id"] = media_asset_id

    return payload


def _list_document_artifact_payloads(
    session,
    *,
    project_id: int | None,
    thread_id: int | None,
    request_user_scope: RequestUserScope,
) -> list[dict[str, Any]]:
    """Read project/thread document artifacts without requiring a migration."""
    user_id = (
        _request_account_id(request_user_scope)
        if _is_multi_user_scope(request_user_scope)
        else None
    )
    fallback_project_id = project_id
    thread_titles: dict[int, str] = {}
    scoped_thread_ids: set[int] = set()
    link_records: list[tuple[Any, str | None]] = []

    if project_id is not None:
        project_threads = _query_document_artifact_project_threads(
            session, project_id, user_id
        )
        for thread in project_threads:
            normalized_thread_id = _coerce_optional_positive_int(
                _row_value(thread, "id")
            )
            if normalized_thread_id is None:
                continue
            scoped_thread_ids.add(normalized_thread_id)
            title = str(_row_value(thread, "title") or "").strip()
            if title:
                thread_titles[normalized_thread_id] = title

        project_links = (
            session.query(ProjectDocumentLink)
            .filter_by(project_id=project_id, is_enabled=True)
            .all()
        )
        link_records.extend(
            (
                link,
                _normalize_document_artifact_type(
                    _row_value(link, "document_type")
                ),
            )
            for link in project_links
        )
        link_records.extend(
            (link, None)
            for link in _query_document_artifact_thread_links(
                session, scoped_thread_ids
            )
        )
    elif thread_id is not None:
        target_thread = session.query(ChatThread).filter_by(id=thread_id).first()
        if target_thread is not None:
            fallback_project_id = _coerce_optional_positive_int(
                _row_value(target_thread, "project_id")
            )
            title = str(_row_value(target_thread, "title") or "").strip()
            if title:
                thread_titles[thread_id] = title
        scoped_thread_ids.add(thread_id)
        link_records.extend(
            (link, None)
            for link in _query_document_artifact_thread_links(
                session, scoped_thread_ids
            )
        )

    direct_generated = _query_document_artifact_rows(
        session,
        GeneratedDocument,
        project_id=project_id,
        thread_id=thread_id,
        user_id=user_id,
    )
    direct_uploaded = _query_document_artifact_rows(
        session,
        UploadedDocument,
        project_id=project_id,
        thread_id=thread_id,
        user_id=user_id,
    )

    linked_ids: dict[str, set[str]] = {"generated": set(), "uploaded": set()}
    for link, explicit_type in link_records:
        document_id = str(_row_value(link, "document_id") or "").strip()
        if not document_id:
            continue
        if explicit_type:
            linked_ids[explicit_type].add(document_id)
        else:
            # ThreadDocument predates the typed project link, so resolve both
            # sources and retain the existing generated-first collision policy.
            linked_ids["generated"].add(document_id)
            linked_ids["uploaded"].add(document_id)

    linked_generated = _query_document_artifact_rows(
        session,
        GeneratedDocument,
        document_ids=linked_ids["generated"],
        user_id=user_id,
    )
    linked_uploaded = _query_document_artifact_rows(
        session,
        UploadedDocument,
        document_ids=linked_ids["uploaded"],
        user_id=user_id,
    )

    rows_by_key: dict[tuple[str, str], Any] = {}
    for row in [*direct_generated, *linked_generated]:
        document_id = str(_row_value(row, "id") or "").strip()
        if document_id:
            rows_by_key[("generated", document_id)] = row
    for row in [*direct_uploaded, *linked_uploaded]:
        document_id = str(_row_value(row, "id") or "").strip()
        if document_id:
            rows_by_key[("uploaded", document_id)] = row

    link_metadata_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for link, explicit_type in link_records:
        document_id = str(_row_value(link, "document_id") or "").strip()
        if not document_id:
            continue
        candidate_types = [explicit_type] if explicit_type else [
            "generated",
            "uploaded",
        ]
        for candidate_type in candidate_types:
            key = (candidate_type, document_id)
            if key not in rows_by_key:
                continue
            link_metadata_by_key.setdefault(key, []).append(
                {
                    "thread_id": _row_value(link, "thread_id"),
                    "relation": _row_value(link, "relation"),
                    "created_at": _row_value(link, "created_at"),
                }
            )
            # Preserve the historical generated-first behavior if a legacy
            # ThreadDocument ID happens to exist in both source tables.
            break

    payloads = [
        _document_artifact_payload(
            row,
            artifact_type,
            fallback_project_id=fallback_project_id,
            scope_thread_id=thread_id,
            thread_titles=thread_titles,
            link_metadata=link_metadata_by_key.get((artifact_type, document_id)),
        )
        for (artifact_type, document_id), row in rows_by_key.items()
    ]
    payloads.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return payloads


@router.get(
    "/document-artifacts",
    response_model=DocumentArtifactListResponse,
    tags=["media"],
)
async def list_document_artifacts(
    project_id: Optional[int] = Query(None),
    thread_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=100),
    tag: Optional[str] = Query(None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """List uploaded and generated documents for one project or thread scope."""
    db = _get_db()
    explicit_project_id = _coerce_optional_positive_int(project_id)
    explicit_thread_id = _coerce_optional_positive_int(thread_id)
    if explicit_project_id is not None and explicit_thread_id is not None:
        raise HTTPException(
            status_code=400,
            detail="Specify either project_id or thread_id, not both",
        )
    if explicit_project_id is not None:
        _require_project_account_scope(
            db, explicit_project_id, request_user_scope
        )
    if explicit_thread_id is not None:
        _require_thread_account_scope(
            db, explicit_thread_id, request_user_scope
        )

    with db.get_session() as session:
        documents = _list_document_artifact_payloads(
            session,
            project_id=explicit_project_id,
            thread_id=explicit_thread_id,
            request_user_scope=request_user_scope,
        )

    normalized_tag = str(tag or "").strip().lower()
    if normalized_tag:
        documents = [
            document
            for document in documents
            if document.get("artifact_type") == normalized_tag
            or str(document.get("source_tag") or "").lower() == normalized_tag
        ]

    documents = documents[:limit]
    return {"documents": documents, "count": len(documents)}


@router.get(
    "/document-artifacts/{artifact_id}",
    response_model=DocumentArtifactDetailResponse,
    tags=["media"],
)
async def get_document_artifact(
    artifact_id: str,
    artifact_type: Optional[str] = Query(None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Fetch previewable content and provenance for one document artifact."""
    identity = str(artifact_id or "").strip()
    if not identity:
        raise HTTPException(status_code=404, detail="Document artifact not found")

    requested_type = _normalize_document_artifact_type(artifact_type)
    if artifact_type and requested_type is None:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    db = _get_db()
    user_id = (
        _request_account_id(request_user_scope)
        if _is_multi_user_scope(request_user_scope)
        else None
    )
    row = None
    resolved_type = requested_type
    with db.get_session() as session:
        candidate_types = [requested_type] if requested_type else [
            "generated",
            "uploaded",
        ]
        for candidate_type in candidate_types:
            model = (
                GeneratedDocument
                if candidate_type == "generated"
                else UploadedDocument
            )
            rows = _query_document_artifact_rows(
                session,
                model,
                document_ids={identity},
                user_id=user_id,
            )
            if rows:
                row = rows[0]
                resolved_type = candidate_type
                break

        if row is None or resolved_type is None:
            raise HTTPException(
                status_code=404,
                detail="Document artifact not found",
            )

        fallback_project_id = _coerce_optional_positive_int(
            _row_value(row, "project_id")
        )
        thread_titles: dict[int, str] = {}
        direct_thread_id = _coerce_optional_positive_int(
            _row_value(row, "thread_id")
        )
        if direct_thread_id is not None:
            thread = (
                session.query(ChatThread)
                .filter_by(id=direct_thread_id)
                .first()
            )
            if thread is not None:
                title = str(_row_value(thread, "title") or "").strip()
                if title:
                    thread_titles[direct_thread_id] = title

        payload = _document_artifact_payload(
            row,
            resolved_type,
            fallback_project_id=fallback_project_id,
            thread_titles=thread_titles,
            include_content=True,
        )
        payload["media_asset_id"] = _row_value(row, "asset_id")
        return payload


@router.get("/documents", tags=["media"])
async def list_documents(
    project_id: Optional[int] = Query(None),
    thread_id: Optional[int] = Query(None),
    limit: int = Query(50, le=100),
    tag: Optional[str] = Query(None),
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """List uploaded documents with optional filters."""
    db = _get_db()
    explicit_project_id = _coerce_optional_positive_int(project_id)
    explicit_thread_id = _coerce_optional_positive_int(thread_id)
    if explicit_project_id is not None:
        _require_project_account_scope(
            db, explicit_project_id, request_user_scope
        )
    if explicit_thread_id is not None:
        _require_thread_account_scope(
            db, explicit_thread_id, request_user_scope
        )
    effective_user_id = _request_account_id(request_user_scope)

    with db.get_session() as session:
        normalized_tag = tag.strip().lower() if tag else None
        query = session.query(UploadedDocument).filter(
            UploadedDocument.deleted_at.is_(None)
        )

        if project_id:
            query = query.filter_by(project_id=project_id)
        if thread_id:
            query = query.filter_by(thread_id=thread_id)
        if _is_multi_user_scope(request_user_scope):
            query = query.filter_by(user_id=effective_user_id)
        if normalized_tag:
            if normalized_tag == "uploaded":
                query = query.filter(
                    or_(
                        UploadedDocument.source_tag.is_(None),
                        UploadedDocument.source_tag == "",
                        UploadedDocument.source_tag == "uploaded",
                    )
                )
            else:
                query = query.filter_by(source_tag=normalized_tag)

        documents = (
            query.order_by(UploadedDocument.created_at.desc())
            .limit(limit)
            .all()
        )

        return {
            "documents": [
                {
                    "id": doc.id,
                    "project_id": doc.project_id,
                    "thread_id": doc.thread_id,
                    "src_url": _signed_src_url(doc.src_url),
                    "filename": doc.filename,
                    "mime_type": doc.mime_type,
                    "filesize": doc.filesize,
                    "source_tag": doc.source_tag,
                    "embedding_status": doc.embedding_status,
                    "embedding_error": doc.embedding_error,
                    "embedding_started_at": (
                        doc.embedding_started_at.isoformat()
                        if doc.embedding_started_at
                        else None
                    ),
                    "embedding_completed_at": (
                        doc.embedding_completed_at.isoformat()
                        if doc.embedding_completed_at
                        else None
                    ),
                    "created_at": (
                        doc.created_at.isoformat() if doc.created_at else None
                    ),
                }
                for doc in documents
            ],
            "count": len(documents),
        }


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    tags=["media"],
)
async def get_document(
    document_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Fetch a single uploaded document with parsed text content."""
    db = _get_db()

    document = _require_uploaded_document_account_scope(
        db, document_id, request_user_scope
    )

    return _document_detail_response_from_row(
        document,
        fallback_project_id=int(document.project_id or 0),
    )


@router.delete("/documents/{document_id}", tags=["media"])
async def delete_document(
    document_id: str,
    request_user_scope: RequestUserScope = Depends(get_request_user_scope),
):
    """Soft delete an uploaded document."""
    db = _get_db()

    document = _require_uploaded_document_account_scope(
        db, document_id, request_user_scope
    )

    with db.get_session() as session:
        document = (
            session.query(UploadedDocument).filter_by(id=document_id).first()
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        document.deleted_at = datetime.now(timezone.utc)
        session.commit()

        logger.info("Document %s soft-deleted", document_id)
        return {"ok": True, "message": "Document deleted"}
