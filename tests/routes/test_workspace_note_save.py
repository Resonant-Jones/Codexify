from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from guardian.core.dependencies import RequestUserScope
from guardian.routes import documents


def _scope(account="owner-a"):
    return RequestUserScope(
        user_id=account, account_id=account, multi_user_enabled=True
    )


def _setup(thread_owner="owner-a", project_owner="owner-a", project_id=7):
    session = MagicMock()
    db = MagicMock()
    db.get_session.return_value.__enter__.return_value = session
    thread = SimpleNamespace(id=11, user_id=thread_owner, project_id=project_id)
    project = SimpleNamespace(id=7, user_id=project_owner)

    def query(model):
        result = MagicMock()
        if model is documents.models.ChatThread:
            result.filter_by.return_value.first.return_value = thread
        elif model is documents.models.Project:
            result.filter_by.return_value.first.return_value = project
        elif model is documents.models.ProjectDocumentLink:
            result.filter_by.return_value.first.return_value = None
        return result

    session.query.side_effect = query
    documents.configure_db(db)
    return session


@pytest.mark.asyncio
async def test_save_creates_new_snapshots_with_canonical_links_and_owner():
    session = _setup()
    request = documents.WorkspaceNoteSaveRequest(
        thread_id=11,
        title="Guardian Notes.md",
        content="# exact authored text\n",
        format="md",
    )
    with (
        patch.object(documents.uuid, "uuid4", side_effect=["doc-1", "doc-2"]),
        patch.object(documents, "chat_with_ai") as model_call,
    ):
        first = await documents.save_workspace_note(
            request, _api_key="key", request_user_scope=_scope()
        )
        second = await documents.save_workspace_note(
            request, _api_key="key", request_user_scope=_scope()
        )
    model_call.assert_not_called()
    assert first["document_id"] != second["document_id"]
    assert first["filename"] == "Guardian Notes.md"
    assert first["project_id"] == 7
    assert first["relation"] == "attached"
    assert first["project_linked"] is True
    assert session.commit.call_count == 2
    added = [call.args[0] for call in session.add.call_args_list]
    generated = [
        row for row in added if isinstance(row, documents.models.GeneratedDocument)
    ]
    thread_links = [
        row for row in added if isinstance(row, documents.models.ThreadDocument)
    ]
    project_links = [
        row for row in added if isinstance(row, documents.models.ProjectDocumentLink)
    ]
    assert len(generated) == len(thread_links) == len(project_links) == 2
    assert [row.id for row in generated] == ["doc-1", "doc-2"]
    assert all(
        row.content == "# exact authored text\n"
        and row.user_id == "owner-a"
        and row.model == "workspace_notes"
        for row in generated
    )
    assert all(
        row.thread_id == 11 and row.relation == "attached" for row in thread_links
    )
    assert all(
        row.project_id == 7
        and row.document_type == "generated"
        and row.attached_by == "owner-a"
        for row in project_links
    )


@pytest.mark.asyncio
async def test_save_rejects_cross_account_thread_and_project():
    for thread_owner, project_owner in [("owner-b", "owner-a"), ("owner-a", "owner-b")]:
        session = _setup(thread_owner, project_owner)
        with pytest.raises(HTTPException) as exc:
            await documents.save_workspace_note(
                documents.WorkspaceNoteSaveRequest(
                    thread_id=11, title="Note", content="body", format="txt"
                ),
                _api_key="key",
                request_user_scope=_scope(),
            )
        assert exc.value.status_code == 403
        session.add.assert_not_called()
        session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_save_validates_inputs_and_requires_project():
    for title, content, format_ in [
        (" ", "body", "md"),
        ("Note", " ", "md"),
        ("Note", "body", "pdf"),
        ("Note.pdf", "body", "md"),
        ("Note.txt", "body", "md"),
    ]:
        with pytest.raises(HTTPException) as exc:
            await documents.save_workspace_note(
                documents.WorkspaceNoteSaveRequest(
                    thread_id=11, title=title, content=content, format=format_
                ),
                _api_key="key",
                request_user_scope=_scope(),
            )
        assert exc.value.status_code == 400
    session = _setup(project_id=None)
    with pytest.raises(HTTPException) as exc:
        await documents.save_workspace_note(
            documents.WorkspaceNoteSaveRequest(
                thread_id=11, title="Note", content="body", format="md"
            ),
            _api_key="key",
            request_user_scope=_scope(),
        )
    assert exc.value.status_code == 409
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_save_commit_failure_does_not_report_success():
    session = _setup()
    session.commit.side_effect = RuntimeError("database unavailable")
    with pytest.raises(HTTPException) as exc:
        await documents.save_workspace_note(
            documents.WorkspaceNoteSaveRequest(
                thread_id=11, title="Note", content="body", format="md"
            ),
            _api_key="key",
            request_user_scope=_scope(),
        )
    assert exc.value.status_code == 500
    assert session.add.call_count == 3
