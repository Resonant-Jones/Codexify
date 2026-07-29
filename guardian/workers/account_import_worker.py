"""Background worker for durable OpenAI account-export imports."""

from __future__ import annotations

import logging
import os
import stat
import time
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from redis.exceptions import TimeoutError as RedisTimeoutError

from backend.rag.openai_export_adapter import (
    build_openai_export_image_evidence_index,
    diagnose_openai_export_path,
    resolve_openai_export_image_evidence,
)
from backend.rag.openai_export_conversation_import import (
    import_openai_export_conversations,
)
from guardian.config.db_defaults import DEFAULT_PG_DSN
from guardian.core import event_bus
from guardian.core.chatlog_postgres import PostgresChatLogDB
from guardian.core.db import GuardianDB
from guardian.queue.account_import_queue import (
    QUEUE_NAME,
    TASK_TYPE,
    dequeue_account_import,
)
from guardian.services.openai_account_import import (
    AccountImportError,
    OpenAIAccountImportService,
    normalize_import_relative_path,
)

logger = logging.getLogger(__name__)


def _database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_PG_DSN


def _get_service() -> OpenAIAccountImportService:
    return OpenAIAccountImportService(db=GuardianDB(_database_url()))


def _safe_extract_zip(
    archive: Path,
    destination: Path,
    *,
    service: OpenAIAccountImportService,
) -> Path:
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    file_count = 0
    byte_count = 0
    actual_byte_count = 0
    seen: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if info.is_dir():
                continue
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise AccountImportError(
                    "OpenAI export ZIP contains a symbolic link.",
                    code="zip_symlink_rejected",
                )
            relative_path = normalize_import_relative_path(info.filename)
            if relative_path in seen:
                raise AccountImportError(
                    f"OpenAI export ZIP contains a duplicate path: {relative_path}",
                    code="conflicting_duplicate_path",
                )
            seen.add(relative_path)
            file_count += 1
            byte_count += int(info.file_size)
            if file_count > service.limits.max_files:
                raise AccountImportError(
                    "OpenAI export ZIP exceeds the configured file limit.",
                    code="file_count_limit_exceeded",
                )
            if byte_count > service.limits.max_total_bytes:
                raise AccountImportError(
                    "OpenAI export ZIP exceeds the configured expanded byte limit.",
                    code="total_size_limit_exceeded",
                )
            if int(info.file_size) > service.limits.max_file_bytes:
                raise AccountImportError(
                    f"OpenAI export ZIP member is too large: {relative_path}",
                    code="file_size_limit_exceeded",
                )
            target = (destination / relative_path).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise AccountImportError(
                    "OpenAI export ZIP member escaped the extraction root.",
                    code="path_traversal_rejected",
                ) from exc
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(info) as source, target.open("wb") as sink:
                copied = 0
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    actual_byte_count += len(chunk)
                    if copied > service.limits.max_file_bytes:
                        raise AccountImportError(
                            f"OpenAI export ZIP member expanded beyond its limit: {relative_path}",
                            code="file_size_limit_exceeded",
                        )
                    if actual_byte_count > service.limits.max_total_bytes:
                        raise AccountImportError(
                            "OpenAI export ZIP expanded beyond its total byte limit.",
                            code="total_size_limit_exceeded",
                        )
                    sink.write(chunk)
    return destination


def _resolve_export_root(
    staged_root: Path,
    *,
    service: OpenAIAccountImportService,
    workspace: Path,
) -> Path:
    files = sorted(path for path in staged_root.rglob("*") if path.is_file())
    if len(files) == 1 and zipfile.is_zipfile(files[0]):
        return _safe_extract_zip(
            files[0], workspace / "expanded", service=service
        )
    return staged_root


def requeue_incomplete_jobs(service: OpenAIAccountImportService) -> int:
    """Recover tasks lost after destructive Redis dequeue and worker crash."""

    recovered = 0
    for job in service.recover_incomplete_jobs():
        service.enqueue_task(job["job_id"], user_id=job["user_id"])
        recovered += 1
    return recovered


