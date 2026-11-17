"""Owner-authorized, terminal-job repair of one immutable retained PDF.

Generic zero-write retry, original checkpoints, and historical warnings stay intact.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from backend.rag.openai_export_adapter import (
    OpenAIExportDetector,
    OpenAIExportFileRecord,
    _detect_magic_kind,
    _looks_textual,
    build_openai_export_image_evidence_index,
    resolve_openai_export_image_evidence,
)
from guardian.core.storage import LocalStorageProvider
from guardian.db.models import (
    ChatThread,
    MediaAsset,
    OpenAIAccountImportJob,
    Project,
    ProjectDocumentLink,
    ThreadDocument,
    UploadedDocument,
)
from guardian.protocol_tokens import AccountImportErrorCode as Code, AccountImportStatus
from guardian.services.document_parsers import PdfTextExtractionError, extract_pdf_text
from guardian.services.media_identity import (
    compute_identity,
    source_label_from_filename,
)
from guardian.services.openai_account_import import (
    AccountImportError,
    normalize_import_relative_path,
)

MAX_FILES = 10000
MAX_VERIFIED_BYTES = 8 * 1024**3
MAX_METADATA_BYTES = 768 * 1024**2
MAX_PDF_BYTES = 16 * 1024**2
PRE_PERSISTENCE_SECONDS = 300
MAX_EVENTS = 256
_SHA = re.compile(r"^[a-f0-9]{64}$")
_EVENT_KEYS = {
    "repair_key",
    "attempt_id",
    "path",
    "size",
    "sha256",
    "requested_at",
    "verified_at",
    "requires_admission",
    "completed_at",
    "failed_at",
    "error_code",
    "asset_id",
    "document_id",
    "credited",
    "text_extracted",
}


def _fail(code, message, status=409):
    raise AccountImportError(message, code=code.value, status_code=status)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _key(job_id):
    return int.from_bytes(
        hashlib.sha256(("codexify:pdf-repair:" + job_id).encode()).digest()[:8], "big"
    ) & ((1 << 63) - 1)


def _engine(service):
    with service.db.get_session() as session:
        engine = session.get_bind()
    if engine.dialect.name != "postgresql":
        _fail(
            Code.MEDIA_REPAIR_UNAVAILABLE,
            "Retained PDF repair requires its qualified local PostgreSQL path.",
            503,
        )
    return engine


@contextmanager
def _exclusive(service, job_id):
    # The connection stays checked out across canonical writer transactions.
    with _engine(service).connect() as connection:
        locked = connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": _key(job_id)}
        ).scalar_one()
        connection.commit()
        if not locked:
            _fail(
                Code.MEDIA_REPAIR_BUSY,
                "Another retained-file repair is active for this job.",
            )
        try:
            yield
        finally:
            connection.rollback()
            connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": _key(job_id)}
            )
            connection.commit()


def _busy(service, job_id):
    key = _key(job_id)
    with _engine(service).connect() as connection:
        return bool(
            connection.execute(
                text(
                    """SELECT EXISTS(SELECT 1 FROM pg_locks
            WHERE locktype='advisory' AND granted AND objsubid=1
            AND database=(SELECT oid FROM pg_database WHERE datname=current_database())
            AND classid::bigint=:high AND objid::bigint=:low)"""
                ),
                {"high": key >> 32, "low": key & 0xFFFFFFFF},
            ).scalar_one()
        )


def get_pdf_repair_audit(service, *, job_id, user_id):
    with service.db.get_session() as session:
        job = service._require_job(session, job_id, user_id)
        events = list((job.checkpoint or {}).get("pdf_repair_events") or [])
        payload = {
            "job": service.serialize_job(job),
            "events": [
                {k: v for k, v in event.items() if k in _EVENT_KEYS}
                for event in events[-64:]
            ],
        }
    payload["busy"] = _busy(service, job_id)
    return payload


def _gate(service, job_id, user_id, fingerprint):
    with service.db.get_session() as session:
        job = service._require_job(session, job_id, user_id)
        if (
            job.status != AccountImportStatus.COMPLETED_WITH_WARNINGS.value
            or job.source_system != "openai"
        ):
            _fail(
                Code.MEDIA_REPAIR_INVALID,
                "Retained PDF repair requires a completed OpenAI import with warnings.",
            )
        if not fingerprint or fingerprint != job.source_export_fingerprint:
            _fail(Code.MEDIA_REPAIR_INTEGRITY, "The accepted export identity changed.")
        active = (
            session.query(OpenAIAccountImportJob.id)
            .filter(
                OpenAIAccountImportJob.user_id == user_id,
                OpenAIAccountImportJob.status.in_(
                    [
                        AccountImportStatus.QUEUED.value,
                        AccountImportStatus.RUNNING.value,
                    ]
                ),
            )
            .first()
        )
        if active:
            _fail(
                Code.MEDIA_REPAIR_BUSY,
                "Let the active account import finish before repairing retained files.",
            )
        return service.serialize_job(job, include_internal=True)


def _event(service, job_id, user_id, event, *, credit=False):
    with service.db.get_session() as session:
        session.execute(text("SET LOCAL statement_timeout = '30000ms'"))
        session.execute(text("SET LOCAL lock_timeout = '2000ms'"))
        job = service._require_job(session, job_id, user_id, for_update=True)
        checkpoint = dict(job.checkpoint or {})
        events = list(checkpoint.get("pdf_repair_events") or [])
        credits = list(checkpoint.get("pdf_repair_credits") or [])
        if credit and event["repair_key"] not in credits:
            job.imported_media_count = int(job.imported_media_count or 0) + 1
            checkpoint["imported_document_count"] = (
                int(checkpoint.get("imported_document_count", 0)) + 1
            )
            credits.append(event["repair_key"])
            event = {**event, "credited": True}
        elif credit:
            event = {**event, "credited": False}
        events.append(dict(event))
        checkpoint["pdf_repair_events"] = events
        checkpoint["pdf_repair_credits"] = credits
        job.checkpoint = checkpoint
        flag_modified(job, "checkpoint")
        job.updated_at = datetime.now(timezone.utc)
        session.commit()


def _deadline(deadline):
    if time.monotonic() >= deadline:
        _fail(
            Code.MEDIA_REPAIR_LIMIT,
            "Retained-file verification exceeded its pre-persistence deadline.",
            408,
        )


@contextmanager
def _open(base, relative):
    parts = Path(normalize_import_relative_path(relative)).parts
    descriptors = []
    try:
        current = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(current)
        for part in parts[:-1]:
            current = os.open(
                part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current
            )
            descriptors.append(current)
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=current)
        with os.fdopen(fd, "rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                _fail(
                    Code.MEDIA_REPAIR_INTEGRITY,
                    "A retained path is not a regular file.",
                )
            yield handle
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def _local(storage):
    if not isinstance(storage.provider, LocalStorageProvider):
        _fail(
            Code.MEDIA_REPAIR_UNAVAILABLE,
            "Retained PDF repair requires private local storage.",
            503,
        )
    return storage.provider.base_path.resolve()


def _manifest(snapshot, path, size, sha):
    entries = list(snapshot["staged_manifest"])
    if (
        len(entries) > MAX_FILES
        or sum(int(e["size"]) for e in entries) > MAX_VERIFIED_BYTES
    ):
        _fail(
            Code.MEDIA_REPAIR_LIMIT,
            "The retained export exceeds this repair's verification limits.",
            413,
        )
    by_path = {str(e["path"]): e for e in entries}
    if (
        len(by_path) != len(entries)
        or len(entries) != snapshot["total_file_count"]
        or sum(int(e["size"]) for e in entries) != snapshot["total_byte_count"]
    ):
        _fail(Code.MEDIA_REPAIR_INTEGRITY, "The accepted manifest does not verify.")
    digest = hashlib.sha256(
        json.dumps(
            [
                [e["path"], e["sha256"], e["size"]]
                for e in sorted(entries, key=lambda e: str(e["path"]))
            ],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()
    item = by_path.get(path)
    if (
        digest != snapshot["source_export_fingerprint"]
        or not item
        or item["size"] != size
        or item["sha256"] != sha
    ):
        _fail(
            Code.MEDIA_REPAIR_INTEGRITY,
            "The retained file identity does not match the accepted export.",
        )
    if path not in (snapshot["checkpoint"].get("media_paths") or []):
        _fail(
            Code.MEDIA_REPAIR_INVALID,
            "This retained file has not completed its original media attempt.",
        )
    return entries


def _verified_evidence(service, snapshot, path, workspace, deadline):
    base = _local(service.staging_storage)
    locator = str(snapshot["staging_locator"]).strip("/")
    descriptors = []
    copied = 0
    for item in snapshot["staged_manifest"]:
        _deadline(deadline)
        relative = str(item["path"])
        if normalize_import_relative_path(relative) != relative:
            _fail(Code.MEDIA_REPAIR_INTEGRITY, "A retained path is not canonical.")
        name = normalize_import_relative_path(f"{locator}/{relative}")
        if item.get("storage_path") != service.staging_storage.get_file_url(name):
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "A retained locator does not belong to this job.",
            )
        with _open(base, name) as source:
            if os.fstat(source.fileno()).st_size != int(item["size"]):
                _fail(Code.MEDIA_REPAIR_INTEGRITY, "Retained file size changed.")
            first = source.read(1024 * 1024)
            magic = _detect_magic_kind(first[:4096])
            sample = first[:4096]
            stripped = sample.lstrip()
            # Match the normal classifier's structured probes before UTF-8 text
            # heuristics, including a multibyte glyph split at the sample edge.
            structured = stripped[:1] in {b"{", b"["} or stripped[
                :256
            ].lower().startswith((b"<!doctype html", b"<html", b"<!--"))
            include = relative == path or (
                magic is None and (structured or _looks_textual(sample))
            )
            sink = None
            try:
                if include:
                    target = workspace / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    sink = target.open("xb")
                digest, count = hashlib.sha256(), 0
                block = first
                while block:
                    _deadline(deadline)
                    count += len(block)
                    if count > int(item["size"]):
                        _fail(
                            Code.MEDIA_REPAIR_INTEGRITY,
                            "Retained file grew during verification.",
                        )
                    digest.update(block)
                    if sink:
                        if relative != path:
                            copied += len(block)
                            if copied > MAX_METADATA_BYTES:
                                _fail(
                                    Code.MEDIA_REPAIR_LIMIT,
                                    "Retained metadata exceeds the repair limit.",
                                    413,
                                )
                        sink.write(block)
                    block = source.read(1024 * 1024)
                if count != int(item["size"]) or digest.hexdigest() != item["sha256"]:
                    _fail(
                        Code.MEDIA_REPAIR_INTEGRITY,
                        "Retained bytes do not match their accepted identity.",
                    )
            finally:
                if sink:
                    sink.close()
            if not include:
                descriptors.append(
                    OpenAIExportFileRecord(
                        path=relative,
                        absolute_path=str(base / name),
                        size=count,
                        extension=Path(relative).suffix,
                        detected_kind=magic or "unknown_binary",
                        first_bytes_hex=first[:32].hex(),
                        magic_signature=magic or "unknown",
                    )
                )
    _deadline(deadline)
    inventory = OpenAIExportDetector().scan(workspace)
    inventory.files.extend(
        descriptors
    )  # Preserve every accepted asset alias, including conflicts.
    if len(inventory.files) != len(snapshot["staged_manifest"]):
        _fail(
            Code.MEDIA_REPAIR_INTEGRITY, "Retained evidence coverage does not verify."
        )
    record = next((e for e in inventory.files if e.path == path), None)
    if record is None or record.detected_kind != "pdf":
        _fail(
            Code.MEDIA_REPAIR_INVALID,
            "Only a magic-verified retained PDF can be repaired.",
            400,
        )
    index = build_openai_export_image_evidence_index(inventory)
    _deadline(deadline)
    return record, resolve_openai_export_image_evidence(path, index)


def _project(service, user_id, evidence):
    with service.db.get_session() as session:
        primary = service._resolve_source_thread(
            session, user_id=user_id, source_thread_id=evidence.source_thread_id
        )
        for cid in {e.source_thread_id for e in evidence.relationships} | {
            evidence.source_thread_id
        }:
            thread = service._resolve_source_thread(
                session, user_id=user_id, source_thread_id=cid
            )
            if thread is not None and thread.project_id is not None:
                project = session.get(Project, thread.project_id)
                if project is None or str(project.user_id) != user_id:
                    _fail(
                        Code.MEDIA_REPAIR_INTEGRITY,
                        "Source Project ownership does not verify.",
                    )
        if primary is not None and primary.project_id is not None:
            return int(primary.project_id)
        project = (
            session.query(Project)
            .filter(Project.user_id == user_id, Project.name == "Imports")
            .first()
        )
        if project is None:
            name = "Imports"
            if session.query(Project.id).filter(Project.name == name).first():
                name = (
                    "Imports (" + hashlib.sha256(user_id.encode()).hexdigest()[:8] + ")"
                )
            project = (
                session.query(Project)
                .filter(Project.user_id == user_id, Project.name == name)
                .first()
            )
        if project is None:
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "An existing owned import Project is required.",
            )
        return int(project.id)


def _verify_blob(storage, name, sha, size):
    base = _local(storage)
    with _open(base, name) as handle:
        digest, count = hashlib.sha256(), 0
        while block := handle.read(1024 * 1024):
            count += len(block)
            if count > size:
                _fail(Code.MEDIA_REPAIR_INTEGRITY, "Stored original size conflicts.")
            digest.update(block)
        if count != size or digest.hexdigest() != sha:
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Stored original integrity does not verify.",
            )


def _existing(service, user_id, project_id, job_id, path, sha, size, fingerprint):
    with service.db.get_session() as session:
        project = session.get(Project, project_id)
        if project is None or str(project.user_id) != user_id:
            _fail(Code.MEDIA_REPAIR_INTEGRITY, "Repair Project ownership changed.")
        matches = (
            session.query(MediaAsset)
            .filter_by(
                project_id=project_id,
                media_kind="document",
                provenance="imported",
                content_hash=sha,
            )
            .all()
        )
        if any(e.deleted_at is not None for e in matches) or len(matches) > 1:
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Conflicting or deleted document assets require operator review.",
            )
        asset = matches[0] if matches else None
        if asset is None:
            return None, False
        if (
            str(asset.user_id) != user_id
            or int(asset.filesize or 0) != size
            or asset.mime_type != "application/pdf"
        ):
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Existing document scope or identity conflicts.",
            )
        name = f"{asset.storage_prefix}{asset.system_name}"
        if asset.src_url != service.media_storage.get_file_url(name):
            _fail(Code.MEDIA_REPAIR_INTEGRITY, "Existing document locator conflicts.")
        _verify_blob(service.media_storage, name, sha, size)
        documents = (
            session.query(UploadedDocument)
            .filter(UploadedDocument.asset_id == asset.id)
            .all()
        )
        lineage = any(
            e.get("import_job_id") == job_id
            and e.get("source_relative_path") == path
            and e.get("source_export_id") == fingerprint
            for e in (asset.import_lineage or [])
        )
        if not lineage:
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Existing imported document lineage does not verify for this retained path.",
            )
        if any(e.deleted_at is not None for e in documents):
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Retained-file repair does not restore deleted documents.",
            )
        document = documents[0] if len(documents) == 1 else None
        if len(documents) > 1 or (
            document is not None
            and (
                str(document.user_id) != user_id
                or document.project_id != project_id
                or document.src_url != asset.src_url
                or document.filesize != size
                or document.mime_type != "application/pdf"
            )
        ):
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Existing document ownership or locator conflicts.",
            )
        for thread_id in {asset.thread_id, document.thread_id if document else None} - {
            None
        }:
            thread = session.get(ChatThread, thread_id)
            if (
                thread is None
                or str(thread.user_id) != user_id
                or thread.project_id not in {None, project_id}
            ):
                _fail(
                    Code.MEDIA_REPAIR_INTEGRITY,
                    "Existing attachment thread ownership conflicts.",
                )
        if document is None:
            return None, True
        if (
            session.query(ProjectDocumentLink.id)
            .filter_by(
                project_id=project_id, document_id=document.id, document_type="uploaded"
            )
            .first()
            is None
        ):
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY,
                "Existing document Project link is missing.",
            )
        if asset.thread_id is not None and (
            document.thread_id != asset.thread_id
            or session.query(ThreadDocument.id)
            .filter_by(
                thread_id=asset.thread_id, document_id=document.id, relation="attached"
            )
            .first()
            is None
        ):
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY, "Existing document thread link is missing."
            )
        return {
            "asset_id": asset.id,
            "document_id": document.id,
            "text_extracted": bool(document.parsed_text),
        }, True


class _WriterDB:
    def __init__(self, original):
        self.original = original

    def get_session(self):
        session = self.original.get_session()
        try:
            session.execute(text("SET LOCAL statement_timeout = '30000ms'"))
            session.execute(text("SET LOCAL lock_timeout = '2000ms'"))
            return session
        except Exception:
            session.close()
            raise


def _verify_completed(
    service, snapshot, receipt, user_id, path, size, sha, fingerprint
):
    item = next(e for e in snapshot["staged_manifest"] if e["path"] == path)
    name = normalize_import_relative_path(
        f"{snapshot['staging_locator'].strip('/')}/{path}"
    )
    if item.get("storage_path") != service.staging_storage.get_file_url(name):
        _fail(Code.MEDIA_REPAIR_INTEGRITY, "The retained locator changed.")
    _verify_blob(service.staging_storage, name, sha, size)
    with service.db.get_session() as session:
        asset = session.get(MediaAsset, receipt.get("asset_id"))
        if asset is None or str(asset.user_id) != user_id:
            _fail(
                Code.MEDIA_REPAIR_INTEGRITY, "The recorded repair no longer verifies."
            )
        project_id = asset.project_id
    ready, _ = _existing(
        service, user_id, project_id, snapshot["job_id"], path, sha, size, fingerprint
    )
    if (
        ready is None
        or ready["document_id"] != receipt.get("document_id")
        or ready["asset_id"] != receipt.get("asset_id")
    ):
        _fail(Code.MEDIA_REPAIR_INTEGRITY, "The recorded repair no longer verifies.")


def repair_retained_pdf(
    service,
    *,
    job_id,
    user_id,
    relative_path,
    file_size,
    file_sha256,
    source_export_fingerprint,
):
    path = normalize_import_relative_path(relative_path)
    if (
        type(file_size) is not int
        or not 0 < file_size <= MAX_PDF_BYTES
        or not _SHA.fullmatch(file_sha256 or "")
    ):
        _fail(
            Code.MEDIA_REPAIR_INVALID,
            "Retained PDF identity is invalid or exceeds 16 MiB.",
            400,
        )
    _gate(
        service, job_id, user_id, source_export_fingerprint
    )  # Authorize before lock visibility.
    _local(service.staging_storage)
    _local(service.media_storage)
    key = hashlib.sha256(
        json.dumps(
            [job_id, path, file_size, file_sha256, source_export_fingerprint],
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    with _exclusive(service, job_id):
        snapshot = _gate(service, job_id, user_id, source_export_fingerprint)
        _manifest(snapshot, path, file_size, file_sha256)
        events = list(snapshot["checkpoint"].get("pdf_repair_events") or [])
        completed = next(
            (
                e
                for e in reversed(events)
                if e.get("repair_key") == key and e.get("completed_at")
            ),
            None,
        )
        if completed:
            _verify_completed(
                service,
                snapshot,
                completed,
                user_id,
                path,
                file_size,
                file_sha256,
                source_export_fingerprint,
            )
        else:
            _perform_repair(
                service,
                snapshot,
                events,
                key,
                job_id,
                user_id,
                path,
                file_size,
                file_sha256,
                source_export_fingerprint,
            )
    return get_pdf_repair_audit(service, job_id=job_id, user_id=user_id)


def _perform_repair(
    service,
    snapshot,
    events,
    key,
    job_id,
    user_id,
    path,
    file_size,
    file_sha256,
    source_export_fingerprint,
):
    if len(events) > MAX_EVENTS - 4:
        _fail(
            Code.MEDIA_REPAIR_LIMIT,
            "This repair's retained audit limit requires operator review.",
            413,
        )
    attempt = str(uuid4())
    common = {
        "repair_key": key,
        "attempt_id": attempt,
        "path": path,
        "size": file_size,
        "sha256": file_sha256,
    }
    _event(service, job_id, user_id, {**common, "requested_at": _now()})
    try:
        deadline = time.monotonic() + PRE_PERSISTENCE_SECONDS
        with TemporaryDirectory(prefix="codexify-pdf-repair-") as scratch:
            record, evidence = _verified_evidence(
                service, snapshot, path, Path(scratch), deadline
            )
            data = Path(record.absolute_path).read_bytes()
            try:
                parsed = extract_pdf_text(data)
            except PdfTextExtractionError:
                parsed = None
            _deadline(deadline)
            project_id = _project(service, user_id, evidence)
            ready, asset_exists = _existing(
                service,
                user_id,
                project_id,
                job_id,
                path,
                file_sha256,
                file_size,
                source_export_fingerprint,
            )
            prior_needed = any(
                e.get("repair_key") == key and e.get("requires_admission")
                for e in events
            )
            needs_credit = ready is None or (
                prior_needed
                and key not in snapshot["checkpoint"].get("pdf_repair_credits", [])
            )
            _event(
                service,
                job_id,
                user_id,
                {**common, "verified_at": _now(), "requires_admission": needs_credit},
            )
            if ready is None:
                if not asset_exists:
                    identity = compute_identity(
                        file_data=data,
                        media_kind="document",
                        provenance="uploaded",
                        human_label=source_label_from_filename(
                            Path(path).name, fallback="imported-document"
                        ),
                        original_filename=None,
                        mime_type="application/pdf",
                        first_seen_at=datetime.fromisoformat(snapshot["created_at"]),
                        content_hash=file_sha256,
                    )
                    name = f"{identity.storage_prefix}{identity.system_name}"
                    # Existing orphan originals may be reused only byte-for-byte.
                    try:
                        _verify_blob(
                            service.media_storage, name, file_sha256, file_size
                        )
                    except FileNotFoundError:
                        pass
                _gate(service, job_id, user_id, source_export_fingerprint)
                _deadline(
                    deadline
                )  # No late parsing may initiate canonical persistence.
                writer = copy.copy(service)
                writer.db = _WriterDB(service.db)
                writer._import_document_bytes(
                    job_id=job_id,
                    user_id=user_id,
                    path=path,
                    filename=Path(path).name,
                    data=data,
                    mime_type="application/pdf",
                    parsed_text=parsed,
                    evidence=evidence,
                    origin_system="openai",
                )
                ready, _ = _existing(
                    service,
                    user_id,
                    project_id,
                    job_id,
                    path,
                    file_sha256,
                    file_size,
                    source_export_fingerprint,
                )
                if ready is None:
                    _fail(
                        Code.MEDIA_REPAIR_INTEGRITY,
                        "Canonical document admission did not verify.",
                    )
            _event(
                service,
                job_id,
                user_id,
                {**common, **ready, "completed_at": _now()},
                credit=needs_credit,
            )
    except Exception as exc:
        code = (
            exc.code
            if isinstance(exc, AccountImportError)
            else Code.MEDIA_REPAIR_UNAVAILABLE.value
        )
        try:
            _event(
                service,
                job_id,
                user_id,
                {**common, "failed_at": _now(), "error_code": code},
            )
        except Exception:
            pass  # The prior durable request remains evidence of an ambiguous outcome.
        if isinstance(exc, AccountImportError):
            raise
        raise AccountImportError(
            "Retained PDF repair did not complete; source and audit were retained.",
            code=code,
            status_code=503,
        ) from exc
