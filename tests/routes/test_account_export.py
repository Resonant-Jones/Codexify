from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("GUARDIAN_API_KEY", "test-key")

from guardian.routes import api_exports

USER_ID = "user-123"
EXPECTED_FILES = [
    "entities/projects.json",
    "entities/chat_threads.json",
    "entities/chat_messages.json",
    "entities/uploaded_documents.json",
    "entities/generated_documents.json",
    "entities/uploaded_images.json",
    "entities/generated_images.json",
    "entities/media_assets.json",
    "entities/media_aliases.json",
    "entities/thread_documents.json",
    "entities/project_document_links.json",
]


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _build_rows() -> dict[str, list[dict[str, object]]]:
    return {
        "projects": [
            {
                "id": 10,
                "name": "Project Alpha",
                "description": "Primary workspace",
                "icon": "A",
                "identity_depth": "deep",
                "created_at": _utc("2026-03-01T00:00:00Z"),
                "updated_at": _utc("2026-03-02T00:00:00Z"),
            },
            {
                "id": 20,
                "name": "Project Beta",
                "description": "Secondary workspace",
                "icon": "B",
                "identity_depth": "light",
                "created_at": _utc("2026-03-03T00:00:00Z"),
                "updated_at": _utc("2026-03-04T00:00:00Z"),
            },
        ],
        "chat_threads": [
            {
                "id": 101,
                "user_id": USER_ID,
                "title": "Launch planning",
                "summary": "Thread summary",
                "project_id": 10,
                "parent_id": None,
                "archived_at": None,
                "is_diary": False,
                "diary_mode": False,
                "exclude_from_identity": False,
                "modeling_excluded": False,
                "metadata": {"source": "manual"},
                "active_profile_id": "profile-a",
                "created_at": _utc("2026-03-05T00:00:00Z"),
                "updated_at": _utc("2026-03-05T01:00:00Z"),
            },
            {
                "id": 102,
                "user_id": USER_ID,
                "title": "Post-launch review",
                "summary": "Follow-up thread",
                "project_id": 20,
                "parent_id": 101,
                "archived_at": _utc("2026-03-10T00:00:00Z"),
                "is_diary": True,
                "diary_mode": True,
                "exclude_from_identity": True,
                "modeling_excluded": True,
                "metadata": {"source": "imported"},
                "active_profile_id": None,
                "created_at": _utc("2026-03-06T00:00:00Z"),
                "updated_at": _utc("2026-03-10T00:00:00Z"),
            },
        ],
        "chat_messages": [
            {
                "id": 1,
                "thread_id": 101,
                "role": "user",
                "content": "Hello",
                "event_at": _utc("2026-03-05T01:00:00Z"),
                "kind": "chat",
                "extra_meta": {
                    "source_thread_id": "source-1",
                    "source_message_id": "m1",
                    "turn_index": 0,
                },
                "created_at": _utc("2026-03-05T01:00:00Z"),
            },
            {
                "id": 2,
                "thread_id": 101,
                "role": "assistant",
                "content": "Hi",
                "event_at": _utc("2026-03-05T01:01:00Z"),
                "kind": "tool",
                "extra_meta": {
                    "source_thread_id": "source-1",
                    "source_message_id": "m2",
                    "turn_index": 1,
                },
                "created_at": _utc("2026-03-05T01:01:00Z"),
            },
            {
                "id": 3,
                "thread_id": 102,
                "role": "user",
                "content": "Follow up",
                "event_at": _utc("2026-03-10T01:00:00Z"),
                "kind": "chat",
                "extra_meta": {"source_thread_id": "source-2"},
                "created_at": _utc("2026-03-10T01:00:00Z"),
            },
        ],
        "uploaded_documents": [
            {
                "id": "ud-1",
                "asset_id": "asset-doc-1",
                "project_id": 10,
                "thread_id": 101,
                "user_id": USER_ID,
                "filename": "brief.pdf",
                "filesize": 1234,
                "mime_type": "application/pdf",
                "src_url": "file:///tmp/brief.pdf",
                "source_tag": "uploaded",
                "parsed_text": "Brief text",
                "embedding_status": "completed",
                "embedding_error": None,
                "embedding_started_at": _utc("2026-03-05T02:00:00Z"),
                "embedding_completed_at": _utc("2026-03-05T02:01:00Z"),
                "created_at": _utc("2026-03-05T02:00:00Z"),
                "updated_at": _utc("2026-03-05T02:02:00Z"),
                "deleted_at": None,
            }
        ],
        "generated_documents": [
            {
                "id": "gd-1",
                "project_id": 20,
                "thread_id": 102,
                "user_id": USER_ID,
                "title": "Launch brief",
                "content": "Drafted content",
                "format": "md",
                "model": "gpt-4.1",
                "created_at": _utc("2026-03-10T02:00:00Z"),
                "updated_at": _utc("2026-03-10T02:05:00Z"),
                "deleted_at": _utc("2026-03-12T00:00:00Z"),
            }
        ],
        "uploaded_images": [
            {
                "id": "ui-1",
                "asset_id": "asset-img-1",
                "project_id": 10,
                "thread_id": 101,
                "user_id": USER_ID,
                "src_url": "file:///tmp/uploaded.png",
                "filename": "uploaded.png",
                "filesize": 2048,
                "mime_type": "image/png",
                "source_tag": "uploaded",
                "created_at": _utc("2026-03-05T03:00:00Z"),
                "updated_at": _utc("2026-03-05T03:05:00Z"),
                "deleted_at": None,
            }
        ],
        "generated_images": [
            {
                "id": "gi-1",
                "asset_id": "asset-img-2",
                "project_id": 20,
                "thread_id": 102,
                "user_id": USER_ID,
                "src_url": "file:///tmp/generated.png",
                "prompt": "a schematic of a distributed system",
                "model": "dall-e-3",
                "created_at": _utc("2026-03-10T03:00:00Z"),
                "updated_at": _utc("2026-03-10T03:05:00Z"),
                "deleted_at": None,
            }
        ],
        "media_assets": [
            {
                "id": "asset-doc-1",
                "project_id": 10,
                "thread_id": 101,
                "user_id": USER_ID,
                "media_kind": "document",
                "provenance": "uploaded",
                "source_tag": "uploaded",
                "content_hash": "hash-doc-1",
                "deterministic_id": "docdet1",
                "normalized_slug": "brief",
                "system_name": "brief.pdf",
                "storage_prefix": "documents",
                "src_url": "file:///tmp/brief.pdf",
                "mime_type": "application/pdf",
                "filesize": 1234,
                "ingested_at": _utc("2026-03-05T02:00:00Z"),
                "deleted_at": None,
            },
            {
                "id": "asset-img-1",
                "project_id": 10,
                "thread_id": 101,
                "user_id": USER_ID,
                "media_kind": "image",
                "provenance": "uploaded",
                "source_tag": "uploaded",
                "content_hash": "hash-img-1",
                "deterministic_id": "imgdet1",
                "normalized_slug": "uploaded",
                "system_name": "uploaded.png",
                "storage_prefix": "images",
                "src_url": "file:///tmp/uploaded.png",
                "mime_type": "image/png",
                "filesize": 2048,
                "ingested_at": _utc("2026-03-05T03:00:00Z"),
                "deleted_at": None,
            },
            {
                "id": "asset-img-2",
                "project_id": 20,
                "thread_id": 102,
                "user_id": USER_ID,
                "media_kind": "image",
                "provenance": "generated",
                "source_tag": "generated",
                "content_hash": "hash-img-2",
                "deterministic_id": "imgdet2",
                "normalized_slug": "generated",
                "system_name": "generated.png",
                "storage_prefix": "generated_images",
                "src_url": "file:///tmp/generated.png",
                "mime_type": "image/png",
                "filesize": 4096,
                "ingested_at": _utc("2026-03-10T03:00:00Z"),
                "deleted_at": None,
            },
        ],
        "media_aliases": [
            {
                "id": "alias-1",
                "asset_id": "asset-doc-1",
                "alias": "Brief PDF",
                "alias_normalized": "brief-pdf",
                "alias_type": "original_name",
                "created_at": _utc("2026-03-05T02:03:00Z"),
            },
            {
                "id": "alias-2",
                "asset_id": "asset-img-2",
                "alias": "Generation prompt",
                "alias_normalized": "generation-prompt",
                "alias_type": "prompt",
                "created_at": _utc("2026-03-10T03:06:00Z"),
            },
        ],
        "thread_documents": [
            {
                "id": 1,
                "thread_id": 101,
                "document_id": "ud-1",
                "relation": "attached",
                "created_at": _utc("2026-03-05T04:00:00Z"),
            },
            {
                "id": 2,
                "thread_id": 102,
                "document_id": "gd-1",
                "relation": "autosave",
                "created_at": _utc("2026-03-10T04:00:00Z"),
            },
        ],
        "project_document_links": [
            {
                "id": 1,
                "project_id": 10,
                "document_id": "ud-1",
                "document_type": "uploaded",
                "is_enabled": True,
                "attached_at": _utc("2026-03-05T05:00:00Z"),
                "attached_by": USER_ID,
            },
            {
                "id": 2,
                "project_id": 20,
                "document_id": "gd-1",
                "document_type": "generated",
                "is_enabled": False,
                "attached_at": _utc("2026-03-10T05:00:00Z"),
                "attached_by": USER_ID,
            },
        ],
    }


