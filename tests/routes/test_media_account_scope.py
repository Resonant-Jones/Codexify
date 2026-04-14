from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope
from guardian.routes import media as media_routes

API_KEY = "test-api-key"


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *args, **kwargs):
        return self

    def filter_by(self, **kwargs):
        rows = self._rows
        for key, value in kwargs.items():
            rows = [
                row
                for row in rows
                if getattr(row, key, None) == value
                or (isinstance(row, dict) and row.get(key) == value)
            ]
        return _FakeQuery(rows)

    def join(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, count):
        return _FakeQuery(self._rows[:count])

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeSession:
    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model
        self.added = []
        self.commit = MagicMock()
        self.rollback = MagicMock()
        self.flush = MagicMock()
        self.refresh = MagicMock()

    def query(self, model):
        return _FakeQuery(self.rows_by_model.get(model, []))

    def add(self, obj):
        self.added.append(obj)


def _make_db(rows_by_model=None):
    db = MagicMock()
    session = _FakeSession(rows_by_model or {})
    db.get_session.return_value.__enter__.return_value = session
    db.get_session.return_value.__exit__.return_value = False
    return db, session


def _make_client(monkeypatch, scope: RequestUserScope, db) -> TestClient:
    monkeypatch.setattr(media_routes, "_get_db", lambda: db)
    app = FastAPI()
    app.dependency_overrides[
        media_routes.get_request_user_scope
    ] = lambda: scope
    app.include_router(media_routes.router, prefix="/api/media")
    return TestClient(app)


def _owned_row(
    *,
    row_id: str,
    user_id: str,
    kind: str,
    **extra,
):
    payload = {
        "id": row_id,
        "user_id": user_id,
        "deleted_at": None,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    if kind == "image":
        payload.update(
            {
                "src_url": f"/media/{row_id}.png",
                "filename": f"{row_id}.png",
                "filesize": 10,
                "mime_type": "image/png",
                "source_tag": "uploaded",
                "project_id": extra.get("project_id", 7),
                "thread_id": extra.get("thread_id", 11),
            }
        )
    elif kind == "generated_image":
        payload.update(
            {
                "src_url": f"/media/{row_id}.png",
                "prompt": extra.get("prompt", "prompt"),
                "model": "dall-e-3",
                "project_id": extra.get("project_id", 7),
                "thread_id": extra.get("thread_id", 11),
            }
        )
    elif kind == "document":
        payload.update(
            {
                "project_id": extra.get("project_id", 7),
                "thread_id": extra.get("thread_id", 11),
                "src_url": f"/media/{row_id}.txt",
                "filename": f"{row_id}.txt",
                "filesize": 42,
                "mime_type": "text/plain",
                "source_tag": "uploaded",
                "parsed_text": "owned text",
                "embedding_status": "pending",
                "embedding_error": None,
                "embedding_started_at": None,
                "embedding_completed_at": None,
            }
        )
    return SimpleNamespace(**payload)


def _foreign_asset(asset_id: str, user_id: str):
    return SimpleNamespace(
        id=asset_id,
        user_id=user_id,
        src_url=f"/media/{asset_id}.png",
        media_kind="image",
        provenance="uploaded",
        source_tag="uploaded",
        ingested_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        deleted_at=None,
    )


@pytest.fixture(autouse=True)
def _base_env(monkeypatch):
    monkeypatch.setenv("GUARDIAN_API_KEY", API_KEY)
    monkeypatch.setenv("STORAGE_BASE_PATH", "/tmp/test_media_scope")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("CODEXIFY_DISABLE_DOTENV", "1")


def test_single_user_media_behavior_remains_compatible(monkeypatch):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "false")
    rows_by_model = {
        media_routes.UploadedImage: [
            _owned_row(row_id="img-owned", user_id="legacy-user", kind="image"),
            _owned_row(
                row_id="img-foreign", user_id="foreign-user", kind="image"
            ),
        ],
    }
    db, session = _make_db(rows_by_model)
    client = _make_client(
        monkeypatch,
        RequestUserScope(
            user_id="legacy-user",
            subject_id=None,
            account_id=None,
            multi_user_enabled=False,
        ),
        db,
    )
    monkeypatch.setattr(
        media_routes,
        "_resolve_upload_context",
        lambda *_args, **_kwargs: (7, 11),
    )
    monkeypatch.setattr(
        media_routes,
        "_require_project_account_scope",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        media_routes,
        "_require_thread_account_scope",
        lambda *_args, **_kwargs: {},
    )
    storage = SimpleNamespace(
        upload_file=MagicMock(return_value="/media/new-upload.png"),
        download_file=MagicMock(return_value=b"bytes"),
    )
    monkeypatch.setattr(media_routes, "storage", storage)

    list_response = client.get(
        "/api/media/images", headers={"X-API-Key": API_KEY}
    )
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 2

    upload_response = client.post(
        "/api/media/upload/image",
        headers={"X-API-Key": API_KEY},
        data={"project_id": "7", "thread_id": "11", "user_id": "legacy-user"},
        files={"file": ("legacy.png", b"legacy-bytes", "image/png")},
    )
    assert upload_response.status_code == 200, upload_response.text

    uploaded_image = next(
        obj
        for obj in session.added
        if obj.__class__.__name__ == "UploadedImage"
    )
    assert uploaded_image.user_id == "legacy-user"


