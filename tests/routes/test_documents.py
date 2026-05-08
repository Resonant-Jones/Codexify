from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

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

    with patch(
        "guardian.routes.documents._resolve_uploaded_document_for_scope",
        return_value=_uploaded_document(),
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

    with patch(
        "guardian.routes.documents._resolve_uploaded_document_for_scope",
        return_value=_uploaded_document(),
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