def process_account_import_task(
    payload: dict[str, Any] | None,
    *,
    service: OpenAIAccountImportService | None = None,
) -> bool:
    if not isinstance(payload, dict) or payload.get("type") != TASK_TYPE:
        logger.warning("[account-import] invalid task payload=%r", payload)
        return False
    job_id = str(payload.get("job_id") or "").strip()
    user_id = str(payload.get("user_id") or "").strip()
    if not job_id or not user_id:
        logger.warning("[account-import] missing job/account identity payload=%r", payload)
        return False

    service = service or _get_service()
    try:
        snapshot = service.mark_running(job_id=job_id, user_id=user_id)
        if snapshot["status"] in {"completed", "completed_with_warnings"}:
            return True

        with TemporaryDirectory(prefix=f"codexify-account-import-{job_id[:8]}-") as tmpdir:
            workspace = Path(tmpdir)
            staged_root = workspace / "staged"
            snapshot = service.materialize_staged_export(
                job_id=job_id,
                user_id=user_id,
                destination=staged_root,
            )
            export_root = _resolve_export_root(
                staged_root, service=service, workspace=workspace
            )
            report = diagnose_openai_export_path(export_root)
            inventory = report.inventory
            checkpoint = dict(snapshot.get("checkpoint") or {})

            if inventory.legacy_detected or inventory.sharded_detected:
                diagnostics = import_openai_export_conversations(
                    export_root,
                    user_id=user_id,
                    diagnostic_dir=workspace / "diagnostics",
                    checkpoint_path=str(workspace / "checkpoint"),
                    resume=True,
                    batch_conversations=service.limits.conversation_batch_size,
                    embedding_mode="defer",
                    completed_conversation_ids=set(
                        str(value)
                        for value in checkpoint.get("conversation_ids", [])
                    ),
                    on_batch_committed=lambda batch: service.record_conversation_batch(
                        job_id=job_id,
                        user_id=user_id,
                        batch=batch,
                    ),
                )
                if diagnostics.errors:
                    raise RuntimeError("; ".join(diagnostics.errors[:5]))

            evidence_index = build_openai_export_image_evidence_index(inventory)
            completed_media_paths = {
                str(value) for value in checkpoint.get("media_paths", [])
            }
            supported_image_records = [
                record
                for record in inventory.files
                if record.detected_kind
                in {"image_png", "image_jpeg", "image_gif", "image_webp"}
            ]
            image_records = [
                record
                for record in supported_image_records
                if record.path not in completed_media_paths
            ]
            for start in range(0, len(image_records), service.limits.media_batch_size):
                results: list[dict[str, Any]] = []
                skipped: list[dict[str, Any]] = []
                warnings: list[dict[str, Any]] = []
                for record in image_records[
                    start : start + service.limits.media_batch_size
                ]:
                    try:
                        evidence = resolve_openai_export_image_evidence(
                            record.path, evidence_index
                        )
                        results.append(
                            service.import_image_record(
                                job_id=job_id,
                                user_id=user_id,
                                record=record,
                                evidence=evidence,
                            )
                        )
                        if evidence.source_tag == "unclassified":
                            warnings.append(
                                {
                                    "path": record.path,
                                    "code": "image_provenance_unclassified",
                                    "message": (
                                        "Image retained without provable uploaded "
                                        "or generated provenance."
                                    ),
                                    "evidence_kind": evidence.evidence_kind,
                                }
                            )
                    except Exception as exc:
                        logger.warning(
                            "[account-import] image skipped job_id=%s path=%s error=%s",
                            job_id,
                            record.path,
                            exc,
                        )
                        skipped.append(
                            {
                                "path": record.path,
                                "code": "image_import_failed",
                                "message": str(exc) or exc.__class__.__name__,
                            }
                        )
                service.record_media_batch(
                    job_id=job_id,
                    user_id=user_id,
                    results=results,
                    skipped=skipped,
                    warnings=warnings,
                )

            unsupported = [
                {
                    "path": record.path,
                    "code": "unsupported_attachment_family",
                    "message": f"Inventoried but not imported: {record.detected_kind}",
                }
                for record in inventory.attachment_files
                if not record.detected_kind.startswith("image_")
                and record.path not in completed_media_paths
            ]
            if unsupported:
                for start in range(
                    0, len(unsupported), service.limits.media_batch_size
                ):
                    service.record_media_batch(
                        job_id=job_id,
                        user_id=user_id,
                        results=[],
                        skipped=unsupported[
                            start : start + service.limits.media_batch_size
                        ],
                    )

            if not inventory.legacy_detected and not inventory.sharded_detected:
                if not supported_image_records:
                    raise AccountImportError(
                        "No importable conversations or supported images were found.",
                        code="unrecognized_export_structure",
                    )
                service.record_media_batch(
                    job_id=job_id,
                    user_id=user_id,
                    results=[],
                    warnings=[
                        {
                            "code": "conversation_payload_not_found",
                            "message": "Images were retained, but no conversation payload was recognized.",
                        }
                    ],
                )

        service.complete_job(job_id=job_id, user_id=user_id)
        return True
    except Exception as exc:
        logger.exception("[account-import] worker failed job_id=%s", job_id)
        code = exc.code if isinstance(exc, AccountImportError) else "account_import_worker_failed"
        try:
            service.fail_job(
                job_id=job_id,
                user_id=user_id,
                code=code,
                message=str(exc) or exc.__class__.__name__,
            )
        except Exception:
            logger.exception(
                "[account-import] failed to persist terminal failure job_id=%s",
                job_id,
            )
        return False


def run_forever() -> None:
    database_url = _database_url()
    try:
        event_bus.configure_event_store(PostgresChatLogDB(database_url))
        service = OpenAIAccountImportService(db=GuardianDB(database_url))
        recovered = requeue_incomplete_jobs(service)
    except Exception as exc:
        logger.error("[account-import] worker boot failed: %s", exc)
        raise SystemExit(1) from exc

    logger.info(
        "[account-import] worker started queue=%s recovered=%d",
        QUEUE_NAME,
        recovered,
    )
    while True:
        try:
            payload = dequeue_account_import(block=True, timeout=5)
        except RedisTimeoutError:
            continue
        except Exception as exc:
            logger.warning("[account-import] dequeue failed: %s", exc)
            time.sleep(1.0)
            continue
        if payload:
            process_account_import_task(payload, service=service)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