def _build_fake_db(rows: dict[str, list[dict[str, object]]]):
    calls: dict[str, str] = {}

    def _record(name: str):
        def _reader(user_id: str):
            calls[name] = user_id
            return list(rows[name])

        return _reader

    db = SimpleNamespace(
        fetch_account_export_projects_for_user=_record("projects"),
        fetch_account_export_chat_threads_for_user=_record("chat_threads"),
        fetch_account_export_chat_messages_for_user=_record("chat_messages"),
        fetch_account_export_uploaded_documents_for_user=_record(
            "uploaded_documents"
        ),
        fetch_account_export_generated_documents_for_user=_record(
            "generated_documents"
        ),
        fetch_account_export_uploaded_images_for_user=_record(
            "uploaded_images"
        ),
        fetch_account_export_generated_images_for_user=_record(
            "generated_images"
        ),
        fetch_account_export_media_assets_for_user=_record("media_assets"),
        fetch_account_export_media_aliases_for_user=_record("media_aliases"),
        fetch_account_export_thread_documents_for_user=_record(
            "thread_documents"
        ),
        fetch_account_export_project_document_links_for_user=_record(
            "project_document_links"
        ),
    )
    return db, calls


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(api_exports.router)
    return application


@pytest.fixture
def rows() -> dict[str, list[dict[str, object]]]:
    return _build_rows()


