from __future__ import annotations

import asyncio
import hashlib

import pytest
from fastapi import HTTPException
from starlette import formparsers

from guardian.routes import migration as routes
from tests.routes.test_migration_routes import test_client, SERVER_USER_ID


def form():
    return {"relative_path": "export/movie.dat", "file_size": "4", "offset": "0",
            "file_sha256": hashlib.sha256(b"data").hexdigest(), "chunk_sha256": hashlib.sha256(b"data").hexdigest()}


def test_chunk_route_uses_authenticated_owner_and_public_receipt(test_client, monkeypatch):
    seen = []
    service = object()
    monkeypatch.setattr(routes, "_get_account_import_service", lambda: service)
    def stage(received, **kwargs):
        assert received is service
        seen.append(kwargs)
        return {"job": {"job_id": "job"}, "received_bytes": 4, "complete": True}
    monkeypatch.setattr(routes, "stage_account_import_chunk", stage)
    response = test_client.post("/api/imports/openai-account/job/file-chunks",
        data={**form(), "user_id": "other-account"}, files={"chunk": ("part", b"data", "video/mp4")})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert seen[0]["user_id"] == SERVER_USER_ID
    assert seen[0]["data"] == b"data"
    assert "other-account" not in response.text


def test_chunk_route_denied_auth_never_calls_staging(test_client, monkeypatch):
    called = []
    def deny(): raise HTTPException(status_code=401, detail="Account authentication required")
    test_client.app.dependency_overrides[routes.require_api_key] = deny
    monkeypatch.setattr(routes, "stage_account_import_chunk", lambda *a, **k: called.append(True))
    response = test_client.post("/api/imports/openai-account/job/file-chunks", data=form(), files={"chunk": ("part", b"data")})
    assert response.status_code == 401 and not called


def test_declared_request_limit_is_rejected_before_parsing(test_client, monkeypatch):
    monkeypatch.setattr(routes, "CHUNK_REQUEST_BYTES", 4096)
    response = test_client.post("/api/imports/openai-account/job/file-chunks", content=b"",
        headers={"Content-Length": "4097", "Content-Type": "multipart/form-data; boundary=test"})
    assert response.status_code == 413


@pytest.mark.parametrize("declared", [None, "1"])
def test_actual_stream_limit_closes_spooled_files_and_maps_only_own_limit(test_client, monkeypatch, declared):
    monkeypatch.setattr(routes, "CHUNK_REQUEST_BYTES", 4096)
    handles = []
    original = formparsers.SpooledTemporaryFile
    def spool(*args, **kwargs):
        kwargs["max_size"] = 1
        handle = original(*args, **kwargs); handles.append(handle); return handle
    monkeypatch.setattr(formparsers, "SpooledTemporaryFile", spool)
    boundary = b'--test\r\nContent-Disposition: form-data; name="chunk"; filename="part"\r\nContent-Type: application/octet-stream\r\n\r\n'
    messages = iter([
        {"type": "http.request", "body": boundary + b"x"*1000, "more_body": True},
        {"type": "http.request", "body": b"x"*4096, "more_body": True},
    ])
    headers = [(b"content-type", b"multipart/form-data; boundary=test")]
    if declared is not None: headers.append((b"content-length", declared.encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
             "scheme": "http", "path": "/api/imports/openai-account/job/file-chunks",
             "raw_path": b"/api/imports/openai-account/job/file-chunks", "query_string": b"", "root_path": "",
             "headers": headers, "server": ("testserver", 80), "client": ("test", 123)}
    responses = []
    async def receive(): return next(messages)
    async def send(message): responses.append(message)
    asyncio.run(test_client.app(scope, receive, send))
    assert responses[0]["status"] == 413
    assert handles and all(handle.closed for handle in handles)


def test_malformed_multipart_is_not_mislabeled_as_size_failure(test_client):
    response = test_client.post("/api/imports/openai-account/job/file-chunks", content=b"bad", headers={"Content-Type": "multipart/form-data"})
    assert response.status_code == 400


def test_logical_source_routes_and_job_use_authenticated_owner(test_client, monkeypatch):
    source_id = "2f524a4b-990b-4f3a-b68d-98c78264b53d"
    seen = []

    class Service:
        def create_openai_source(self, **kwargs):
            seen.append(kwargs)
            return {"id": source_id, "label": kwargs["label"]}

        def list_openai_sources(self, **kwargs):
            seen.append(kwargs)
            return [{"id": source_id, "label": "Business"}]

        def create_job(self, **kwargs):
            seen.append(kwargs)
            return {"job_id": "test", "openai_import_source_id": source_id}

    monkeypatch.setattr(routes, "_get_account_import_service", Service)
    base = "/api/imports/openai-account"
    assert test_client.post(f"{base}/sources", json={"label": "Business", "user_id": "forged"}).json() == {
        "id": source_id, "label": "Business"
    }
    assert test_client.get(f"{base}/sources").json() == {
        "sources": [{"id": source_id, "label": "Business"}]
    }
    assert test_client.post(base, json={
        "total_file_count": 1, "total_byte_count": 20,
        "openai_import_source_id": source_id, "user_id": "forged",
    }).json()["openai_import_source_id"] == source_id
    assert [entry["user_id"] for entry in seen] == [SERVER_USER_ID] * 3
    assert seen[2]["openai_import_source_id"] == source_id
