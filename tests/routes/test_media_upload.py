from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _doc_row(*, user_id: str = "user-a", embedding_status: str = "pending"):
    now = datetime(2026, 5, 8, tzinfo=timezone.utc)
    return SimpleNamespace(
        id="doc-123",
        asset_id="asset-123",
        project_id=7,
        thread_id=11,
        user_id=user_id,
        src_url="/media/documents/doc-123.txt",
        filename="doc.txt",
        filesize=42,
        mime_type="text/plain",
        source_tag="uploaded",
        parsed_text="sentinel text",
        embedding_status=embedding_status,
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
        created_at=now,
        deleted_at=None,
    )


def test_document_upload_returns_document_and_asset_identity():
    from guardian.routes import media

    app = FastAPI()
    app.include_router(media.router, prefix="/api/media")
    client = TestClient(app, headers={"X-API-Key": "test"})

    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    mock_db.get_session.return_value.__exit__.return_value = False

    fake_document = _doc_row()

    with (
        patch("guardian.routes.media.verify_api_key", return_value="test"),
        patch("guardian.routes.media._get_db", return_value=mock_db),
        patch(
            "guardian.routes.media._resolve_upload_context",
            return_value=(7, 11),
        ),
        patch("guardian.routes.media._require_project_account_scope"),
        patch("guardian.routes.media._require_thread_account_scope"),
        patch(
            "guardian.routes.media._compute_identity_with_existing_asset",
            return_value=(SimpleNamespace(), SimpleNamespace(id="asset-123")),
        ),
        patch(
            "guardian.routes.media._find_uploaded_document_for_asset",
            return_value=fake_document,
        ),
        patch("guardian.routes.media._ensure_thread_document_link"),
        patch("guardian.routes.media._ensure_project_document_link"),
        patch("guardian.routes.media.ensure_asset_alias"),
    ):
        response = client.post(
            "/api/media/upload/document",
            files={"file": ("doc.txt", b"sentinel text", "text/plain")},
            data={"project_id": "7", "thread_id": "11", "user_id": "user-a"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "doc-123"
    assert payload["document_id"] == "doc-123"
    assert payload["media_asset_id"] == "asset-123"
    assert payload["embedding_status"] == "pending"
