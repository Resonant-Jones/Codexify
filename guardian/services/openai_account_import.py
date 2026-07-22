"""Durable intake, checkpoint, and media ingestion for OpenAI account exports."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Callable, Sequence

from sqlalchemy.orm import Session

from backend.rag.openai_export_adapter import (
    OpenAIExportFileRecord,
    OpenAIExportImageEvidence,
    OpenAIExportImageRelationship,
    guess_mime_type,
)
from guardian.core import event_bus
from guardian.core.db import GuardianDB, load_guardian_db_from_env
from guardian.core.storage import (
    StorageManager,
    create_import_staging_storage_from_env,
    create_storage_from_env,
)
from guardian.db.models import (
    ChatThread,
    GeneratedImage,
    MediaAsset,
    OpenAIAccountImportJob,
    Project,
    UploadedImage,
)
from guardian.protocol_tokens import AccountImportEventType, AccountImportStatus
from guardian.services.media_identity import (
    compute_content_hash,
    compute_identity,
    ensure_asset_alias,
    find_existing_asset,
    source_label_from_filename,
    utcnow,
)

logger = logging.getLogger(__name__)

_WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
_DETAIL_LIMIT = 100
_DETAIL_TEXT_LIMIT = 500


class AccountImportError(ValueError):
    """Bounded client/worker error with an HTTP-safe status code."""

    def __init__(self, message: str, *, code: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class AccountImportLimits:
    max_files: int = 20_000
    max_total_bytes: int = 20 * 1024 * 1024 * 1024
    max_file_bytes: int = 2 * 1024 * 1024 * 1024
    max_batch_files: int = 50
    max_batch_bytes: int = 2 * 1024 * 1024 * 1024
    conversation_batch_size: int = 10
    media_batch_size: int = 25

    @classmethod
    def from_env(cls) -> "AccountImportLimits":
        def value(name: str, default: int) -> int:
            try:
                return max(1, int(os.getenv(name, str(default))))
            except (TypeError, ValueError):
                return default

        return cls(
            max_files=value("OPENAI_ACCOUNT_IMPORT_MAX_FILES", cls.max_files),
            max_total_bytes=value(
                "OPENAI_ACCOUNT_IMPORT_MAX_TOTAL_BYTES", cls.max_total_bytes
            ),
            max_file_bytes=value(
                "OPENAI_ACCOUNT_IMPORT_MAX_FILE_BYTES", cls.max_file_bytes
            ),
            max_batch_files=value(
                "OPENAI_ACCOUNT_IMPORT_MAX_BATCH_FILES", cls.max_batch_files
            ),
            max_batch_bytes=value(
                "OPENAI_ACCOUNT_IMPORT_MAX_BATCH_BYTES", cls.max_batch_bytes
            ),
            conversation_batch_size=value(
                "OPENAI_ACCOUNT_IMPORT_CONVERSATION_BATCH_SIZE",
                cls.conversation_batch_size,
            ),
            media_batch_size=value(
                "OPENAI_ACCOUNT_IMPORT_MEDIA_BATCH_SIZE", cls.media_batch_size
            ),
        )


@dataclass(frozen=True)
class StagedImportFile:
    relative_path: str
    data: bytes | None = None
    content_type: str | None = None
    stream: BinaryIO | None = None


def normalize_import_relative_path(value: str) -> str:
    """Return a canonical POSIX relative path or reject unsafe input."""

    raw = unicodedata.normalize(
        "NFC", str(value or "").replace("\\", "/").strip()
    )
    if not raw or "\x00" in raw:
        raise AccountImportError(
            "Import file path is empty or invalid.", code="invalid_relative_path"
        )
    if raw.startswith("/") or _WINDOWS_DRIVE_RE.match(raw):
        raise AccountImportError(
            "Absolute import file paths are not allowed.",
            code="absolute_path_rejected",
        )
    original_parts = raw.split("/")
    if any(part == ".." for part in original_parts):
        raise AccountImportError(
            "Import file path traversal is not allowed.",
            code="path_traversal_rejected",
        )
    parts = [part for part in original_parts if part not in {"", "."}]
    if not parts:
        raise AccountImportError(
            "Import file path is empty after normalization.",
            code="empty_relative_path",
        )
    if any(len(part.encode("utf-8")) > 255 for part in parts):
        raise AccountImportError(
            "Import file path contains an overlong component.",
            code="relative_path_too_long",
        )
    normalized = PurePosixPath(*parts).as_posix()
    if len(normalized.encode("utf-8")) > 1024:
        raise AccountImportError(
            "Import file path is too long.", code="relative_path_too_long"
        )
    return normalized


def _bounded_detail(value: dict[str, Any]) -> dict[str, Any]:
    bounded: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, str):
            bounded[str(key)] = item[:_DETAIL_TEXT_LIMIT]
        elif isinstance(item, (int, float, bool)) or item is None:
            bounded[str(key)] = item
        elif isinstance(item, list):
            bounded[str(key)] = item[:50]
        else:
            bounded[str(key)] = str(item)[:_DETAIL_TEXT_LIMIT]
    return bounded


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OpenAIAccountImportService:
    """Own the durable account-import state machine and staged byte contract."""

    def __init__(
        self,
        *,
        db: GuardianDB | Any | None = None,
        storage: StorageManager | None = None,
        staging_storage: StorageManager | None = None,
        media_storage: StorageManager | None = None,
        enqueue_task: Callable[..., None] | None = None,
        emit_event: Callable[..., None] | None = None,
        limits: AccountImportLimits | None = None,
    ) -> None:
        resolved_db = db or load_guardian_db_from_env()
        if resolved_db is None:
            raise RuntimeError("Account import database is unavailable")
        self.db = resolved_db
        # ``storage`` remains a compatibility injection for focused tests. In
        # production, raw exports use a private persistent root and only
        # canonical media bytes use the signed /media surface.
        self.staging_storage = (
            staging_storage or storage or create_import_staging_storage_from_env()
        )
        self.media_storage = media_storage or storage or create_storage_from_env()
        if enqueue_task is None:
            from guardian.queue.account_import_queue import enqueue_account_import

            enqueue_task = enqueue_account_import
        self.enqueue_task = enqueue_task
        self.emit_event = emit_event or event_bus.emit_event
        self.limits = limits or AccountImportLimits.from_env()

    def _emit(self, topic: AccountImportEventType, payload: dict[str, Any], user_id: str) -> None:
        try:
            self.emit_event(topic.value, payload, tenant_id=user_id)
        except Exception:
            logger.exception(
                "[account-import] event emission failed topic=%s job_id=%s",
                topic.value,
                payload.get("job_id"),
            )

    @staticmethod
    def _job_query(
        session: Session,
        job_id: str,
        user_id: str,
        *,
        for_update: bool = False,
    ):
        query = session.query(OpenAIAccountImportJob).filter(
            OpenAIAccountImportJob.id == str(job_id),
            OpenAIAccountImportJob.user_id == str(user_id),
        )
        return query.with_for_update() if for_update else query

    def _require_job(
        self,
        session: Session,
        job_id: str,
        user_id: str,
        *,
        for_update: bool = False,
    ) -> OpenAIAccountImportJob:
        job = self._job_query(
            session, job_id, user_id, for_update=for_update
        ).first()
        if job is None:
            raise AccountImportError(
                "Account import job was not found.",
                code="account_import_not_found",
                status_code=404,
            )
        return job

    def create_job(
        self,
        *,
        user_id: str,
        total_file_count: int,
        total_byte_count: int,
        source_system: str = "openai",
    ) -> dict[str, Any]:
        count = int(total_file_count)
        byte_count = int(total_byte_count)
        if count <= 0 or count > self.limits.max_files:
            raise AccountImportError(
                "Declared import file count is outside configured limits.",
                code="file_count_limit_exceeded",
            )
        if byte_count < 0 or byte_count > self.limits.max_total_bytes:
            raise AccountImportError(
                "Declared import byte count is outside configured limits.",
                code="total_size_limit_exceeded",
            )
        if str(source_system).strip().lower() != "openai":
            raise AccountImportError(
                "Only OpenAI account exports are supported by this intake.",
                code="unsupported_source_system",
            )
        job_id = str(uuid.uuid4())
        account_scope = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:16]
        locator = f"account-imports/{account_scope}/{job_id}"
        job = OpenAIAccountImportJob(
            id=job_id,
            user_id=str(user_id),
            source_system="openai",
            status=AccountImportStatus.RECEIVING.value,
            staging_locator=locator,
            total_file_count=count,
            total_byte_count=byte_count,
            staged_manifest=[],
            warning_details=[],
            error_details=[],
            checkpoint={"conversation_ids": [], "media_paths": []},
        )
        with self.db.get_session() as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            return self.serialize_job(job)

    def get_job(self, *, job_id: str, user_id: str) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(session, job_id, user_id)
            return self.serialize_job(job)

    def get_worker_job(self, *, job_id: str, user_id: str) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(session, job_id, user_id)
            return self.serialize_job(job, include_internal=True)

    def recover_incomplete_jobs(self) -> list[dict[str, str]]:
        """Return queued/running jobs for startup re-enqueue after a crash."""

        with self.db.get_session() as session:
            jobs = (
                session.query(OpenAIAccountImportJob)
                .filter(
                    OpenAIAccountImportJob.status.in_(
                        {
                            AccountImportStatus.QUEUED.value,
                            AccountImportStatus.RUNNING.value,
                        }
                    )
                )
                .order_by(OpenAIAccountImportJob.created_at.asc())
                .all()
            )
            return [
                {"job_id": str(job.id), "user_id": str(job.user_id)}
                for job in jobs
            ]

    @staticmethod
    def _describe_staged_file(item: StagedImportFile) -> tuple[int, str]:
        if item.data is not None:
            return len(item.data), hashlib.sha256(item.data).hexdigest()
        if item.stream is None:
            raise AccountImportError(
                "Import file has no readable content.",
                code="invalid_upload_content",
            )
        digest = hashlib.sha256()
        size = 0
        try:
            item.stream.seek(0)
            while True:
                chunk = item.stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
            item.stream.seek(0)
        except Exception as exc:
            raise AccountImportError(
                "Import file stream could not be read.",
                code="invalid_upload_content",
            ) from exc
        return size, digest.hexdigest()

    def stage_files(
        self,
        *,
        job_id: str,
        user_id: str,
        files: Sequence[StagedImportFile],
    ) -> dict[str, Any]:
        if not files or len(files) > self.limits.max_batch_files:
            raise AccountImportError(
                "Upload batch file count is outside configured limits.",
                code="batch_file_limit_exceeded",
            )
        normalized_batch: list[dict[str, Any]] = []
        batch_paths: dict[str, tuple[str, int]] = {}
        batch_bytes = 0
        for item in files:
            normalized_path = normalize_import_relative_path(item.relative_path)
            size, digest = self._describe_staged_file(item)
            batch_bytes += size
            if size > self.limits.max_file_bytes:
                raise AccountImportError(
                    f"Import file exceeds the configured per-file limit: {normalized_path}",
                    code="file_size_limit_exceeded",
                )
            previous = batch_paths.get(normalized_path)
            if previous is not None and previous != (digest, size):
                raise AccountImportError(
                    f"Conflicting duplicate import path: {normalized_path}",
                    code="conflicting_duplicate_path",
                )
            batch_paths[normalized_path] = (digest, size)
            normalized_batch.append(
                {
                    "path": normalized_path,
                    "size": size,
                    "sha256": digest,
                    "content_type": item.content_type,
                    "data": item.data,
                    "stream": item.stream,
                }
            )
        if batch_bytes > self.limits.max_batch_bytes:
            raise AccountImportError(
                "Upload batch byte count exceeds the configured limit.",
                code="batch_size_limit_exceeded",
            )

        uploaded_urls: list[str] = []
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            if job.status != AccountImportStatus.RECEIVING.value:
                raise AccountImportError(
                    "Account import is no longer accepting files.",
                    code="account_import_not_receiving",
                    status_code=409,
                )
            manifest = [dict(item) for item in (job.staged_manifest or [])]
            by_path = {str(item.get("path")): item for item in manifest}
            additions: list[dict[str, Any]] = []
            duplicate_count = 0
            for item in normalized_batch:
                existing = by_path.get(item["path"])
                if existing is not None:
                    if (
                        str(existing.get("sha256")) != item["sha256"]
                        or int(existing.get("size", -1)) != item["size"]
                    ):
                        raise AccountImportError(
                            f"Conflicting duplicate import path: {item['path']}",
                            code="conflicting_duplicate_path",
                        )
                    duplicate_count += 1
                    continue
                additions.append(item)
                by_path[item["path"]] = item

            projected_files = len(manifest) + len(additions)
            projected_bytes = int(job.uploaded_byte_count or 0) + sum(
                int(item["size"]) for item in additions
            )
            if projected_files > int(job.total_file_count):
                raise AccountImportError(
                    "Uploaded file count exceeds the job declaration.",
                    code="declared_file_count_exceeded",
                )
            if projected_bytes > int(job.total_byte_count):
                raise AccountImportError(
                    "Uploaded byte count exceeds the job declaration.",
                    code="declared_byte_count_exceeded",
                )

            try:
                for item in additions:
                    storage_name = f"{job.staging_locator}/{item['path']}"
                    metadata = {
                        "job_id": job.id,
                        "relative_path": item["path"],
                    }
                    if item["data"] is not None:
                        storage_path = self.staging_storage.upload_file(
                            item["data"],
                            storage_name,
                            content_type=item.get("content_type"),
                            metadata=metadata,
                        )
                    else:
                        storage_path = self.staging_storage.upload_stream(
                            item["stream"],
                            storage_name,
                            content_type=item.get("content_type"),
                            metadata=metadata,
                        )
                    uploaded_urls.append(storage_path)
                    manifest.append(
                        {
                            "path": item["path"],
                            "size": item["size"],
                            "sha256": item["sha256"],
                            "content_type": item.get("content_type"),
                            "storage_path": storage_path,
                        }
                    )
                job.staged_manifest = manifest
                job.uploaded_file_count = len(manifest)
                job.uploaded_byte_count = projected_bytes
                job.duplicate_count = int(job.duplicate_count or 0) + duplicate_count
                job.updated_at = _utcnow()
                session.commit()
                session.refresh(job)
                return self.serialize_job(job)
            except Exception:
                session.rollback()
                for storage_path in uploaded_urls:
                    try:
                        self.staging_storage.delete_file(storage_path)
                    except Exception:
                        logger.warning(
                            "[account-import] unable to clean staged path=%s",
                            storage_path,
                        )
                raise

    def finalize_job(self, *, job_id: str, user_id: str) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            if job.status in {
                AccountImportStatus.QUEUED.value,
                AccountImportStatus.RUNNING.value,
                AccountImportStatus.COMPLETED.value,
                AccountImportStatus.COMPLETED_WITH_WARNINGS.value,
            }:
                return self.serialize_job(job)
            if job.status != AccountImportStatus.RECEIVING.value:
                raise AccountImportError(
                    "Account import cannot be finalized from its current state.",
                    code="account_import_invalid_state",
                    status_code=409,
                )
            if (
                int(job.uploaded_file_count) != int(job.total_file_count)
                or int(job.uploaded_byte_count) != int(job.total_byte_count)
            ):
                raise AccountImportError(
                    "All declared files must be staged before queue acceptance.",
                    code="staged_upload_incomplete",
                    status_code=409,
                )
            manifest = sorted(
                (dict(item) for item in (job.staged_manifest or [])),
                key=lambda item: str(item.get("path")),
            )
            fingerprint_input = [
                [item.get("path"), item.get("sha256"), item.get("size")]
                for item in manifest
            ]
            job.source_export_fingerprint = hashlib.sha256(
                json.dumps(
                    fingerprint_input,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ).hexdigest()
            job.status = AccountImportStatus.QUEUED.value
            job.queued_at = _utcnow()
            job.updated_at = job.queued_at
            session.commit()
            session.refresh(job)
            accepted = self.serialize_job(job)

        try:
            self.enqueue_task(job_id, user_id=user_id)
        except Exception as exc:
            with self.db.get_session() as session:
                job = self._require_job(
                    session, job_id, user_id, for_update=True
                )
                if job.status == AccountImportStatus.QUEUED.value:
                    job.status = AccountImportStatus.RECEIVING.value
                    job.queued_at = None
                    details = list(job.error_details or [])
                    details.append(
                        _bounded_detail(
                            {
                                "code": "queue_enqueue_failed",
                                "message": str(exc) or exc.__class__.__name__,
                            }
                        )
                    )
                    job.error_details = details[-_DETAIL_LIMIT:]
                    session.commit()
            raise AccountImportError(
                "The staged export could not be accepted by the background queue.",
                code="queue_enqueue_failed",
                status_code=503,
            ) from exc

        self._emit(
            AccountImportEventType.ACCEPTED,
            {
                "job_id": job_id,
                "status": AccountImportStatus.QUEUED.value,
                "file_count": accepted["total_file_count"],
                "byte_count": accepted["total_byte_count"],
            },
            user_id,
        )
        return accepted

    def mark_running(self, *, job_id: str, user_id: str) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            if job.status in {
                AccountImportStatus.COMPLETED.value,
                AccountImportStatus.COMPLETED_WITH_WARNINGS.value,
            }:
                return self.serialize_job(job)
            if job.status not in {
                AccountImportStatus.QUEUED.value,
                AccountImportStatus.RUNNING.value,
            }:
                raise AccountImportError(
                    "Account import worker received a job in an invalid state.",
                    code="account_import_invalid_state",
                    status_code=409,
                )
            first_start = job.started_at is None
            job.status = AccountImportStatus.RUNNING.value
            job.started_at = job.started_at or _utcnow()
            job.updated_at = _utcnow()
            session.commit()
            session.refresh(job)
            result = self.serialize_job(job)
        if first_start:
            self._emit(
                AccountImportEventType.RUNNING,
                {"job_id": job_id, "status": AccountImportStatus.RUNNING.value},
                user_id,
            )
        return result

    def materialize_staged_export(
        self, *, job_id: str, user_id: str, destination: Path
    ) -> dict[str, Any]:
        snapshot = self.get_worker_job(job_id=job_id, user_id=user_id)
        root = destination.resolve()
        root.mkdir(parents=True, exist_ok=True)
        locator = str(snapshot["staging_locator"]).strip("/")
        for item in snapshot["staged_manifest"]:
            relative_path = normalize_import_relative_path(str(item.get("path") or ""))
            storage_path = str(item.get("storage_path") or "")
            normalized_storage_path = storage_path.replace("\\", "/")
            expected_storage_path = self.staging_storage.get_file_url(
                f"{locator}/{relative_path}"
            ).replace("\\", "/")
            if normalized_storage_path != expected_storage_path:
                raise AccountImportError(
                    "Staged manifest locator does not belong to this import job.",
                    code="staging_locator_mismatch",
                    status_code=500,
                )
            target = (root / relative_path).resolve()
            try:
                target.relative_to(root)
            except ValueError as exc:
                raise AccountImportError(
                    "Staged file escaped the import workspace.",
                    code="path_traversal_rejected",
                    status_code=500,
                ) from exc
            self.staging_storage.download_to_path(storage_path, target)
            digest = hashlib.sha256()
            size = 0
            with target.open("rb") as staged_file:
                while True:
                    chunk = staged_file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    digest.update(chunk)
            if (
                digest.hexdigest() != str(item.get("sha256"))
                or size != int(item.get("size"))
            ):
                target.unlink(missing_ok=True)
                raise AccountImportError(
                    f"Staged file integrity check failed: {relative_path}",
                    code="staged_file_integrity_failed",
                    status_code=500,
                )
        return snapshot

    def record_conversation_batch(
        self, *, job_id: str, user_id: str, batch: dict[str, Any]
    ) -> dict[str, Any]:
        conversation_ids = [
            str(value)
            for value in batch.get("conversation_ids", [])
            if str(value).strip()
        ]
        conversation_counts = {
            str(item.get("conversation_id")): max(
                0, int(item.get("message_count", 0))
            )
            for item in batch.get("conversation_counts", [])
            if isinstance(item, dict)
            and str(item.get("conversation_id") or "").strip()
        }
        skipped_ids = [
            str(value)
            for value in batch.get("skipped_conversation_ids", [])
            if str(value).strip()
        ]
        attempted_ids = list(dict.fromkeys([*conversation_ids, *skipped_ids]))
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            checkpoint = dict(job.checkpoint or {})
            completed = list(checkpoint.get("conversation_ids") or [])
            seen = set(str(value) for value in completed)
            newly_completed = [
                value for value in attempted_ids if value not in seen
            ]
            completed.extend(newly_completed)
            checkpoint["conversation_ids"] = completed
            job.checkpoint = checkpoint
            newly_imported = [
                value for value in conversation_ids if value in newly_completed
            ]
            thread_delta = (
                len(newly_imported)
                if conversation_counts
                else min(
                    len(newly_imported),
                    max(0, int(batch.get("threads_imported", 0))),
                )
            )
            message_delta = (
                sum(conversation_counts.get(value, 0) for value in newly_imported)
                if conversation_counts
                else max(0, int(batch.get("messages_imported", 0)))
                if newly_imported
                else 0
            )
            duplicate_delta = max(
                0,
                thread_delta - max(0, int(batch.get("threads_imported", 0))),
            ) + max(
                0,
                message_delta - max(0, int(batch.get("messages_imported", 0))),
            )
            newly_skipped = [
                value for value in skipped_ids if value in newly_completed
            ]
            job.imported_thread_count = int(job.imported_thread_count or 0) + thread_delta
            job.imported_message_count = (
                int(job.imported_message_count or 0) + message_delta
            )
            job.duplicate_count = int(job.duplicate_count or 0) + duplicate_delta
            job.skipped_count = int(job.skipped_count or 0) + len(newly_skipped)
            if newly_skipped:
                details = list(job.warning_details or [])
                details.extend(
                    _bounded_detail(
                        {
                            "code": "conversation_not_committed",
                            "source_thread_id": value,
                            "message": "Conversation could not be confirmed after ingestion.",
                        }
                    )
                    for value in newly_skipped
                )
                job.warning_details = details[-_DETAIL_LIMIT:]
                job.warning_count = int(job.warning_count or 0) + len(newly_skipped)
            job.updated_at = _utcnow()
            session.commit()
            session.refresh(job)
            result = self.serialize_job(job)
        if not newly_completed:
            return result
        self._emit(
            AccountImportEventType.BATCH_COMMITTED,
            {
                "job_id": job_id,
                "status": AccountImportStatus.RUNNING.value,
                "batch_kind": "conversations",
                "conversation_ids": [value[:255] for value in newly_imported[:50]],
                "threads_imported": thread_delta,
                "messages_imported": message_delta,
                "duplicates": duplicate_delta,
                "skipped": len(newly_skipped),
            },
            user_id,
        )
        return result

    def _resolve_import_project(
        self, session: Session, *, user_id: str
    ) -> Project:
        project = (
            session.query(Project)
            .filter(Project.user_id == user_id, Project.name == "Imports")
            .first()
        )
        if project is not None:
            return project
        suffix = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:8]
        name = "Imports"
        if session.query(Project.id).filter(Project.name == name).first():
            name = f"Imports ({suffix})"
        project = (
            session.query(Project)
            .filter(Project.user_id == user_id, Project.name == name)
            .first()
        )
        if project is None:
            project = Project(
                user_id=user_id,
                name=name,
                description="Account-owned OpenAI export imports",
            )
            session.add(project)
            session.flush()
        return project

    @staticmethod
    def _resolve_source_thread(
        session: Session, *, user_id: str, source_thread_id: str | None
    ) -> ChatThread | None:
        if not source_thread_id:
            return None
        rows = session.query(ChatThread).filter(ChatThread.user_id == user_id).all()
        for thread in rows:
            metadata = thread.thread_config if isinstance(thread.thread_config, dict) else {}
            if str(metadata.get("source_thread_id") or "") == source_thread_id:
                return thread
        return None

    def import_image_record(
        self,
        *,
        job_id: str,
        user_id: str,
        record: OpenAIExportFileRecord,
        evidence: OpenAIExportImageEvidence,
    ) -> dict[str, Any]:
        if record.detected_kind not in {
            "image_png",
            "image_jpeg",
            "image_gif",
            "image_webp",
        }:
            raise AccountImportError(
                "Only supported image records may enter image ingestion.",
                code="unsupported_media_kind",
            )
        data = Path(record.absolute_path).read_bytes()
        content_hash = compute_content_hash(data)
        mime_type = guess_mime_type(record) or "application/octet-stream"
        source_tag = evidence.source_tag
        if source_tag not in {"generated", "uploaded", "unclassified"}:
            source_tag = "unclassified"

        with self.db.get_session() as session:
            job = self._require_job(session, job_id, user_id)
            source_thread = self._resolve_source_thread(
                session,
                user_id=user_id,
                source_thread_id=evidence.source_thread_id,
            )
            project = (
                session.query(Project)
                .filter(
                    Project.id == source_thread.project_id,
                    Project.user_id == user_id,
                )
                .first()
                if source_thread is not None and source_thread.project_id is not None
                else None
            )
            project = project or self._resolve_import_project(session, user_id=user_id)
            existing = find_existing_asset(
                session,
                project_id=int(project.id),
                media_kind="image",
                provenance="imported",
                content_hash=content_hash,
            )
            if existing is not None and str(existing.user_id) != user_id:
                raise AccountImportError(
                    "Canonical media ownership did not match the import account.",
                    code="media_account_scope_mismatch",
                    status_code=500,
                )
            relationships = evidence.relationships or (
                OpenAIExportImageRelationship(
                    source_thread_id=evidence.source_thread_id,
                    source_message_id=evidence.source_message_id,
                    evidence_kind=evidence.evidence_kind,
                ),
            )
            lineages = [
                {
                    "import_job_id": job_id,
                    "source_relative_path": record.path,
                    "source_export_id": job.source_export_fingerprint,
                    "source_message_id": relationship.source_message_id,
                    "source_thread_id": relationship.source_thread_id,
                    "evidence_kind": relationship.evidence_kind,
                    "source_tag": source_tag,
                }
                for relationship in relationships
            ]
            asset_created = existing is None
            if existing is None:
                identity = compute_identity(
                    file_data=data,
                    media_kind="image",
                    provenance=(
                        "generated" if source_tag == "generated" else "uploaded"
                    ),
                    human_label=source_label_from_filename(
                        record.path, fallback="openai-export-image"
                    ),
                    original_filename=Path(record.path).name,
                    mime_type=mime_type,
                    first_seen_at=job.created_at or utcnow(),
                    content_hash=content_hash,
                )
                src_url = self.media_storage.upload_file(
                    data,
                    f"{identity.storage_prefix}{identity.system_name}",
                    content_type=mime_type,
                    metadata={"import_job_id": job_id, "source_path": record.path},
                )
                existing = MediaAsset(
                    id=str(uuid.uuid4()),
                    project_id=int(project.id),
                    thread_id=source_thread.id if source_thread is not None else None,
                    user_id=user_id,
                    media_kind="image",
                    provenance="imported",
                    source_tag=source_tag,
                    content_hash=identity.content_hash,
                    deterministic_id=identity.deterministic_id,
                    normalized_slug=identity.normalized_slug,
                    system_name=identity.system_name,
                    storage_prefix=identity.storage_prefix,
                    src_url=src_url,
                    mime_type=mime_type,
                    filesize=len(data),
                    import_job_id=job_id,
                    source_relative_path=record.path,
                    source_export_id=job.source_export_fingerprint,
                    source_message_id=evidence.source_message_id,
                    source_thread_id=evidence.source_thread_id,
                    import_lineage=lineages,
                )
                session.add(existing)
                session.flush()
            else:
                current_lineage = list(existing.import_lineage or [])
                for lineage in lineages:
                    if lineage not in current_lineage:
                        current_lineage.append(lineage)
                existing.import_lineage = current_lineage[-_DETAIL_LIMIT:]
                if existing.source_tag != source_tag:
                    existing.source_tag = "unclassified"
                existing.import_job_id = existing.import_job_id or job_id
                existing.source_relative_path = (
                    existing.source_relative_path or record.path
                )
                existing.source_export_id = (
                    existing.source_export_id or job.source_export_fingerprint
                )
                existing.source_message_id = (
                    existing.source_message_id or evidence.source_message_id
                )
                existing.source_thread_id = (
                    existing.source_thread_id or evidence.source_thread_id
                )

            ensure_asset_alias(
                session,
                asset_id=existing.id,
                alias=Path(record.path).name,
                alias_type="original_name",
            )

            effective_source_tag = str(existing.source_tag or "unclassified")
            generated_image = (
                session.query(GeneratedImage)
                .filter(GeneratedImage.asset_id == existing.id)
                .first()
            )
            uploaded_image = (
                session.query(UploadedImage)
                .filter(UploadedImage.asset_id == existing.id)
                .first()
            )
            if generated_image is not None and str(generated_image.user_id) != user_id:
                raise AccountImportError(
                    "Generated image ownership did not match the import account.",
                    code="media_account_scope_mismatch",
                    status_code=500,
                )
            if uploaded_image is not None and str(uploaded_image.user_id) != user_id:
                raise AccountImportError(
                    "Uploaded image ownership did not match the import account.",
                    code="media_account_scope_mismatch",
                    status_code=500,
                )
            metadata_created = False
            if effective_source_tag == "generated":
                if uploaded_image is not None and uploaded_image.deleted_at is None:
                    uploaded_image.deleted_at = _utcnow()
                image = generated_image
                if image is None:
                    image = GeneratedImage(
                        id=str(uuid.uuid4()),
                        asset_id=existing.id,
                        project_id=int(project.id),
                        thread_id=(
                            source_thread.id if source_thread is not None else None
                        ),
                        user_id=user_id,
                        src_url=existing.src_url,
                        prompt=evidence.prompt or "",
                        model=evidence.model or "openai-export",
                    )
                    session.add(image)
                    metadata_created = True
                elif image.deleted_at is not None:
                    image.deleted_at = None
            else:
                if generated_image is not None and generated_image.deleted_at is None:
                    generated_image.deleted_at = _utcnow()
                image = uploaded_image
                if image is None:
                    image = UploadedImage(
                        id=str(uuid.uuid4()),
                        asset_id=existing.id,
                        project_id=int(project.id),
                        thread_id=(
                            source_thread.id if source_thread is not None else None
                        ),
                        user_id=user_id,
                        src_url=existing.src_url,
                        filename=Path(record.path).name,
                        filesize=len(data),
                        mime_type=mime_type,
                        source_tag=effective_source_tag,
                    )
                    session.add(image)
                    metadata_created = True
                else:
                    image.deleted_at = None
                    image.source_tag = effective_source_tag
            session.commit()
            return {
                "path": record.path,
                "asset_id": existing.id,
                "media_id": image.id,
                "source_tag": effective_source_tag,
                "evidence_kind": evidence.evidence_kind,
                "thread_id": source_thread.id if source_thread is not None else None,
                "created": bool(asset_created or metadata_created),
                "duplicate": not bool(asset_created or metadata_created),
            }

    def record_media_batch(
        self,
        *,
        job_id: str,
        user_id: str,
        results: Sequence[dict[str, Any]],
        skipped: Sequence[dict[str, Any]] = (),
        warnings: Sequence[dict[str, Any]] = (),
    ) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            checkpoint = dict(job.checkpoint or {})
            media_paths = list(checkpoint.get("media_paths") or [])
            seen = set(str(value) for value in media_paths)
            credited_results = [
                item
                for item in results
                if item.get("path") and str(item["path"]) not in seen
            ]
            credited_skips = [
                item
                for item in skipped
                if item.get("path") and str(item["path"]) not in seen
            ]
            committed_paths = list(
                dict.fromkeys(
                    [
                        *(str(item["path"]) for item in credited_results),
                        *(str(item["path"]) for item in credited_skips),
                    ]
                )
            )
            media_paths.extend(committed_paths)
            checkpoint["media_paths"] = media_paths
            warning_keys = list(checkpoint.get("warning_keys") or [])
            seen_warning_keys = {str(value) for value in warning_keys}
            credited_warnings: list[dict[str, Any]] = []
            for item in warnings:
                key = json.dumps(_bounded_detail(item), sort_keys=True)
                if key in seen_warning_keys:
                    continue
                seen_warning_keys.add(key)
                warning_keys.append(key)
                credited_warnings.append(item)
            checkpoint["warning_keys"] = warning_keys[-_DETAIL_LIMIT:]
            job.checkpoint = checkpoint
            imported_count = len(credited_results)
            duplicate_count = sum(
                1 for item in credited_results if item.get("duplicate")
            )
            job.imported_media_count = int(job.imported_media_count or 0) + imported_count
            job.duplicate_count = int(job.duplicate_count or 0) + duplicate_count
            job.skipped_count = int(job.skipped_count or 0) + len(credited_skips)
            details = list(job.warning_details or [])
            details.extend(_bounded_detail(item) for item in credited_warnings)
            details.extend(_bounded_detail(item) for item in credited_skips)
            job.warning_details = details[-_DETAIL_LIMIT:]
            job.warning_count = (
                int(job.warning_count or 0)
                + len(credited_warnings)
                + len(credited_skips)
            )
            job.updated_at = _utcnow()
            session.commit()
            session.refresh(job)
            result = self.serialize_job(job)
        if not credited_results and not credited_skips and not credited_warnings:
            return result
        self._emit(
            AccountImportEventType.BATCH_COMMITTED,
            {
                "job_id": job_id,
                "status": AccountImportStatus.RUNNING.value,
                "batch_kind": "media",
                "media_ids": [
                    str(item.get("media_id"))
                    for item in credited_results[:50]
                    if item.get("media_id")
                ],
                "imported_media": imported_count,
                "duplicates": duplicate_count,
                "skipped": len(credited_skips),
            },
            user_id,
        )
        return result

    def complete_job(self, *, job_id: str, user_id: str) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            if job.status in {
                AccountImportStatus.COMPLETED.value,
                AccountImportStatus.COMPLETED_WITH_WARNINGS.value,
                AccountImportStatus.FAILED.value,
            }:
                return self.serialize_job(job)
            has_warnings = int(job.warning_count or 0) > 0 or int(job.skipped_count or 0) > 0
            job.status = (
                AccountImportStatus.COMPLETED_WITH_WARNINGS.value
                if has_warnings
                else AccountImportStatus.COMPLETED.value
            )
            job.completed_at = _utcnow()
            job.updated_at = job.completed_at
            session.commit()
            session.refresh(job)
            result = self.serialize_job(job)
        self._emit(
            AccountImportEventType.COMPLETED,
            {
                "job_id": job_id,
                "status": result["status"],
                "threads_imported": result["imported_thread_count"],
                "messages_imported": result["imported_message_count"],
                "media_imported": result["imported_media_count"],
                "warnings": result["warning_count"],
            },
            user_id,
        )
        return result

    def fail_job(
        self,
        *,
        job_id: str,
        user_id: str,
        code: str,
        message: str,
    ) -> dict[str, Any]:
        with self.db.get_session() as session:
            job = self._require_job(
                session, job_id, user_id, for_update=True
            )
            if job.status in {
                AccountImportStatus.COMPLETED.value,
                AccountImportStatus.COMPLETED_WITH_WARNINGS.value,
                AccountImportStatus.FAILED.value,
            }:
                return self.serialize_job(job)
            details = list(job.error_details or [])
            details.append(_bounded_detail({"code": code, "message": message}))
            job.error_details = details[-_DETAIL_LIMIT:]
            job.failure_count = int(job.failure_count or 0) + 1
            job.status = AccountImportStatus.FAILED.value
            job.completed_at = _utcnow()
            job.updated_at = job.completed_at
            session.commit()
            session.refresh(job)
            result = self.serialize_job(job)
        self._emit(
            AccountImportEventType.FAILED,
            {
                "job_id": job_id,
                "status": AccountImportStatus.FAILED.value,
                "error_code": str(code)[:100],
            },
            user_id,
        )
        return result

    @staticmethod
    def serialize_job(
        job: OpenAIAccountImportJob,
        *,
        include_internal: bool = False,
    ) -> dict[str, Any]:
        def timestamp(value: datetime | None) -> str | None:
            return value.isoformat() if value is not None else None

        payload = {
            "job_id": job.id,
            "source_system": job.source_system,
            "source_export_fingerprint": job.source_export_fingerprint,
            "status": job.status,
            "total_file_count": int(job.total_file_count or 0),
            "total_byte_count": int(job.total_byte_count or 0),
            "uploaded_file_count": int(job.uploaded_file_count or 0),
            "uploaded_byte_count": int(job.uploaded_byte_count or 0),
            "imported_thread_count": int(job.imported_thread_count or 0),
            "imported_message_count": int(job.imported_message_count or 0),
            "imported_media_count": int(job.imported_media_count or 0),
            "duplicate_count": int(job.duplicate_count or 0),
            "skipped_count": int(job.skipped_count or 0),
            "warning_count": int(job.warning_count or 0),
            "failure_count": int(job.failure_count or 0),
            "warning_details": list(job.warning_details or [])[-_DETAIL_LIMIT:],
            "error_details": list(job.error_details or [])[-_DETAIL_LIMIT:],
            "created_at": timestamp(job.created_at),
            "queued_at": timestamp(job.queued_at),
            "started_at": timestamp(job.started_at),
            "updated_at": timestamp(job.updated_at),
            "completed_at": timestamp(job.completed_at),
        }
        if include_internal:
            payload.update(
                {
                    "user_id": job.user_id,
                    "staging_locator": job.staging_locator,
                    "staged_manifest": list(job.staged_manifest or []),
                    "checkpoint": dict(job.checkpoint or {}),
                }
            )
        return payload
