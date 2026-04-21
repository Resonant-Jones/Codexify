from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("GUARDIAN_API_KEY", "test-key")

from guardian.routes import api_exports
from guardian.services.account_export import (
    ZIP_FILENAME,
    build_account_export_zip,
)

USER_ID = "user-123"
EXPECTED_PAYLOAD_FILES = [
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
    "entities/extension_proposals.json",
    "entities/extension_install_gate_decisions.json",
    "entities/extension_registry_entries.json",
    "entities/extension_install_bindings.json",
]


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _write_blob(base_path: Path, relative_path: str, data: bytes) -> None:
    blob_path = base_path / relative_path
    blob_path.parent.mkdir(parents=True, exist_ok=True)
    blob_path.write_bytes(data)


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
                "src_url": "/media/documents/brief.pdf",
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
                "src_url": "/media/images/uploaded.png",
                "filename": "uploaded.png",
                "filesize": 2048,
                "mime_type": "image/png",
                "source_tag": "uploaded",
                "created_at": _utc("2026-03-05T03:00:00Z"),
                "updated_at": _utc("2026-03-05T03:05:00Z"),
                "deleted_at": None,
            },
            {
                "id": "ui-missing",
                "asset_id": "asset-img-missing",
                "project_id": 20,
                "thread_id": 102,
                "user_id": USER_ID,
                "src_url": "/media/images/missing.png",
                "filename": "missing.png",
                "filesize": 1024,
                "mime_type": "image/png",
                "source_tag": "uploaded",
                "created_at": _utc("2026-03-12T03:00:00Z"),
                "updated_at": _utc("2026-03-12T03:05:00Z"),
                "deleted_at": None,
            },
        ],
        "generated_images": [
            {
                "id": "gi-1",
                "asset_id": "asset-img-2",
                "project_id": 20,
                "thread_id": 102,
                "user_id": USER_ID,
                "src_url": "/media/generated_images/generated.png",
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
                "storage_prefix": "documents/",
                "src_url": "/media/documents/brief.pdf",
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
                "storage_prefix": "images/",
                "src_url": "/media/images/uploaded.png",
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
                "storage_prefix": "generated_images/",
                "src_url": "/media/generated_images/generated.png",
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
        "extension_proposals": [
            {
                "proposal_id": "proposal-1",
                "account_id": USER_ID,
                "project_id": 10,
                "profile_id": "profile-a",
                "source_thread_id": 101,
                "source_message_id": 202,
                "target_surface_token": "command_bus",
                "scope_token": "project_scoped",
                "status_token": "draft",
                "requested_permissions_json": [
                    {
                        "permission": "command.run",
                        "resource": "command_bus",
                        "reason": "bounded command execution",
                        "metadata": {},
                    }
                ],
                "declared_dependencies_json": [
                    {
                        "name": "httpx",
                        "version_spec": ">=0.28",
                        "source": "pypi",
                        "required": True,
                        "metadata": {},
                    }
                ],
                "rollback_metadata_json": {
                    "strategy": "disable_and_revert",
                    "rollback_ref": "ticket-123",
                    "can_rollback": True,
                    "metadata": {},
                },
                "test_evidence_json": {
                    "status": "passing",
                    "summary": "proposal draft coverage",
                    "artifacts": [
                        "tests/services/test_account_export_extension_proposals.py",
                    ],
                    "metadata": {},
                },
                "manifest_json": {
                    "manifest_version": "extension-proposal-manifest.v1",
                    "target_surface": "command_bus",
                    "scope": "project_scoped",
                    "source_thread_id": 101,
                    "source_message_id": 202,
                    "project_id": 10,
                    "profile_id": "profile-a",
                    "summary": "Generate a bounded tool plugin",
                    "description": "Draft a tool proposal without executing it.",
                    "requested_permissions": [
                        {
                            "permission": "command.run",
                            "resource": "command_bus",
                            "reason": "bounded command execution",
                            "metadata": {},
                        }
                    ],
                    "declared_dependencies": [
                        {
                            "name": "httpx",
                            "version_spec": ">=0.28",
                            "source": "pypi",
                            "required": True,
                            "metadata": {},
                        }
                    ],
                    "rollback_metadata": {
                        "strategy": "disable_and_revert",
                        "rollback_ref": "ticket-123",
                        "can_rollback": True,
                        "metadata": {},
                    },
                    "test_evidence_metadata": {
                        "status": "passing",
                        "summary": "proposal draft coverage",
                        "artifacts": [
                            "tests/services/test_account_export_extension_proposals.py",
                        ],
                        "metadata": {},
                    },
                },
                "created_at": _utc("2026-03-14T00:00:00Z"),
                "updated_at": _utc("2026-03-14T01:00:00Z"),
            }
        ],
        "extension_install_gate_decisions": [],
        "extension_registry_entries": [],
        "extension_install_bindings": [],
    }


def _build_fake_db(rows: dict[str, list[dict[str, object]]]):
    calls: list[str] = []

    def _fetch(user_id: str):
        calls.append(user_id)
        return rows

    return SimpleNamespace(fetch_account_export_bundle_for_user=_fetch), calls


@pytest.fixture
def storage_base_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base_path = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_BASE_PATH", str(base_path))
    monkeypatch.setenv("STORAGE_URL_PREFIX", "/media")
    _write_blob(base_path, "documents/brief.pdf", b"brief-pdf-bytes")
    _write_blob(base_path, "images/uploaded.png", b"uploaded-image-bytes")
    _write_blob(
        base_path, "generated_images/generated.png", b"generated-image-bytes"
    )
    return base_path


@pytest.fixture
def rows(storage_base_path: Path) -> dict[str, list[dict[str, object]]]:
    return _build_rows()


@pytest.fixture
def fake_db(rows):
    return _build_fake_db(rows)


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(api_exports.router)
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _read_archive(payload: bytes) -> zipfile.ZipFile:
    archive = zipfile.ZipFile(io.BytesIO(payload), "r")
    assert archive.testzip() is None
    return archive


def _load_json(archive: zipfile.ZipFile, path: str):
    return json.loads(archive.read(path).decode("utf-8"))


def test_account_export_zip_requires_auth(client: TestClient) -> None:
    response = client.get("/exports/account.zip", headers={"X-API-Key": ""})
    assert response.status_code == 401


def test_account_export_zip_writes_archive_to_temp_file(fake_db) -> None:
    db, _calls = fake_db
    zip_path = build_account_export_zip(
        db,
        SimpleNamespace(id=USER_ID),
    )

    try:
        assert os.path.exists(zip_path)
        with zipfile.ZipFile(zip_path, "r") as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert "manifest.json" in names
            for path in EXPECTED_PAYLOAD_FILES:
                assert path in names
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            assert manifest["blob_mode"] == "canonical_bundled"
            assert manifest["compatibility"]["binary_payloads_included"] is True
            assert manifest["binary_complete_families"]
    finally:
        if os.path.exists(zip_path):
            os.unlink(zip_path)


def test_account_export_zip_returns_truthful_manifest(
    client: TestClient,
    fake_db,
    monkeypatch: pytest.MonkeyPatch,
    rows,
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
        f'attachment; filename="{ZIP_FILENAME}"'
    )
    assert calls == [USER_ID]

    archive = _read_archive(response.content)
    names = archive.namelist()
    assert "manifest.json" in names
    for path in EXPECTED_PAYLOAD_FILES:
        assert path in names

    manifest = _load_json(archive, "manifest.json")
    assert manifest["schema_version"] == "account-export.v1"
    assert manifest["app_version"] == "0.1.0"
    assert manifest["export_kind"] == "full_account"
    assert manifest["user_id"] == USER_ID
    assert manifest["blob_mode"] == "canonical_bundled"
    assert manifest["compatibility"]["restore_mode"] == "not_implemented"
    assert manifest["compatibility"]["binary_payloads_included"] is True
    assert manifest["integrity"]["algorithm"] == "sha256"
    assert (
        "restore/import is not implemented"
        in " ".join(manifest["notes"]).lower()
    )

    expected_counts = {name: len(value) for name, value in rows.items()}
    assert manifest["entity_counts"] == expected_counts

    payload_integrity = manifest["integrity"]["payload_files"]
    blob_integrity = manifest["integrity"]["blob_files"]
    all_integrity = manifest["integrity"]["files"]

    assert set(payload_integrity) == set(EXPECTED_PAYLOAD_FILES)
    assert set(all_integrity) == set(payload_integrity) | set(blob_integrity)

    for path in EXPECTED_PAYLOAD_FILES:
        payload_bytes = archive.read(path)
        payload = json.loads(payload_bytes.decode("utf-8"))
        family = path.rsplit("/", 1)[-1].removesuffix(".json")
        assert len(payload) == expected_counts[family]
        assert (
            payload_integrity[path]["sha256"]
            == hashlib.sha256(payload_bytes).hexdigest()
        )
        assert payload_integrity[path]["size_bytes"] == len(payload_bytes)

    bundled_blob_paths = manifest["blob_coverage"]["bundled_blob_paths"]
    assert bundled_blob_paths
    assert len(bundled_blob_paths) == len(set(bundled_blob_paths))
    assert set(blob_integrity) == set(bundled_blob_paths)

    for path in bundled_blob_paths:
        blob_bytes = archive.read(path)
        assert (
            blob_integrity[path]["sha256"]
            == hashlib.sha256(blob_bytes).hexdigest()
        )
        assert blob_integrity[path]["size_bytes"] == len(blob_bytes)

    uploaded_documents = _load_json(archive, "entities/uploaded_documents.json")
    generated_documents = _load_json(
        archive, "entities/generated_documents.json"
    )
    uploaded_images = _load_json(archive, "entities/uploaded_images.json")
    generated_images = _load_json(archive, "entities/generated_images.json")
    media_assets = _load_json(archive, "entities/media_assets.json")

    doc_blob_path = uploaded_documents[0]["export"]["blob"]["bundle_path"]
    media_doc_blob_path = next(
        row["export"]["blob"]["bundle_path"]
        for row in media_assets
        if row["id"] == "asset-doc-1"
    )
    assert doc_blob_path == media_doc_blob_path

    uploaded_image_blob_path = next(
        row["export"]["blob"]["bundle_path"]
        for row in uploaded_images
        if row["id"] == "ui-1"
    )
    media_image_blob_path = next(
        row["export"]["blob"]["bundle_path"]
        for row in media_assets
        if row["id"] == "asset-img-1"
    )
    assert uploaded_image_blob_path == media_image_blob_path

    generated_image_blob_path = generated_images[0]["export"]["blob"][
        "bundle_path"
    ]
    media_generated_blob_path = next(
        row["export"]["blob"]["bundle_path"]
        for row in media_assets
        if row["id"] == "asset-img-2"
    )
    assert generated_image_blob_path == media_generated_blob_path

    unresolved_row = next(
        row for row in uploaded_images if row["id"] == "ui-missing"
    )
    assert unresolved_row["export"]["blob"]["status"] == "unresolved"
    assert unresolved_row["export"]["blob"]["bundle_path"] is None
    assert unresolved_row["export"]["blob"]["missing_reason"]

    assert manifest["blob_coverage"]["missing_families"] == ["uploaded_images"]
    assert "uploaded_images" in manifest["blob_coverage"]["bundled_families"]
    assert manifest["binary_complete_families"] == [
        "generated_documents",
        "generated_images",
        "media_assets",
        "uploaded_documents",
    ]
    assert manifest["blob_coverage"]["unresolved_rows"] == [
        {
            "family": "uploaded_images",
            "row_id": "ui-missing",
            "canonical_blob_id": "asset:asset-img-missing",
            "source_locator": "/media/images/missing.png",
            "reason": "blob could not be resolved from current storage",
        }
    ]
