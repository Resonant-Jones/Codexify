from __future__ import annotations

import io
import json
import os
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CODEXIFY_EMBEDDINGS_BACKEND", "mock")
os.environ.setdefault("GUARDIAN_API_KEY", "test-key")
os.environ.setdefault("LOCAL_DEV", "1")
os.environ.setdefault("STORAGE_BASE_PATH", "/tmp/test_media")
os.environ.setdefault("STORAGE_URL_PREFIX", "/media")

from guardian.routes import migration as migration_routes
from guardian.services.account_export import (
    ZIP_FILENAME,
    build_account_export_zip,
)
from guardian.services.account_restore import RESTORE_ORDER

USER_ID = "user-123"


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
            }
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
                "metadata": {"source_thread_id": "source-1"},
                "active_profile_id": "profile-a",
                "created_at": _utc("2026-03-05T00:00:00Z"),
                "updated_at": _utc("2026-03-05T01:00:00Z"),
            },
            {
                "id": 102,
                "user_id": USER_ID,
                "title": "Post-launch review",
                "summary": "Follow-up thread",
                "project_id": 10,
                "parent_id": 101,
                "archived_at": _utc("2026-03-10T00:00:00Z"),
                "is_diary": True,
                "diary_mode": True,
                "exclude_from_identity": True,
                "modeling_excluded": True,
                "metadata": {"source_thread_id": "source-2"},
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
                "thread_id": 102,
                "role": "assistant",
                "content": "Hi",
                "event_at": _utc("2026-03-06T01:01:00Z"),
                "kind": "tool",
                "extra_meta": {
                    "source_thread_id": "source-2",
                    "source_message_id": "m2",
                    "turn_index": 1,
                },
                "created_at": _utc("2026-03-06T01:01:00Z"),
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
                "embedding_status": "ready",
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
                "project_id": 10,
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
                "project_id": 10,
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
                "project_id": 10,
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
                "project_id": 10,
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
            {
                "id": "asset-img-missing",
                "project_id": 10,
                "thread_id": 102,
                "user_id": USER_ID,
                "media_kind": "image",
                "provenance": "uploaded",
                "source_tag": "uploaded",
                "content_hash": "hash-img-missing",
                "deterministic_id": "imgdet3",
                "normalized_slug": "missing",
                "system_name": "missing.png",
                "storage_prefix": "images/",
                "src_url": "/media/images/missing.png",
                "mime_type": "image/png",
                "filesize": 1024,
                "ingested_at": _utc("2026-03-12T03:00:00Z"),
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
                "project_id": 10,
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
                        "tests/routes/test_account_restore.py",
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
                        "artifacts": ["tests/routes/test_account_restore.py"],
                        "metadata": {},
                    },
                },
                "created_at": _utc("2026-03-14T00:00:00Z"),
                "updated_at": _utc("2026-03-14T01:00:00Z"),
            }
        ],
    }


def _build_export_db(rows: dict[str, list[dict[str, object]]]):
    calls: list[str] = []

    def _fetch(user_id: str):
        calls.append(user_id)
        return rows

    return SimpleNamespace(fetch_account_export_bundle_for_user=_fetch), calls


def _zip_bytes_from_archive(archive_path: str) -> bytes:
    payload = Path(archive_path).read_bytes()
    return payload


def _read_manifest(archive_bytes: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(archive_bytes), "r") as archive:
        return json.loads(archive.read("manifest.json").decode("utf-8"))


def _rewrite_archive_member(
    archive_bytes: bytes,
    member_path: str,
    transform,
) -> bytes:
    src = zipfile.ZipFile(io.BytesIO(archive_bytes), "r")
    buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(
            buffer, "w", compression=zipfile.ZIP_DEFLATED
        ) as dst:
            for info in src.infolist():
                if info.is_dir():
                    continue
                body = src.read(info.filename)
                if info.filename == member_path:
                    body = transform(body)
                dst.writestr(info.filename, body)
        return buffer.getvalue()
    finally:
        src.close()