def test_multi_user_upload_persists_authenticated_principal_as_owner(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    db, session = _make_db()
    client = _make_client(
        monkeypatch,
        RequestUserScope(
            user_id="owner-a",
            subject_id="subject-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
        db,
    )
    monkeypatch.setattr(
        media_routes,
        "_resolve_upload_context",
        lambda *_args, **_kwargs: (7, 11),
    )
    monkeypatch.setattr(
        media_routes,
        "_require_project_account_scope",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        media_routes,
        "_require_thread_account_scope",
        lambda *_args, **_kwargs: {},
    )
    storage = SimpleNamespace(
        upload_file=MagicMock(return_value="/media/new-owned.png"),
        download_file=MagicMock(return_value=b"bytes"),
    )
    monkeypatch.setattr(media_routes, "storage", storage)

    response = client.post(
        "/api/media/upload/image",
        headers={"X-API-Key": API_KEY},
        data={"project_id": "7", "thread_id": "11"},
        files={"file": ("owned.png", b"owned-bytes", "image/png")},
    )

    assert response.status_code == 200, response.text

    media_asset = next(
        obj for obj in session.added if obj.__class__.__name__ == "MediaAsset"
    )
    uploaded_image = next(
        obj
        for obj in session.added
        if obj.__class__.__name__ == "UploadedImage"
    )
    assert media_asset.user_id == "owner-a"
    assert uploaded_image.user_id == "owner-a"


def test_multi_user_list_read_returns_only_owned_media(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    owned_image = _owned_row(
        row_id="img-owned", user_id="owner-a", kind="image"
    )
    foreign_image = _owned_row(
        row_id="img-foreign", user_id="owner-b", kind="image"
    )
    owned_generated = _owned_row(
        row_id="gen-owned",
        user_id="owner-a",
        kind="generated_image",
        prompt="Owned prompt",
    )
    foreign_generated = _owned_row(
        row_id="gen-foreign",
        user_id="owner-b",
        kind="generated_image",
        prompt="Foreign prompt",
    )
    owned_document = _owned_row(
        row_id="doc-owned", user_id="owner-a", kind="document"
    )
    foreign_document = _owned_row(
        row_id="doc-foreign", user_id="owner-b", kind="document"
    )
    foreign_asset = _foreign_asset("asset-foreign", "owner-b")

    rows_by_model = {
        media_routes.UploadedImage: [owned_image, foreign_image],
        media_routes.GeneratedImage: [owned_generated, foreign_generated],
        media_routes.UploadedDocument: [owned_document, foreign_document],
        media_routes.MediaAsset: [foreign_asset],
    }
    db, _session = _make_db(rows_by_model)
    client = _make_client(
        monkeypatch,
        RequestUserScope(
            user_id="owner-a",
            subject_id="subject-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
        db,
    )
    monkeypatch.setattr(
        media_routes,
        "_require_project_account_scope",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        media_routes,
        "_require_thread_account_scope",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        media_routes,
        "resolve_asset_from_aliases",
        lambda *args, **kwargs: foreign_asset,
    )

    images_response = client.get(
        "/api/media/images", headers={"X-API-Key": API_KEY}
    )
    assert images_response.status_code == 200
    assert images_response.json()["count"] == 1
    assert images_response.json()["images"][0]["id"] == "img-owned"

    generated_response = client.get(
        "/api/media/images?tag=generated", headers={"X-API-Key": API_KEY}
    )
    assert generated_response.status_code == 200
    assert generated_response.json()["count"] == 1
    assert generated_response.json()["images"][0]["id"] == "gen-owned"

    documents_response = client.get(
        "/api/media/documents", headers={"X-API-Key": API_KEY}
    )
    assert documents_response.status_code == 200
    assert documents_response.json()["count"] == 1
    assert documents_response.json()["documents"][0]["id"] == "doc-owned"

    foreign_image_read = client.get(
        "/api/media/images/img-foreign", headers={"X-API-Key": API_KEY}
    )
    assert foreign_image_read.status_code == 403

    foreign_document_read = client.get(
        "/api/media/documents/doc-foreign", headers={"X-API-Key": API_KEY}
    )
    assert foreign_document_read.status_code == 403

    foreign_asset_resolve = client.get(
        "/api/media/resolve",
        headers={"X-API-Key": API_KEY},
        params={"project_id": 7, "q": "secret"},
    )
    assert foreign_asset_resolve.status_code == 403


def test_multi_user_thread_and_project_hints_are_rejected(monkeypatch):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    db, _session = _make_db()
    client = _make_client(
        monkeypatch,
        RequestUserScope(
            user_id="owner-a",
            subject_id="subject-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
        db,
    )

    def deny_foreign_thread(*_args, **kwargs):
        thread_id = kwargs.get("thread_id")
        if thread_id is None and len(_args) >= 2:
            thread_id = _args[1]
        if thread_id == 99:
            raise HTTPException(
                status_code=403,
                detail="Thread does not belong to the authenticated account",
            )
        return {}

    def deny_foreign_project(*_args, **kwargs):
        project_id = kwargs.get("project_id")
        if project_id is None and len(_args) >= 2:
            project_id = _args[1]
        if project_id == 98:
            raise HTTPException(
                status_code=403,
                detail="Project does not belong to the authenticated account",
            )
        return {}

    monkeypatch.setattr(
        media_routes, "_require_thread_account_scope", deny_foreign_thread
    )
    monkeypatch.setattr(
        media_routes, "_require_project_account_scope", deny_foreign_project
    )

    thread_response = client.get(
        "/api/media/images?thread_id=99", headers={"X-API-Key": API_KEY}
    )
    assert thread_response.status_code == 403

    project_response = client.get(
        "/api/media/documents?project_id=98", headers={"X-API-Key": API_KEY}
    )
    assert project_response.status_code == 403


def test_multi_user_delete_rejects_cross_account_access(monkeypatch):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    rows_by_model = {
        media_routes.UploadedImage: [
            _owned_row(row_id="img-foreign", user_id="owner-b", kind="image")
        ],
    }
    db, _session = _make_db(rows_by_model)
    client = _make_client(
        monkeypatch,
        RequestUserScope(
            user_id="owner-a",
            subject_id="subject-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
        db,
    )

    response = client.delete(
        "/api/media/images/img-foreign", headers={"X-API-Key": API_KEY}
    )
    assert response.status_code == 403


def test_conflicting_caller_supplied_user_id_is_rejected_in_multi_user_mode(
    monkeypatch,
):
    monkeypatch.setenv("CODEXIFY_MULTI_USER_ENABLED", "true")
    db, _session = _make_db()
    client = _make_client(
        monkeypatch,
        RequestUserScope(
            user_id="owner-a",
            subject_id="subject-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
        db,
    )
    monkeypatch.setattr(
        media_routes,
        "_resolve_upload_context",
        lambda *_args, **_kwargs: (7, 11),
    )
    monkeypatch.setattr(
        media_routes,
        "_require_project_account_scope",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        media_routes,
        "_require_thread_account_scope",
        lambda *_args, **_kwargs: {},
    )
    storage = SimpleNamespace(
        upload_file=MagicMock(return_value="/media/rejected.png"),
        download_file=MagicMock(return_value=b"bytes"),
    )
    monkeypatch.setattr(media_routes, "storage", storage)

    response = client.post(
        "/api/media/upload/image",
        headers={"X-API-Key": API_KEY},
        data={
            "project_id": "7",
            "thread_id": "11",
            "user_id": "owner-b",
        },
        files={"file": ("rejected.png", b"rejected-bytes", "image/png")},
    )

    assert response.status_code == 403
    assert "authenticated account" in response.json()["detail"]
