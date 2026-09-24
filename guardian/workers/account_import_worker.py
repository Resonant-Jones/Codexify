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
from backend.rag.anthropic_export_adapter import (
    import_anthropic_export_path as import_anthropic_export_conversations,
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


class AccountImportEmbeddingHandoffRetryable(RuntimeError):
    """Keep a committed import job recoverable when Redis handoff fails."""


def _handoff_committed_embeddings(
    service: OpenAIAccountImportService,
    *,
    job_id: str,
    user_id: str,
    conversation_ids: list[str] | None = None,
) -> None:
    try:
        service.enqueue_pending_import_embeddings(
            job_id=job_id,
            user_id=user_id,
            conversation_ids=conversation_ids,
        )
    except AccountImportError:
        raise
    except Exception as exc:
        raise AccountImportEmbeddingHandoffRetryable(
            f"Import embedding handoff failed for job {job_id}"
        ) from exc


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
            checkpoint = dict(snapshot.get("checkpoint") or {})
            source_summary: dict[str, int | bool] = {
                "conversations_discovered": 0,
                "conversations_accepted": 0,
                "conversations_skipped": 0,
                "conversations_failed": 0,
                "conversation_transactions_committed": False,
            }

            job_source_system = (
                str(snapshot.get("source_system") or "").strip().lower()
            )

            if job_source_system == "openai":
                # A crash after the durable batch checkpoint but before Redis
                # enqueue leaves the job running. Startup requeues that job;
                # its checkpointed conversations are reconciled here before
                # the importer skips them on resume.
                _handoff_committed_embeddings(
                    service, job_id=job_id, user_id=user_id
                )

            if job_source_system == "anthropic":
                anthropic_result = import_anthropic_export_conversations(
                    export_root,
                    user_id=user_id,
                )
                if anthropic_result.errors:
                    raise RuntimeError(
                        "; ".join(anthropic_result.errors[:5])
                    )
                source_summary = {
                    "conversations_discovered": anthropic_result.conversations_discovered,
                    "conversations_accepted": anthropic_result.conversations_accepted,
                    "conversations_skipped": max(
                        0,
                        anthropic_result.conversations_discovered
                        - anthropic_result.conversations_accepted
                        - anthropic_result.conversations_failed,
                    ),
                    "conversations_failed": anthropic_result.conversations_failed,
                    "conversation_transactions_committed": (
                        anthropic_result.conversations_imported > 0
                        or anthropic_result.canonical_duplicate_count > 0
                    ),
                }
                service.record_source_summary(
                    job_id=job_id,
                    user_id=user_id,
                    summary=source_summary,
                )
                # Credit the canonical writer's authoritative committed totals
                # onto the durable job BEFORE terminal classification. The
                # adapter result carries writer-derived thread/message counts
                # (never source-discovery totals); without this accounting,
                # ``complete_job`` would reject the internally inconsistent
                # zero-counter job even though persistence succeeded.
                service.record_committed_conversation_totals(
                    job_id=job_id,
                    user_id=user_id,
                    threads_imported=anthropic_result.conversations_imported,
                    messages_imported=anthropic_result.messages_imported,
                    canonical_duplicate_count=anthropic_result.canonical_duplicate_count,
                    phase_key="anthropic_conversations",
                )
                completed_media_paths = {
                    str(value) for value in checkpoint.get("media_paths", [])
                }
                documents = [
                    item for item in anthropic_result.documents
                    if item.path not in completed_media_paths
                ]
                for start in range(0, len(documents), service.limits.media_batch_size):
                    results: list[dict[str, Any]] = []
                    skipped: list[dict[str, Any]] = []
                    for item in documents[start:start + service.limits.media_batch_size]:
                        try:
                            results.append(service.import_text_document_record(
                                job_id=job_id,
                                user_id=user_id,
                                path=item.path,
                                source_filename=item.source_filename,
                                content=item.content,
                                source_thread_id=item.source_thread_id,
                                source_message_id=item.source_message_id,
                                source_project_id=item.source_project_id,
                                source_document_id=item.source_document_id,
                            ))
                        except Exception as exc:
                            logger.warning(
                                "[account-import] Claude text document skipped job_id=%s path=%s error=%s",
                                job_id, item.path, exc,
                            )
                            skipped.append({
                                "path": item.path,
                                "code": "document_import_failed",
                                "message": str(exc) or exc.__class__.__name__,
                            })
                    service.record_media_batch(
                        job_id=job_id, user_id=user_id,
                        results=results, skipped=skipped,
                    )
                missing_originals = [
                    {
                        "path": f"anthropic/reference-only/{index}",
                        "code": "source_binary_unavailable",
                        "message": "Source export contained a file reference without original bytes.",
                    }
                    for index in range(anthropic_result.reference_only_count)
                    if f"anthropic/reference-only/{index}" not in completed_media_paths
                ]
                for start in range(0, len(missing_originals), service.limits.media_batch_size):
                    service.record_media_batch(
                        job_id=job_id, user_id=user_id,
                        results=[],
                        skipped=missing_originals[start:start + service.limits.media_batch_size],
                    )
                service.complete_job(job_id=job_id, user_id=user_id)
                return True

            report = diagnose_openai_export_path(export_root)
            inventory = report.inventory
            if inventory.legacy_detected or inventory.sharded_detected:
                handoff_failure: AccountImportEmbeddingHandoffRetryable | None = None

                def record_batch_and_handoff(batch: dict[str, Any]) -> None:
                    nonlocal handoff_failure
                    service.record_conversation_batch(
                        job_id=job_id,
                        user_id=user_id,
                        batch=batch,
                    )
                    try:
                        _handoff_committed_embeddings(
                            service,
                            job_id=job_id,
                            user_id=user_id,
                            conversation_ids=list(batch.get("conversation_ids") or []),
                        )
                    except AccountImportEmbeddingHandoffRetryable as exc:
                        handoff_failure = exc
                        raise

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
                    on_batch_committed=record_batch_and_handoff,
                )
                # The importer turns callback exceptions into diagnostics; keep
                # the handoff's retryable classification across that boundary.
                if handoff_failure is not None:
                    raise handoff_failure
                if diagnostics.errors:
                    raise RuntimeError("; ".join(diagnostics.errors[:5]))
                if diagnostics.conversations_discovered == 0:
                    raise AccountImportError(
                        "No conversations were found in the selected OpenAI export.",
                        code="unrecognized_export_structure",
                    )
                source_summary = {
                    "conversations_discovered": diagnostics.conversations_discovered,
                    "conversations_accepted": diagnostics.conversations_accepted,
                    "conversations_skipped": (
                        diagnostics.conversations_skipped_title
                        + diagnostics.conversations_skipped_limit
                        + diagnostics.conversations_skipped_duplicate
                        + diagnostics.conversations_skipped_checkpoint
                    ),
                    "conversations_failed": diagnostics.conversations_failed,
                    "conversation_transactions_committed": diagnostics.text_import_complete,
                }
            if source_summary["conversations_discovered"] == 0:
                raise AccountImportError(
                    "No conversations were found in the selected OpenAI export.",
                    code="unrecognized_export_structure",
                )
            service.record_source_summary(
                job_id=job_id,
                user_id=user_id,
                summary=source_summary,
            )

            evidence_index = build_openai_export_image_evidence_index(inventory)
            completed_media_paths = {
                str(value) for value in checkpoint.get("media_paths", [])
            }
            supported_asset_records = [
                record
                for record in inventory.files
                if record.detected_kind
                in {"image_png", "image_jpeg", "image_gif", "image_webp", "pdf"}
            ]
            asset_records = [
                record
                for record in supported_asset_records
                if record.path not in completed_media_paths
            ]
            for start in range(0, len(asset_records), service.limits.media_batch_size):
                results: list[dict[str, Any]] = []
                skipped: list[dict[str, Any]] = []
                warnings: list[dict[str, Any]] = []
                for record in asset_records[
                    start : start + service.limits.media_batch_size
                ]:
                    try:
                        evidence = resolve_openai_export_image_evidence(
                            record.path, evidence_index
                        )
                        importer = (
                            service.import_pdf_record
                            if record.detected_kind == "pdf"
                            else service.import_image_record
                        )
                        outcome = importer(
                            job_id=job_id,
                            user_id=user_id,
                            record=record,
                            evidence=evidence,
                        )
                        results.append(outcome)
                        if evidence.source_tag == "unclassified":
                            warnings.append(
                                {
                                    "path": record.path,
                                    "code": (
                                        "document_provenance_unclassified"
                                        if record.detected_kind == "pdf"
                                        else "image_provenance_unclassified"
                                    ),
                                    "message": (
                                        "Asset retained without provable uploaded "
                                        "or generated provenance."
                                    ),
                                    "evidence_kind": evidence.evidence_kind,
                                }
                            )
                        if record.detected_kind == "pdf" and not outcome.get("text_extracted", True):
                            warnings.append({
                                "path": record.path,
                                "code": "document_text_unavailable",
                                "message": "PDF retained, but no searchable text could be extracted.",
                            })
                    except Exception as exc:
                        logger.warning(
                            "[account-import] asset skipped job_id=%s path=%s error=%s",
                            job_id,
                            record.path,
                            exc,
                        )
                        skipped.append(
                            {
                                "path": record.path,
                                "code": "document_import_failed" if record.detected_kind == "pdf" else "image_import_failed",
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
                and record.detected_kind != "pdf"
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
    except AccountImportEmbeddingHandoffRetryable:
        # The checkpoint and canonical rows remain durable. Do not classify a
        # transient Redis handoff as a terminal import failure: retry this
        # running job here, or through startup recovery after a crash.
        logger.exception("[account-import] embedding handoff deferred job_id=%s", job_id)
        raise
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
            while True:
                try:
                    process_account_import_task(payload, service=service)
                    break
                except AccountImportEmbeddingHandoffRetryable:
                    time.sleep(5.0)


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    run_forever()
