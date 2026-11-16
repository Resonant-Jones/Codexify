from __future__ import annotations

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