@pytest.fixture
def fake_db(rows):
    return _build_fake_db(rows)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_account_export_zip_requires_auth(client: TestClient) -> None:
    response = client.get("/exports/account.zip", headers={"X-API-Key": ""})
    assert response.status_code == 401


def test_account_export_zip_writes_archive_to_temp_file(
    fake_db,
) -> None:
    db, _ = fake_db
    zip_path = api_exports.build_account_export_zip(
        db,
        SimpleNamespace(id=USER_ID),
    )

    try:
        assert os.path.exists(zip_path)

        with zipfile.ZipFile(zip_path, "r") as archive:
            assert archive.testzip() is None
            assert sorted(archive.namelist()) == sorted(
                ["manifest.json", *EXPECTED_FILES]
            )
    finally:
        if os.path.exists(zip_path):
            os.unlink(zip_path)


def test_account_export_zip_returns_truthful_manifest(
    client: TestClient, fake_db, monkeypatch: pytest.MonkeyPatch, rows
) -> None:
    db, calls = fake_db
    monkeypatch.setattr(api_exports, "db", db, raising=True)

    response = client.get(
        "/exports/account.zip",
        headers={
            "X-API-Key": os.environ["GUARDIAN_API_KEY"],
            "X-Guardian-Identity": USER_ID,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"] == (
        'attachment; filename="Codexify-Export.zip"'
    )

    archive = zipfile.ZipFile(io.BytesIO(response.content), "r")
    assert archive.testzip() is None
    assert sorted(archive.namelist()) == sorted(
        ["manifest.json", *EXPECTED_FILES]
    )

    manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    assert manifest["schema_version"] == "1"
    assert manifest["export_kind"] == "full_account"
    assert manifest["user_id"] == USER_ID
    assert manifest["blob_mode"] == "metadata_only"
    assert manifest["compatibility"]["binary_payloads_included"] is False
    assert manifest["integrity"]["algorithm"] == "sha256"
    assert "binary" in " ".join(manifest["notes"]).lower()

    assert manifest["included_families"] == [
        "projects",
        "chat_threads",
        "chat_messages",
        "uploaded_documents",
        "generated_documents",
        "uploaded_images",
        "generated_images",
        "media_assets",
        "media_aliases",
        "thread_documents",
        "project_document_links",
    ]

    expected_counts = {name: len(value) for name, value in rows.items()}
    assert manifest["entity_counts"] == expected_counts

    payload_files = manifest["integrity"]["payload_files"]
    assert set(payload_files) == set(EXPECTED_FILES)

    for path in EXPECTED_FILES:
        payload_bytes = archive.read(path)
        payload = json.loads(payload_bytes.decode("utf-8"))
        assert (
            len(payload)
            == expected_counts[path.rsplit("/", 1)[-1].removesuffix(".json")]
        )

        digest = hashlib.sha256(payload_bytes).hexdigest()
        assert payload_files[path]["sha256"] == digest
        assert payload_files[path]["size_bytes"] == len(payload_bytes)

    assert calls == {
        "projects": USER_ID,
        "chat_threads": USER_ID,
        "chat_messages": USER_ID,
        "uploaded_documents": USER_ID,
        "generated_documents": USER_ID,
        "uploaded_images": USER_ID,
        "generated_images": USER_ID,
        "media_assets": USER_ID,
        "media_aliases": USER_ID,
        "thread_documents": USER_ID,
        "project_document_links": USER_ID,
    }

    assert "uploaded_documents.binary_payload" in manifest["omitted_families"]
    assert "generated_images.binary_payload" in manifest["omitted_families"]
