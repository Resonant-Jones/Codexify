"""Bounded private transport parts; only existing stage_files admits logical files."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from tempfile import TemporaryFile
from typing import Any

from guardian.core.storage import LocalStorageProvider, StorageError
from guardian.protocol_tokens import AccountImportErrorCode, AccountImportStatus
from guardian.services.openai_account_import import (
    AccountImportError, OpenAIAccountImportService, StagedImportFile,
    normalize_import_relative_path,
)

CHUNK_BYTES = 8 * 1024 * 1024
CHUNK_REQUEST_BYTES = CHUNK_BYTES + 64 * 1024
_SHA = re.compile(r"^[a-f0-9]{64}$")


def _fail(code: AccountImportErrorCode, message: str, status: int = 409):
    raise AccountImportError(message, code=code.value, status_code=status)


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _directory(root: Path, *parts: str) -> Path:
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            _fail(AccountImportErrorCode.CHUNK_CONFLICT, "Unsafe private upload path.")
        existed = path.exists()
        path.mkdir(mode=0o700, exist_ok=True)
        if not existed:
            _sync_dir(path.parent)
        if not path.is_dir():
            _fail(AccountImportErrorCode.CHUNK_CONFLICT, "Unsafe private upload path.")
    return path


def _read(path: Path, limit: int) -> bytes:
    if path.is_symlink() or path.stat().st_size > limit:
        _fail(AccountImportErrorCode.CHUNK_CONFLICT, "Private upload data conflicts.")
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        _fail(AccountImportErrorCode.CHUNK_CONFLICT, "Private upload data conflicts.")
    return data


def _metadata(path: Path) -> dict[str, Any] | None:
    if not path.exists() and not path.is_symlink():
        return None
    try:
        result = json.loads(_read(path, 16384))
        if not isinstance(result, dict):
            raise ValueError("not an object")
        return result
    except (ValueError, UnicodeError):
        _fail(AccountImportErrorCode.CHUNK_CONFLICT, "Private upload metadata conflicts.")


def _write_metadata(path: Path, value: dict[str, Any]) -> None:
    pending = path.with_suffix(".next")
    if pending.is_symlink() or path.is_symlink():
        _fail(AccountImportErrorCode.CHUNK_CONFLICT, "Unsafe private upload path.")
    with pending.open("wb") as handle:
        handle.write(json.dumps(value, sort_keys=True).encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(pending, path)
    _sync_dir(path.parent)


def _matches(entry: dict[str, Any] | None, identity: dict[str, Any]) -> bool:
    return bool(entry and all(k in identity and entry.get(k) == identity[k] for k in ("path", "size", "sha256")))


def stage_account_import_chunk(
    service: OpenAIAccountImportService, *, job_id: str, user_id: str,
    relative_path: str, file_size: int, file_sha256: str,
    chunk_sha256: str, offset: int, data: bytes,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Replay one part safely, then admit the verified original through stage_files.

    The job row lock serializes private writes. Parts remain immutable and retained
    after admission, so a lost stage response cannot justify deleting any bytes.
    """
    invalid = AccountImportErrorCode.CHUNK_INVALID
    conflict = AccountImportErrorCode.CHUNK_CONFLICT
    path = normalize_import_relative_path(relative_path)
    if (type(file_size) is not int or type(offset) is not int or
        not 0 < file_size <= min(service.limits.max_file_bytes, service.limits.max_batch_bytes) or
        not 0 <= offset < file_size or offset % CHUNK_BYTES or
        not _SHA.fullmatch(file_sha256) or not _SHA.fullmatch(chunk_sha256) or
        len(data) != min(CHUNK_BYTES, file_size - offset) or
        len(content_type or "") > 256):
        _fail(invalid, "Invalid bounded file upload.", 400)
    if hashlib.sha256(data).hexdigest() != chunk_sha256:
        _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Upload part integrity failed.")
    identity = {"path": path, "size": file_size, "sha256": file_sha256}
    provider = service.staging_storage.provider
    if not isinstance(provider, LocalStorageProvider):
        _fail(AccountImportErrorCode.CHUNK_STORAGE_UNAVAILABLE, "Private chunk storage unavailable.", 503)
    base = provider.base_path.resolve()
    try:
        with service.db.get_session() as session:
            job = service._require_job(session, job_id, user_id, for_update=True)
            if job.status != AccountImportStatus.RECEIVING.value:
                _fail(conflict, "Account import is no longer accepting files.")
            by_path = {str(item["path"]): item for item in (job.staged_manifest or [])}
            existing = by_path.get(path)
            if existing:
                if not _matches(existing, identity):
                    _fail(conflict, "The logical file conflicts with staged content.")
                storage_name = f"{job.staging_locator}/{path}"
                if existing.get("storage_path") != service.staging_storage.get_file_url(storage_name):
                    _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Staged file integrity failed.")
                canonical = base / storage_name
                if (canonical.is_symlink() or not canonical.resolve().is_relative_to(base) or
                    canonical.stat().st_size != file_size):
                    _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Staged file integrity failed.")
                with canonical.open("rb") as handle:
                    handle.seek(offset)
                    if handle.read(len(data)) != data:
                        _fail(conflict, "The upload part conflicts with staged content.")
                    # stage_files already verified the whole-file digest before
                    # durable admission. A retry proves only its claimed range;
                    # rehashing 2 GiB on every 8 MiB replay enables I/O amplification.
                return {"job": service.serialize_job(job), "received_bytes": file_size, "complete": True}
            # This is admission checking, not a reservation against raw uploads.
            # The existing final stage_files transaction checks these again.
            if (int(job.uploaded_file_count or 0) + 1 > job.total_file_count or
                int(job.uploaded_byte_count or 0) + file_size > job.total_byte_count):
                _fail(invalid, "The logical file exceeds the remaining declaration.", 413)
            owner = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
            scope = _directory(base, ".account-import-parts", owner,
                               hashlib.sha256(str(job.id).encode()).hexdigest())
            active = _metadata(scope / "active.json")
            if active and active != identity and not _matches(by_path.get(str(active.get("path"))), active):
                _fail(conflict, "Finish the existing private file upload before another file.")
            key = hashlib.sha256(path.encode()).hexdigest()
            parts = _directory(scope, key, f"{file_sha256}-{file_size}")
            metadata = {**identity, "content_type": content_type}
            pinned = _metadata(parts / "metadata.json")
            if pinned is not None and pinned != metadata:
                _fail(conflict, "The private file identity changed.")
            if pinned is None:
                _write_metadata(parts / "metadata.json", metadata)
            if active != identity:
                _write_metadata(scope / "active.json", identity)
            received = 0
            for start in range(0, file_size, CHUNK_BYTES):
                part = parts / f"{start}.part"
                if not part.exists() and not part.is_symlink():
                    break
                if part.is_symlink() or part.stat().st_size != min(CHUNK_BYTES, file_size - start):
                    _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Stored upload part integrity failed.")
                received += part.stat().st_size
            if offset > received:
                _fail(conflict, "Upload offset is ahead of the verified prefix.")
            part = parts / f"{offset}.part"
            if offset < received:
                if _read(part, CHUNK_BYTES) != data:
                    _fail(conflict, "The replayed upload part conflicts.")
            else:
                pending = parts / f"{offset}.pending"
                prefix = _read(pending, CHUNK_BYTES) if pending.exists() or pending.is_symlink() else b""
                if not data.startswith(prefix):
                    _fail(conflict, "The interrupted upload part conflicts.")
                with pending.open("ab") as handle:
                    handle.write(data[len(prefix):])
                    handle.flush()
                    os.fsync(handle.fileno())
                if _read(pending, CHUNK_BYTES) != data:
                    _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Upload part persistence failed.")
                os.replace(pending, part)
                _sync_dir(parts)
                received += len(data)
            snapshot = service.serialize_job(job)
        if received < file_size:
            return {"job": snapshot, "received_bytes": received, "complete": False}
        # Immutable parts survive this lock boundary. stage_files owns its own
        # row lock, original path/hash/size conflicts, counters and transaction.
        with TemporaryFile() as assembled:
            digest = hashlib.sha256()
            size = 0
            for start in range(0, file_size, CHUNK_BYTES):
                part = parts / f"{start}.part"
                if part.is_symlink() or part.stat().st_size != min(CHUNK_BYTES, file_size - start):
                    _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Stored upload part integrity failed.")
                with part.open("rb") as source:
                    while block := source.read(1024 * 1024):
                        size += len(block)
                        if size > file_size:
                            _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Assembled file size conflicts.")
                        digest.update(block)
                        assembled.write(block)
            if size != file_size or digest.hexdigest() != file_sha256:
                _fail(AccountImportErrorCode.CHUNK_INTEGRITY, "Whole-file integrity failed; parts retained.")
            assembled.seek(0)
            job_snapshot = service.stage_files(job_id=job_id, user_id=user_id,
                files=[StagedImportFile(relative_path=path, stream=assembled,
                                        content_type=content_type)])
        return {"job": job_snapshot, "received_bytes": file_size, "complete": True}
    except (OSError, StorageError) as exc:
        raise AccountImportError("Private upload storage unavailable; bytes retained.",
            code=AccountImportErrorCode.CHUNK_STORAGE_UNAVAILABLE.value, status_code=503) from exc
