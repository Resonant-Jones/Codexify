from __future__ import annotations

import json
from types import SimpleNamespace
import pytest

from guardian.services.openai_account_import import AccountImportError, StagedImportFile
from tests.rag.test_openai_export_account_import import account_import_service


def test_resume_manifest_is_owner_scoped_and_excludes_storage(account_import_service):
    service, _sessions, _trace, _staging, _media = account_import_service
    job = service.create_job(user_id="account-a", total_file_count=2, total_byte_count=3)
    service.stage_files(job_id=job["job_id"], user_id="account-a", files=[StagedImportFile("export/a.txt", b"a")])
    manifest = service.get_upload_manifest(job_id=job["job_id"], user_id="account-a")
    assert set(manifest) == {"job_id", "source_system", "status", "total_file_count", "total_byte_count", "files"}
    assert manifest["job_id"] == job["job_id"]
    assert manifest["status"] == "receiving"
    assert manifest["total_file_count"] == 2
    assert manifest["total_byte_count"] == 3
    assert manifest["files"] == [{"path": "export/a.txt", "size": 1, "sha256": "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb"}]
    with pytest.raises(AccountImportError) as denied:
        service.get_upload_manifest(job_id=job["job_id"], user_id="account-b")
    assert denied.value.status_code == 404


def test_manifest_pages_have_strict_response_byte_budget(account_import_service, monkeypatch):
    service, _sessions, _trace, _staging, _media = account_import_service
    long_path = "/".join(["directory" * 10] * 9)
    entries = [{"path": f"{long_path}/{i:04d}", "size": 0, "sha256": "a" * 64}
               for i in range(700)]
    record = SimpleNamespace(
        id="synthetic", source_system="openai", status="receiving",
        total_file_count=700, total_byte_count=0, staged_manifest=entries,
    )
    monkeypatch.setattr(service, "_require_job", lambda session, job_id, user_id: record)
    cursor = 0
    seen = []
    for _ in range(10):
        page = service.get_upload_manifest(job_id="synthetic", user_id="account-a", cursor=cursor)
        assert len(json.dumps(page, ensure_ascii=False).encode("utf-8")) <= 192 * 1024
        seen.extend(page["files"])
        if "next_cursor" not in page:
            break
        assert page["next_cursor"] == len(seen)
        cursor = page["next_cursor"]
    assert seen == entries
