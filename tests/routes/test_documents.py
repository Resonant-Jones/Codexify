from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core.dependencies import RequestUserScope
from guardian.routes import documents


def _uploaded_document(*, user_id: str = "owner-a"):
    return SimpleNamespace(
        id="doc-1",
        asset_id="asset-1",
        project_id=3,
        thread_id=9,
        user_id=user_id,
        src_url="/media/documents/doc-1.txt",
        filename="doc-1.txt",
        filesize=100,
        mime_type="text/plain",
        source_tag="uploaded",
        parsed_text="SENTINEL_UPLOAD_EMBED_RETRIEVE",
        embedding_status="ready",
        embedding_error=None,
        embedding_started_at=datetime(2026, 5, 8, tzinfo=timezone.utc),
        embedding_completed_at=datetime(2026, 5, 8, tzinfo=timezone.utc),
        created_at=datetime(2026, 5, 8, tzinfo=timezone.utc),
        deleted_at=None,
    )


@pytest.mark.asyncio
async def test_get_uploaded_document_detail_by_document_id():
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    documents.configure_db(mock_db)

    document = _uploaded_document()
    with patch(
        "guardian.routes.documents._resolve_uploaded_document_for_scope",
        return_value=(document, document.parsed_text),
    ):
        result = await documents.get_uploaded_document_detail(
            "doc-1",
            _api_key="test",
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert result["id"] == "doc-1"
    assert result["document_id"] == "doc-1"
    assert result["media_asset_id"] == "asset-1"
    assert result["embedding_status"] == "ready"


@pytest.mark.asyncio
async def test_get_uploaded_document_detail_by_asset_id():
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    documents.configure_db(mock_db)

    document = _uploaded_document()
    with patch(
        "guardian.routes.documents._resolve_uploaded_document_for_scope",
        return_value=(document, document.parsed_text),
    ):
        result = await documents.get_uploaded_document_detail(
            "asset-1",
            _api_key="test",
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert result["document_id"] == "doc-1"
    assert result["media_asset_id"] == "asset-1"


@pytest.mark.asyncio
async def test_get_uploaded_document_detail_forbidden_cross_account():
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    documents.configure_db(mock_db)

    with patch(
        "guardian.routes.documents._resolve_uploaded_document_for_scope",
        side_effect=HTTPException(
            status_code=403,
            detail="Document does not belong to the authenticated account",
        ),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await documents.get_uploaded_document_detail(
                "doc-1",
                _api_key="test",
                request_user_scope=RequestUserScope(
                    user_id="owner-b",
                    account_id="owner-b",
                    multi_user_enabled=True,
                ),
            )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_uploaded_document_detail_not_found():
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    documents.configure_db(mock_db)

    with patch(
        "guardian.routes.documents._resolve_uploaded_document_for_scope",
        side_effect=HTTPException(status_code=404, detail="Document not found"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await documents.get_uploaded_document_detail(
                "missing-id",
                _api_key="test",
                request_user_scope=RequestUserScope(
                    user_id="owner-a",
                    account_id="owner-a",
                    multi_user_enabled=True,
                ),
            )

    assert exc_info.value.status_code == 404


def test_preview_limits_utf8_payload_and_preserves_account_scope(monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    model = documents.models.UploadedDocument
    model.__table__.create(engine)
    session_factory = sessionmaker(bind=engine)
    prefix = "a" * (8 * 1024 - 1)
    text = prefix + "🧭" + ("remaining document\n" * 400_000)
    with session_factory.begin() as session:
        document = vars(_uploaded_document()) | {"parsed_text": text}
        session.add(model(**document))
        small = document | {"id": "small", "asset_id": None, "parsed_text": "short"}
        session.add(model(**small))

    monkeypatch.setattr(documents, "_db", SimpleNamespace(get_session=session_factory))
    app = FastAPI()
    app.include_router(documents.router)
    app.dependency_overrides[documents.require_api_key] = lambda: "test"
    account_id = "owner-a"
    app.dependency_overrides[documents.get_request_user_scope] = (
        lambda: RequestUserScope(
            user_id=account_id, account_id=account_id, multi_user_enabled=True
        )
    )

    with TestClient(app) as client:
        preview = client.get("/api/documents/asset-1", params={"preview": "true"})
        assert preview.status_code == 200
        assert preview.json()["document_id"] == "doc-1"
        assert preview.json()["parsed_text"] == prefix
        assert preview.json()["text_preview_truncated"] is True
        assert len(preview.content) < 10_000

        full = client.get("/api/documents/doc-1")
        assert full.status_code == 200
        assert full.json()["parsed_text"] == text
        assert "text_preview_truncated" not in full.json()

        small_preview = client.get("/api/documents/small", params={"preview": "true"})
        assert small_preview.status_code == 200
        assert small_preview.json()["parsed_text"] == "short"
        assert small_preview.json()["text_preview_truncated"] is False

        account_id = "owner-b"
        denied = client.get("/api/documents/asset-1", params={"preview": "true"})
        assert denied.status_code == 403
        assert "parsed_text" not in denied.json()
    engine.dispose()
