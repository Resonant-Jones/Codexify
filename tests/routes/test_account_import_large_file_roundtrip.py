"""Exact recovery-size synthetic round trip in a disposable PostgreSQL scope."""
from __future__ import annotations

import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import migration as routes
from guardian.services.account_import_chunks import CHUNK_BYTES
from tests.rag.test_account_import_chunks_postgres import pg_chunk_service


def test_original_oversize_length_crosses_bounded_http_parts_and_keeps_exact_identity(pg_chunk_service, monkeypatch):
    (service, _sessions, trace, staging, _media), _engine, _app = pg_chunk_service
    total = 107_330_125
    piece = b"v" * CHUNK_BYTES
    expected = hashlib.sha256()
    for offset in range(0, total, CHUNK_BYTES):
        expected.update(piece[:min(CHUNK_BYTES, total-offset)])
    whole = expected.hexdigest()
    record = service.create_job(user_id="account-a", total_file_count=1, total_byte_count=total)
    app = FastAPI()
    app.dependency_overrides[routes.require_api_key] = lambda: "synthetic-test-auth"
    app.dependency_overrides[routes.get_request_user_id] = lambda: "account-a"
    app.include_router(routes.router)
    monkeypatch.setattr(routes, "_get_account_import_service", lambda: service)
    with TestClient(app) as client:
        for offset in range(0, total, CHUNK_BYTES):
            data = piece[:min(CHUNK_BYTES, total-offset)]
            response = client.post(f"/api/imports/openai-account/{record['job_id']}/file-chunks",
                data={"relative_path": "export/synthetic-video.dat", "file_size": str(total),
                      "file_sha256": whole, "chunk_sha256": hashlib.sha256(data).hexdigest(),
                      "offset": str(offset), "content_type": "video/mp4"},
                files={"chunk": ("synthetic-part", data, "application/octet-stream")})
            assert response.status_code == 200, response.text
            receipt = response.json()
            assert receipt["received_bytes"] == offset + len(data)
            assert receipt["complete"] == (offset + len(data) == total)
            assert receipt["job"]["uploaded_file_count"] == int(receipt["complete"])
    assert receipt["job"]["uploaded_byte_count"] == total
    assert receipt["job"]["status"] == "receiving"
    manifest = service.get_upload_manifest(job_id=record["job_id"], user_id="account-a")
    assert manifest["files"] == [{"path": "export/synthetic-video.dat", "size": total, "sha256": whole}]
    assert len(list(staging.provider.base_path.rglob("*.part"))) == 13
    assert not any(item[0] == "enqueue" for item in trace)
    service.finalize_job(job_id=record["job_id"], user_id="account-a")
    assert len([item for item in trace if item[0] == "enqueue"]) == 1
