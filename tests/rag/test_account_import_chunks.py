from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from guardian.services import account_import_chunks as chunks
from guardian.services.openai_account_import import AccountImportError, StagedImportFile
from tests.rag.test_openai_export_account_import import account_import_service


def digest(value):
    return hashlib.sha256(value).hexdigest()


@pytest.fixture(autouse=True)
def small_parts(monkeypatch):
    monkeypatch.setattr(chunks, "CHUNK_BYTES", 4)


def job(service, size=10, count=1):
    return service.create_job(user_id="account-a", total_file_count=count, total_byte_count=size)


def send(service, record, body=b"abcdefghij", offset=0, **overrides):
    data = body[offset:offset + 4]
    arguments = dict(job_id=record["job_id"], user_id="account-a", relative_path="export/movie.dat",
                     file_size=len(body), file_sha256=digest(body), chunk_sha256=digest(data),
                     offset=offset, data=data, content_type="video/mp4")
    arguments.update(overrides)
    return chunks.stage_account_import_chunk(service, **arguments)


def test_parts_become_one_original_logical_file_only_after_whole_verification(account_import_service):
    service, _sessions, trace, staging, _media = account_import_service
    record = job(service)
    first = send(service, record)
    assert first["received_bytes"] == 4 and not first["complete"]
    assert first["job"]["uploaded_file_count"] == 0
    assert service.get_upload_manifest(job_id=record["job_id"], user_id="account-a")["files"] == []
    assert send(service, record, offset=0)["received_bytes"] == 4
    assert send(service, record, offset=4)["received_bytes"] == 8
    final = send(service, record, offset=8)
    assert final["complete"] and final["received_bytes"] == 10
    assert final["job"]["uploaded_file_count"] == 1
    assert final["job"]["uploaded_byte_count"] == 10
    assert not any(t[0] == "enqueue" for t in trace)
    manifest = service.get_upload_manifest(job_id=record["job_id"], user_id="account-a")
    assert manifest["files"] == [{"path": "export/movie.dat", "size": 10, "sha256": digest(b"abcdefghij")}]
    parts = list(staging.provider.base_path.rglob("*.part"))
    assert len(parts) == 3
    before = {p: p.read_bytes() for p in parts}
    replay = send(service, record, offset=8)
    assert replay["complete"] and replay["job"]["uploaded_file_count"] == 1
    assert replay["job"]["duplicate_count"] == final["job"]["duplicate_count"]
    assert {p: p.read_bytes() for p in parts} == before
    assert service.finalize_job(job_id=record["job_id"], user_id="account-a")["status"] == "queued"
    assert len([t for t in trace if t[0] == "enqueue"]) == 1


def test_owner_is_checked_before_any_private_transport_files(account_import_service):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    with pytest.raises(AccountImportError) as denied:
        send(service, record, user_id="account-b")
    assert denied.value.status_code == 404
    assert not (staging.provider.base_path / ".account-import-parts").exists()


@pytest.mark.parametrize("changes", [
    {"offset": 2}, {"offset": 8}, {"data": b"abc"}, {"file_size": 0},
    {"file_sha256": "invalid"}, {"chunk_sha256": "0" * 64},
    {"relative_path": "../secret"},
])
def test_invalid_or_ahead_parts_do_not_advance_manifest(account_import_service, changes):
    service, _sessions, _trace, _staging, _media = account_import_service
    record = job(service)
    with pytest.raises(AccountImportError):
        send(service, record, **changes)
    assert service.get_job(job_id=record["job_id"], user_id="account-a")["uploaded_file_count"] == 0


def test_changed_identity_and_changed_replay_bytes_preserve_parts(account_import_service):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    send(service, record)
    parts = list(staging.provider.base_path.rglob("*.part"))
    before = {p: p.read_bytes() for p in parts}
    for changes in ({"file_sha256": "0" * 64}, {"file_size": 9},
                    {"data": b"xxxx", "chunk_sha256": digest(b"xxxx")}):
        with pytest.raises(AccountImportError):
            send(service, record, **changes)
    assert {p: p.read_bytes() for p in parts} == before


def test_whole_file_hash_failure_preserves_every_part(account_import_service):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    send(service, record, file_sha256="0" * 64)
    send(service, record, offset=4, file_sha256="0" * 64)
    with pytest.raises(AccountImportError) as failed:
        send(service, record, offset=8, file_sha256="0" * 64)
    assert failed.value.code == "account_import_chunk_integrity_failed"
    parts = list(staging.provider.base_path.rglob("*.part"))
    assert b"".join(p.read_bytes() for p in sorted(parts, key=lambda p: int(p.stem))) == b"abcdefghij"
    assert service.get_job(job_id=record["job_id"], user_id="account-a")["uploaded_file_count"] == 0


def test_interrupted_pending_write_resumes_without_truncation(account_import_service, monkeypatch):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    original = Path.open
    class PartialWriter:
        def __init__(self, handle): self.handle = handle
        def __enter__(self): return self
        def __exit__(self, *args): self.handle.close()
        def write(self, data):
            self.handle.write(data[:2]); self.handle.flush()
            raise OSError("simulated interrupted disk write")
    def opened(path, mode="r", *args, **kwargs):
        handle = original(path, mode, *args, **kwargs)
        return PartialWriter(handle) if path.suffix == ".pending" and mode == "ab" else handle
    monkeypatch.setattr(Path, "open", opened)
    with pytest.raises(AccountImportError) as failed:
        send(service, record)
    assert failed.value.status_code == 503
    pending = list(staging.provider.base_path.rglob("*.pending"))
    assert len(pending) == 1 and pending[0].read_bytes() == b"ab"
    monkeypatch.setattr(Path, "open", original)
    assert send(service, record)["received_bytes"] == 4
    assert list(staging.provider.base_path.rglob("*.part"))[0].read_bytes() == b"abcd"


