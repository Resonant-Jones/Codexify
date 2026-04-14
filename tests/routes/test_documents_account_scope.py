from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.routes import documents


def _configure_session(mock_db: MagicMock) -> MagicMock:
    mock_session = MagicMock()
    mock_db.get_session.return_value.__enter__.return_value = mock_session
    return mock_session


def _install_document_models(mock_models: MagicMock) -> None:
    mock_models.ChatThread = MagicMock()
    mock_models.ThreadDocument = MagicMock()
    mock_models.GeneratedDocument = MagicMock()
    mock_models.UploadedDocument = MagicMock()
    mock_models.ProjectDocumentLink = MagicMock()


@pytest.mark.asyncio
@patch("guardian.routes.documents.models")
@patch("guardian.routes.documents.event_bus.emit_event")
async def test_single_user_autosave_preserves_legacy_thread_owner(
    mock_emit, mock_models, mock_db
):
    mock_session = _configure_session(mock_db)
    mock_emit.return_value = None
    _install_document_models(mock_models)

    thread = MagicMock()
    thread.id = 1
    thread.user_id = "legacy-user"
    thread.title = "Legacy Thread"
    thread.project_id = 7

    thread_query = MagicMock()
    thread_query.filter_by.return_value.first.return_value = thread

    thread_doc_query = MagicMock()
    thread_doc_query.filter_by.return_value.first.return_value = None

    project_link_query = MagicMock()
    project_link_query.filter_by.return_value.first.return_value = None

    def query_side_effect(model):
        if model == mock_models.ChatThread:
            return thread_query
        if model == mock_models.ThreadDocument:
            return thread_doc_query
        if model == mock_models.ProjectDocumentLink:
            return project_link_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect
    documents.configure_db(mock_db)

    result = await documents.autosave_document(
        documents.AutosaveRequest(thread_id=1, content="Session notes"),
        _api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id="local",
            account_id="local",
            multi_user_enabled=False,
        ),
    )

    assert result["ok"] is True
    assert mock_models.GeneratedDocument.call_args.kwargs["user_id"] == (
        "legacy-user"
    )
    assert mock_models.ProjectDocumentLink.call_args.kwargs["attached_by"] == (
        "legacy-user"
    )


@pytest.mark.asyncio
@patch("guardian.routes.documents.models")
@patch("guardian.routes.documents.uuid.uuid4")
@patch("guardian.routes.documents.chat_with_ai")
async def test_multi_user_generate_document_persists_account_owner(
    mock_chat_with_ai, mock_uuid, mock_models, mock_db
):
    mock_session = _configure_session(mock_db)
    _install_document_models(mock_models)
    mock_uuid.return_value = type(
        "UuidStub",
        (),
        {"__str__": lambda self: "12345678-1234-5678-1234-567812345678"},
    )()
    mock_chat_with_ai.return_value = "generated content"

    thread = MagicMock()
    thread.id = 1
    thread.user_id = "owner-a"
    thread.project_id = 7
    thread.title = "Thread Title"

    thread_query = MagicMock()
    thread_query.filter_by.return_value.first.return_value = thread

    project_link_query = MagicMock()
    project_link_query.filter_by.return_value.first.return_value = None

    def query_side_effect(model):
        if model == mock_models.ChatThread:
            return thread_query
        if model == mock_models.ProjectDocumentLink:
            return project_link_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect
    documents.configure_db(mock_db)

    result = await documents.generate_document(
        documents.DocumentGenerateRequest(
            thread_id=1,
            prompt="Draft a summary",
            user_id="owner-a",
        ),
        _api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id="owner-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
    )

    assert result["ok"] is True
    assert mock_models.GeneratedDocument.call_args.kwargs["user_id"] == (
        "owner-a"
    )
    assert mock_models.ThreadDocument.call_args.kwargs["thread_id"] == 1
    assert mock_models.ProjectDocumentLink.call_args.kwargs["attached_by"] == (
        "owner-a"
    )


@pytest.mark.asyncio
@patch("guardian.routes.documents.models")
async def test_multi_user_thread_documents_return_owned_thread_data(
    mock_models, mock_db
):
    mock_session = _configure_session(mock_db)
    _install_document_models(mock_models)

    thread = MagicMock()
    thread.id = 1
    thread.user_id = "owner-a"

    link = MagicMock()
    link.id = 1
    link.thread_id = 1
    link.document_id = "doc-1"
    link.relation = "attached"
    link.created_at = datetime(2025, 1, 1, 12, 0, 0)

    generated_doc = MagicMock()
    generated_doc.id = "doc-1"
    generated_doc.title = "Owned Doc"

    thread_query = MagicMock()
    thread_query.filter_by.return_value.first.return_value = thread

    link_query = MagicMock()
    link_query.filter_by.return_value.order_by.return_value.all.return_value = [
        link
    ]

    generated_query = MagicMock()
    generated_query.filter_by.return_value.first.return_value = generated_doc

    uploaded_query = MagicMock()
    uploaded_query.filter_by.return_value.first.return_value = None

    def query_side_effect(model):
        if model == mock_models.ChatThread:
            return thread_query
        if model == mock_models.ThreadDocument:
            return link_query
        if model == mock_models.GeneratedDocument:
            return generated_query
        if model == mock_models.UploadedDocument:
            return uploaded_query
        return MagicMock()

    mock_session.query.side_effect = query_side_effect
    documents.configure_db(mock_db)

    result = await documents.get_thread_documents(
        1,
        _api_key="test-api-key",
        request_user_scope=RequestUserScope(
            user_id="owner-a",
            account_id="owner-a",
            multi_user_enabled=True,
        ),
    )

    assert result["ok"] is True
    assert result["documents"] == [
        {
            "id": "doc-1",
            "title": "Owned Doc",
            "relation": "attached",
            "created_at": "2025-01-01T12:00:00",
        }
    ]


@pytest.mark.asyncio
@patch("guardian.routes.documents.models")
async def test_multi_user_linked_document_lookup_rejects_cross_account_access(
    mock_models, mock_db
):
    mock_session = _configure_session(mock_db)
    _install_document_models(mock_models)

    thread = MagicMock()
    thread.id = 1
    thread.user_id = "owner-b"

    thread_query = MagicMock()
    thread_query.filter_by.return_value.first.return_value = thread

    mock_session.query.return_value = thread_query
    documents.configure_db(mock_db)

    with pytest.raises(HTTPException) as exc_info:
        await documents.get_thread_documents(
            1,
            _api_key="test-api-key",
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
@patch("guardian.routes.documents.chat_with_ai")
async def test_multi_user_conflicting_user_id_is_rejected(
    mock_chat_with_ai, mock_db
):
    mock_chat_with_ai.return_value = "generated content"
    documents.configure_db(mock_db)

    with pytest.raises(HTTPException) as exc_info:
        await documents.generate_document(
            documents.DocumentGenerateRequest(
                thread_id=1,
                prompt="Draft a summary",
                user_id="other-account",
            ),
            _api_key="test-api-key",
            request_user_scope=RequestUserScope(
                user_id="owner-a",
                account_id="owner-a",
                multi_user_enabled=True,
            ),
        )

    assert exc_info.value.status_code == 403
    mock_chat_with_ai.assert_not_called()