class FakeAccountRestoreDB:
    TABLE_SPECS = {
        "projects": {
            "pk": "id",
            "columns": (
                "id",
                "name",
                "description",
                "icon",
                "identity_depth",
                "created_at",
                "updated_at",
            ),
            "unique": (("name",),),
        },
        "chat_threads": {
            "pk": "id",
            "columns": (
                "id",
                "user_id",
                "title",
                "summary",
                "project_id",
                "parent_id",
                "archived_at",
                "is_diary",
                "diary_mode",
                "exclude_from_identity",
                "modeling_excluded",
                "metadata",
                "active_profile_id",
                "created_at",
                "updated_at",
            ),
        },
        "chat_messages": {
            "pk": "id",
            "columns": (
                "id",
                "thread_id",
                "role",
                "content",
                "event_at",
                "kind",
                "extra_meta",
                "created_at",
            ),
        },
        "media_assets": {
            "pk": "id",
            "columns": (
                "id",
                "project_id",
                "thread_id",
                "user_id",
                "media_kind",
                "provenance",
                "source_tag",
                "content_hash",
                "deterministic_id",
                "normalized_slug",
                "system_name",
                "storage_prefix",
                "src_url",
                "mime_type",
                "filesize",
                "ingested_at",
                "deleted_at",
            ),
        },
        "media_aliases": {
            "pk": "id",
            "columns": (
                "id",
                "asset_id",
                "alias",
                "alias_normalized",
                "alias_type",
                "created_at",
            ),
        },
        "uploaded_documents": {
            "pk": "id",
            "columns": (
                "id",
                "asset_id",
                "project_id",
                "thread_id",
                "user_id",
                "filename",
                "filesize",
                "mime_type",
                "src_url",
                "source_tag",
                "parsed_text",
                "embedding_status",
                "embedding_error",
                "embedding_started_at",
                "embedding_completed_at",
                "created_at",
                "updated_at",
                "deleted_at",
            ),
        },
        "generated_documents": {
            "pk": "id",
            "columns": (
                "id",
                "project_id",
                "thread_id",
                "user_id",
                "title",
                "content",
                "format",
                "model",
                "created_at",
                "updated_at",
                "deleted_at",
            ),
        },
        "uploaded_images": {
            "pk": "id",
            "columns": (
                "id",
                "asset_id",
                "project_id",
                "thread_id",
                "user_id",
                "src_url",
                "filename",
                "filesize",
                "mime_type",
                "source_tag",
                "created_at",
                "updated_at",
                "deleted_at",
            ),
        },
        "generated_images": {
            "pk": "id",
            "columns": (
                "id",
                "asset_id",
                "project_id",
                "thread_id",
                "user_id",
                "src_url",
                "prompt",
                "model",
                "created_at",
                "updated_at",
                "deleted_at",
            ),
        },
        "thread_documents": {
            "pk": "id",
            "columns": (
                "id",
                "thread_id",
                "document_id",
                "relation",
                "created_at",
            ),
        },
        "project_document_links": {
            "pk": "id",
            "columns": (
                "id",
                "project_id",
                "document_id",
                "document_type",
                "is_enabled",
                "attached_at",
                "attached_by",
            ),
            "unique": (("project_id", "document_id", "document_type"),),
        },
        "extension_proposals": {
            "pk": "proposal_id",
            "columns": (
                "proposal_id",
                "account_id",
                "project_id",
                "profile_id",
                "source_thread_id",
                "source_message_id",
                "target_surface_token",
                "scope_token",
                "status_token",
                "requested_permissions_json",
                "declared_dependencies_json",
                "rollback_metadata_json",
                "test_evidence_json",
                "manifest_json",
                "created_at",
                "updated_at",
            ),
        },
    }

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.tables: dict[str, dict[Any, dict[str, Any]]] = {
            family: {} for family in self.TABLE_SPECS
        }

    @staticmethod
    def _normalize(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: FakeAccountRestoreDB._normalize(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [FakeAccountRestoreDB._normalize(item) for item in value]
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                return str(value)
        return value

    def _restore_family(
        self, family: str, rows: list[dict[str, Any]]
    ) -> dict[str, int]:
        self.calls.append(family)
        spec = self.TABLE_SPECS[family]
        pk_column = str(spec["pk"])
        columns = tuple(spec["columns"])
        unique_keys = tuple(spec.get("unique", ()))
        imported = 0
        skipped = 0
        for raw_row in rows:
            row = dict(raw_row)
            normalized = {
                column: self._normalize(row.get(column)) for column in columns
            }
            missing = [column for column in columns if column not in row]
            if missing:
                raise ValueError(
                    f"{family} row is missing required columns: {missing}"
                )
            pk_value = normalized[pk_column]
            existing = self.tables[family].get(pk_value)
            if existing is not None:
                if existing == normalized:
                    skipped += 1
                    continue
                raise ValueError(
                    f"{family} row {pk_value!r} conflicts with existing data"
                )
            for unique_columns in unique_keys:
                for other_pk, existing_row in self.tables[family].items():
                    if other_pk == pk_value:
                        continue
                    if all(
                        existing_row.get(column) == normalized.get(column)
                        for column in unique_columns
                    ):
                        raise ValueError(
                            f"{family} row {pk_value!r} conflicts with unique key {unique_columns}"
                        )
            self.tables[family][pk_value] = normalized
            imported += 1
        return {
            "imported": imported,
            "skipped": skipped,
            "failed": 0,
            "unresolved": 0,
        }

    def restore_account_export_projects(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("projects", rows)

    def restore_account_export_chat_threads(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("chat_threads", rows)

    def restore_account_export_chat_messages(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("chat_messages", rows)

    def restore_account_export_media_assets(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("media_assets", rows)

    def restore_account_export_media_aliases(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("media_aliases", rows)

    def restore_account_export_uploaded_documents(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("uploaded_documents", rows)

    def restore_account_export_generated_documents(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("generated_documents", rows)

    def restore_account_export_uploaded_images(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("uploaded_images", rows)

    def restore_account_export_generated_images(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("generated_images", rows)

    def restore_account_export_thread_documents(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("thread_documents", rows)

    def restore_account_export_project_document_links(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("project_document_links", rows)

    def restore_account_export_extension_proposals(self, rows, *, conn=None):
        _ = conn
        return self._restore_family("extension_proposals", rows)


@pytest.fixture
def rows() -> dict[str, list[dict[str, object]]]:
    return _build_rows()


@pytest.fixture
def archive_package(
    rows: dict[str, list[dict[str, object]]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    base_path = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_BASE_PATH", str(base_path))
    monkeypatch.setenv("STORAGE_URL_PREFIX", "/media")
    _write_blob(base_path, "documents/brief.pdf", b"brief-pdf-bytes")
    _write_blob(base_path, "images/uploaded.png", b"uploaded-image-bytes")
    _write_blob(
        base_path, "generated_images/generated.png", b"generated-image-bytes"
    )

    export_db, export_calls = _build_export_db(rows)
    archive_path = build_account_export_zip(
        export_db,
        SimpleNamespace(id=USER_ID),
    )
    try:
        payload = _zip_bytes_from_archive(archive_path)
        manifest = _read_manifest(payload)
        yield payload, manifest, export_calls
    finally:
        if os.path.exists(archive_path):
            os.unlink(archive_path)


@pytest.fixture
def restore_db() -> FakeAccountRestoreDB:
    return FakeAccountRestoreDB()


@pytest.fixture
def app(
    restore_db: FakeAccountRestoreDB, monkeypatch: pytest.MonkeyPatch
) -> FastAPI:
    monkeypatch.setattr(
        migration_routes, "chatlog_db", restore_db, raising=True
    )
    application = FastAPI()
    application.include_router(migration_routes.router)
    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _post_archive(
    client: TestClient,
    archive_bytes: bytes,
    *,
    path: str = "/imports/account/metadata",
    headers: dict[str, str] | None = None,
):
    request_headers = {
        "X-API-Key": os.environ["GUARDIAN_API_KEY"],
        "X-User-Id": USER_ID,
    }
    if headers:
        request_headers.update(headers)
    files = {"file": (ZIP_FILENAME, archive_bytes, "application/zip")}
    return client.post(path, files=files, headers=request_headers)


def test_account_metadata_restore_requires_auth(
    client: TestClient, archive_package
):
    archive_bytes, _manifest, _export_calls = archive_package
    response = client.post(
        "/imports/account/metadata",
        files={"file": (ZIP_FILENAME, archive_bytes, "application/zip")},
    )
    assert response.status_code in {401, 403}


def test_account_metadata_restore_rejects_invalid_manifest_before_write(
    client: TestClient,
    archive_package,
    restore_db: FakeAccountRestoreDB,
):
    archive_bytes, _manifest, _export_calls = archive_package

    def _mutate_manifest(body: bytes) -> bytes:
        manifest = json.loads(body.decode("utf-8"))
        manifest["export_kind"] = "partial_account"
        return json.dumps(
            manifest, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    mutated = _rewrite_archive_member(
        archive_bytes, "manifest.json", _mutate_manifest
    )
    response = _post_archive(client, mutated)

    assert response.status_code == 400
    data = response.json()
    assert data["ok"] is False
    assert data["validated"] is False
    assert data["error"]["code"] == "export_kind_invalid"
    assert restore_db.calls == []


def test_account_metadata_restore_rejects_integrity_mismatch_before_write(
    client: TestClient,
    archive_package,
    restore_db: FakeAccountRestoreDB,
):
    archive_bytes, _manifest, _export_calls = archive_package

    def _mutate_payload(body: bytes) -> bytes:
        payload = json.loads(body.decode("utf-8"))
        payload[0]["filename"] = "broken.pdf"
        return json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")

    mutated = _rewrite_archive_member(
        archive_bytes, "entities/uploaded_documents.json", _mutate_payload
    )
    response = _post_archive(client, mutated)

    assert response.status_code == 400
    data = response.json()
    assert data["ok"] is False
    assert data["validated"] is False
    assert data["error"]["code"] == "integrity_mismatch"
    assert restore_db.calls == []


def test_account_metadata_restore_imports_clean_fixture(
    client: TestClient,
    archive_package,
    restore_db: FakeAccountRestoreDB,
    rows: dict[str, list[dict[str, object]]],
):
    archive_bytes, manifest, export_calls = archive_package
    assert export_calls == [USER_ID]

    response = _post_archive(client, archive_bytes)
    assert response.status_code == 200
    report = response.json()

    assert report["ok"] is True
    assert report["validated"] is True
    assert report["metadata_restore_only"] is True
    assert report["blob_restore_supported"] is False
    assert report["archive_includes_blob_coverage"] is True
    assert report["blob_coverage"]["validated_only"] is True
    assert "not written back to storage" in " ".join(report["notes"]).lower()

    assert [family["family"] for family in report["families"]] == list(
        RESTORE_ORDER
    )
    assert restore_db.calls == list(RESTORE_ORDER)

    expected_total = sum(len(value) for value in rows.values())
    expected_unresolved = len(manifest["blob_coverage"]["unresolved_rows"])
    assert report["counts"]["imported"] == expected_total
    assert report["counts"]["skipped"] == 0
    assert report["counts"]["failed"] == 0
    assert report["counts"]["unresolved"] == expected_unresolved

    per_family = {family["family"]: family for family in report["families"]}
    for family_name, payload_rows in rows.items():
        assert per_family[family_name]["payload_rows"] == len(payload_rows)
        assert per_family[family_name]["imported"] == len(payload_rows)
        assert per_family[family_name]["failed"] == 0

    assert restore_db.tables["projects"][10]["name"] == "Project Alpha"
    assert restore_db.tables["chat_threads"][102]["parent_id"] == 101
    assert (
        restore_db.tables["chat_threads"][101]["metadata"]["source_thread_id"]
        == "source-1"
    )
    assert restore_db.tables["thread_documents"][1]["document_id"] == "ud-1"
    assert (
        restore_db.tables["project_document_links"][2]["document_type"]
        == "generated"
    )
    assert (
        restore_db.tables["media_assets"]["asset-img-missing"]["src_url"]
        == "/media/images/missing.png"
    )
    assert (
        restore_db.tables["uploaded_images"]["ui-missing"]["asset_id"]
        == "asset-img-missing"
    )


def test_account_metadata_restore_is_idempotent_on_reimport(
    client: TestClient,
    archive_package,
    restore_db: FakeAccountRestoreDB,
):
    archive_bytes, manifest, _export_calls = archive_package

    first_response = _post_archive(client, archive_bytes)
    assert first_response.status_code == 200
    first_state = deepcopy(restore_db.tables)

    second_response = _post_archive(client, archive_bytes)
    assert second_response.status_code == 200
    report = second_response.json()

    expected_total = sum(
        len(family_rows) for family_rows in first_state.values()
    )
    assert report["counts"]["imported"] == 0
    assert report["counts"]["skipped"] == expected_total
    assert report["counts"]["failed"] == 0
    assert report["counts"]["unresolved"] == len(
        manifest["blob_coverage"]["unresolved_rows"]
    )
    assert any(
        family["status"] == "already_present" for family in report["families"]
    )
    assert any(
        family["status"] == "unresolved" for family in report["families"]
    )
    assert restore_db.tables == first_state


def test_account_metadata_restore_reports_metadata_only_and_blob_validation(
    client: TestClient,
    archive_package,
):
    archive_bytes, manifest, _export_calls = archive_package
    response = _post_archive(client, archive_bytes)

    assert response.status_code == 200
    report = response.json()
    assert report["metadata_restore_only"] is True
    assert report["blob_restore_supported"] is False
    assert report["archive_includes_blob_coverage"] is True
    assert report["blob_coverage"]["validated_only"] is True
    assert report["blob_coverage"]["bundled_blob_paths"]
    assert (
        report["blob_coverage"]["unresolved_rows"]
        == manifest["blob_coverage"]["unresolved_rows"]
    )
    assert any(
        "validated" in note.lower()
        and "not written back to storage" in note.lower()
        for note in report["notes"]
    )