def test_lost_final_response_reuses_admitted_bytes(account_import_service, monkeypatch):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    send(service, record); send(service, record, offset=4)
    original = service.stage_files
    def lost(**kwargs):
        original(**kwargs)
        raise RuntimeError("lost committed response")
    monkeypatch.setattr(service, "stage_files", lost)
    with pytest.raises(RuntimeError): send(service, record, offset=8)
    monkeypatch.setattr(service, "stage_files", original)
    replay = send(service, record, offset=8)
    assert replay["complete"] and replay["job"]["uploaded_byte_count"] == 10
    assert len(list(staging.provider.base_path.rglob("*.part"))) == 3
    with pytest.raises(AccountImportError):
        send(service, record, offset=8, data=b"zz", chunk_sha256=digest(b"zz"))


def test_admitted_file_replay_reads_only_the_claimed_chunk(account_import_service, monkeypatch):
    service, _sessions, _trace, _staging, _media = account_import_service
    record = job(service)
    send(service, record)
    send(service, record, offset=4)
    send(service, record, offset=8)
    original = Path.open
    bytes_read = []

    def tracked_open(path, mode="r", *args, **kwargs):
        handle = original(path, mode, *args, **kwargs)
        if path.name != "movie.dat" or mode != "rb":
            return handle

        class Tracked:
            def __enter__(self): return self
            def __exit__(self, *exc): handle.close()
            def seek(self, *args): return handle.seek(*args)
            def read(self, size=-1):
                data = handle.read(size)
                bytes_read.append(len(data))
                return data

        return Tracked()

    monkeypatch.setattr(Path, "open", tracked_open)
    assert send(service, record, offset=4)["complete"]
    assert sum(bytes_read) == 4


def test_raw_upload_exhaustion_is_rechecked_and_parts_remain(account_import_service):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    send(service, record)
    service.stage_files(job_id=record["job_id"], user_id="account-a", files=[StagedImportFile("export/other", b"short")])
    with pytest.raises(AccountImportError) as failed: send(service, record, offset=4)
    assert failed.value.status_code == 413
    assert len(list(staging.provider.base_path.rglob("*.part"))) == 1
    assert service.get_job(job_id=record["job_id"], user_id="account-a")["uploaded_file_count"] == 1


def test_only_one_incomplete_file_and_later_identity_keeps_old_parts(account_import_service):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service, size=20, count=2)
    send(service, record)
    with pytest.raises(AccountImportError): send(service, record, relative_path="export/next")
    send(service, record, offset=4); send(service, record, offset=8)
    old_parts = {p: p.read_bytes() for p in staging.provider.base_path.rglob("*.part")}
    send(service, record, relative_path="export/next")
    assert all(p.read_bytes() == data for p, data in old_parts.items())


def test_queued_job_and_symlink_refuse_writes(account_import_service):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    unsafe = staging.provider.base_path / ".account-import-parts"
    unsafe.symlink_to(staging.provider.base_path, target_is_directory=True)
    with pytest.raises(AccountImportError): send(service, record)
    # The symlink is a disposable synthetic fixture, never serving data.
    unsafe.unlink()
    service.stage_files(job_id=record["job_id"], user_id="account-a", files=[StagedImportFile("export/movie.dat", b"abcdefghij")])
    service.finalize_job(job_id=record["job_id"], user_id="account-a")
    with pytest.raises(AccountImportError): send(service, record)
    assert not unsafe.exists()


def test_final_admission_failure_keeps_parts_and_retries_existing_admission(account_import_service, monkeypatch):
    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    send(service, record); send(service, record, offset=4)
    original = service.stage_files
    def unavailable(**kwargs): raise RuntimeError("simulated admission unavailable")
    monkeypatch.setattr(service, "stage_files", unavailable)
    with pytest.raises(RuntimeError): send(service, record, offset=8)
    before = {p: p.read_bytes() for p in staging.provider.base_path.rglob("*.part")}
    assert len(before) == 3
    assert service.get_job(job_id=record["job_id"], user_id="account-a")["uploaded_file_count"] == 0
    monkeypatch.setattr(service, "stage_files", original)
    assert send(service, record, offset=8)["complete"]
    assert {p: p.read_bytes() for p in before} == before


@pytest.mark.parametrize("failure", [OSError, chunks.StorageError])
def test_storage_admission_failure_returns_retryable_503_and_preserves_parts(account_import_service, monkeypatch, failure):
    from guardian.core.storage import UploadError

    service, _sessions, _trace, staging, _media = account_import_service
    record = job(service)
    send(service, record)
    send(service, record, offset=4)
    provider = staging.provider
    original = provider.upload_stream

    def unavailable(*args, **kwargs):
        raise (UploadError("synthetic wrapped disk failure") if failure is chunks.StorageError else failure("synthetic disk failure"))

    monkeypatch.setattr(provider, "upload_stream", unavailable)
    with pytest.raises(AccountImportError) as failed:
        send(service, record, offset=8)
    assert failed.value.status_code == 503
    assert failed.value.code == "account_import_chunk_storage_unavailable"
    before = {part: part.read_bytes() for part in provider.base_path.rglob("*.part")}
    assert len(before) == 3
    assert service.get_job(job_id=record["job_id"], user_id="account-a")["uploaded_file_count"] == 0
    monkeypatch.setattr(provider, "upload_stream", original)
    result = send(service, record, offset=8)
    assert result["complete"] and result["job"]["uploaded_file_count"] == 1
    assert result["job"]["uploaded_byte_count"] == 10
    assert {part: part.read_bytes() for part in before} == before
