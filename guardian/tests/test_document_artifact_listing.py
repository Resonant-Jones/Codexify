from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.core.dependencies import RequestUserScope
from guardian.routes import media as media_routes


class _FakeQuery:
    def __init__(self, rows):
        self._rows = list(rows)

    def filter(self, *expressions):
        rows = self._rows
        for expression in expressions:
            rows = [row for row in rows if _matches_expression(row, expression)]
        return _FakeQuery(rows)

    def filter_by(self, **values):
        rows = self._rows
        for key, value in values.items():
            rows = [row for row in rows if getattr(row, key, None) == value]
        return _FakeQuery(rows)

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, count):
        return _FakeQuery(self._rows[:count])

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


def _matches_expression(row, expression) -> bool:
    clauses = getattr(expression, "clauses", None)
    if clauses is not None:
        return all(_matches_expression(row, clause) for clause in clauses)

    left = getattr(expression, "left", None)
    right = getattr(expression, "right", None)
    key = getattr(left, "key", None)
    if not key:
        return True

    row_value = getattr(row, key, None)
    operator_name = getattr(getattr(expression, "operator", None), "__name__", "")
    if operator_name == "is_":
        return row_value is getattr(right, "value", None)
    if operator_name == "in_op":
        values = getattr(right, "value", [])
        return row_value in values
    return row_value == getattr(right, "value", None)


class _FakeSession:
    def __init__(self, rows_by_model):
        self.rows_by_model = rows_by_model

    def query(self, model):
        return _FakeQuery(self.rows_by_model.get(model, []))


def _make_db(rows_by_model):
    db = MagicMock()
    session = _FakeSession(rows_by_model)
    db.get_session.return_value.__enter__.return_value = session
    db.get_session.return_value.__exit__.return_value = False
    db.list_projects.return_value = [
        {"id": 10, "name": "Project Ten", "user_id": "user-1"},
        {"id": 11, "name": "Other Project", "user_id": "user-1"},
    ]
    return db


def _row(**values):
    defaults = {
        "deleted_at": None,
        "created_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "user_id": "user-1",
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def _client(monkeypatch, db, scope=None) -> TestClient:
    scope = scope or RequestUserScope(
        user_id="user-1",
        account_id="user-1",
        multi_user_enabled=False,
    )
    monkeypatch.setattr(media_routes, "_get_db", lambda: db)
    monkeypatch.setattr(media_routes, "_signed_src_url", lambda value: value or "")
    app = FastAPI()
    app.dependency_overrides[media_routes.get_request_user_scope] = lambda: scope
    app.include_router(media_routes.router, prefix="/api/media")
    return TestClient(app)


def test_project_artifacts_aggregate_direct_and_thread_linked_documents(monkeypatch):
    project_upload = _row(
        id="upload-project",
        project_id=10,
        thread_id=None,
        filename="project-notes.txt",
        src_url="/media/documents/project-notes.txt",
        filesize=12,
        mime_type="text/plain",
        source_tag="uploaded",
        embedding_status="ready",
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
    )
    thread_upload = _row(
        id="upload-thread",
        project_id=10,
        thread_id=101,
        filename="thread-upload.pdf",
        src_url="/media/documents/thread-upload.pdf",
        filesize=24,
        mime_type="application/pdf",
        source_tag="uploaded",
        embedding_status="pending",
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
    )
    linked_upload = _row(
        id="upload-linked",
        project_id=None,
        thread_id=None,
        filename="linked-upload.md",
        src_url="/media/documents/linked-upload.md",
        filesize=18,
        mime_type="text/markdown",
        source_tag="uploaded",
        embedding_status="ready",
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
    )
    generated = _row(
        id="generated-102",
        project_id=10,
        thread_id=102,
        title="Generated Brief",
        content="Generated brief body",
        format="md",
        model="test-model",
    )
    unrelated = _row(
        id="other-project",
        project_id=11,
        thread_id=None,
        filename="other.txt",
        src_url="/media/documents/other.txt",
        filesize=3,
        mime_type="text/plain",
        source_tag="uploaded",
        embedding_status="ready",
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
    )
    threads = [
        _row(id=101, project_id=10, title="First Thread"),
        _row(id=102, project_id=10, title="Second Thread"),
        _row(id=201, project_id=11, title="Other Thread"),
    ]
    thread_links = [
        _row(
            id=1,
            thread_id=101,
            document_id="upload-thread",
            relation="attached",
        ),
        _row(
            id=2,
            thread_id=102,
            document_id="generated-102",
            relation="attached",
        ),
        _row(
            id=3,
            thread_id=102,
            document_id="upload-linked",
            relation="reference",
        ),
    ]
    project_links = [
        _row(
            id=1,
            project_id=10,
            document_id="generated-102",
            document_type="generated",
            is_enabled=True,
        ),
        _row(
            id=2,
            project_id=10,
            document_id="upload-linked",
            document_type="uploaded",
            is_enabled=True,
        ),
    ]
    db = _make_db(
        {
            media_routes.ChatThread: threads,
            media_routes.ThreadDocument: thread_links,
            media_routes.ProjectDocumentLink: project_links,
            media_routes.GeneratedDocument: [generated],
            media_routes.UploadedDocument: [
                project_upload,
                thread_upload,
                linked_upload,
                unrelated,
            ],
        }
    )

    with _client(monkeypatch, db) as client:
        response = client.get(
            "/api/media/document-artifacts", params={"project_id": 10}
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert {item["id"] for item in payload["documents"]} == {
        "upload-project",
        "upload-thread",
        "upload-linked",
        "generated-102",
    }
    generated_payload = next(
        item for item in payload["documents"] if item["id"] == "generated-102"
    )
    assert generated_payload["artifact_type"] == "generated"
    assert generated_payload["project_id"] == 10
    assert generated_payload["thread_ids"] == [102]
    assert generated_payload["thread_title"] == "Second Thread"
    assert "other-project" not in {item["id"] for item in payload["documents"]}


def test_thread_artifacts_use_exact_thread_links_and_generated_detail(monkeypatch):
    generated = _row(
        id="generated-102",
        project_id=10,
        thread_id=102,
        title="Generated Brief",
        content="Generated brief body",
        format="md",
        model="test-model",
    )
    other_upload = _row(
        id="upload-101",
        project_id=10,
        thread_id=101,
        filename="other-thread.txt",
        src_url="/media/documents/other-thread.txt",
        filesize=4,
        mime_type="text/plain",
        source_tag="uploaded",
        embedding_status="ready",
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
    )
    linked_upload = _row(
        id="upload-linked",
        project_id=None,
        thread_id=None,
        filename="linked.md",
        src_url="/media/documents/linked.md",
        filesize=8,
        mime_type="text/markdown",
        source_tag="uploaded",
        embedding_status="ready",
        embedding_error=None,
        embedding_started_at=None,
        embedding_completed_at=None,
    )
    threads = [
        _row(id=102, project_id=10, title="Second Thread"),
        _row(id=101, project_id=10, title="First Thread"),
    ]
    links = [
        _row(
            id=1,
            thread_id=102,
            document_id="generated-102",
            relation="attached",
        ),
        _row(
            id=2,
            thread_id=102,
            document_id="upload-linked",
            relation="reference",
        ),
    ]
    db = _make_db(
        {
            media_routes.ChatThread: threads,
            media_routes.ThreadDocument: links,
            media_routes.GeneratedDocument: [generated],
            media_routes.UploadedDocument: [other_upload, linked_upload],
            media_routes.ProjectDocumentLink: [],
        }
    )

    with _client(monkeypatch, db) as client:
        list_response = client.get(
            "/api/media/document-artifacts", params={"thread_id": 102}
        )
        detail_response = client.get(
            "/api/media/document-artifacts/generated-102",
            params={"artifact_type": "generated"},
        )

    assert list_response.status_code == 200, list_response.text
    listed = list_response.json()["documents"]
    assert {item["id"] for item in listed} == {
        "generated-102",
        "upload-linked",
    }
    assert all(item["thread_id"] == 102 for item in listed)
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["artifact_type"] == "generated"
    assert detail["content"] == "Generated brief body"
    assert detail["format"] == "md"


def test_multi_user_project_artifacts_remain_account_scoped(monkeypatch):
    owned = _row(
        id="owned-upload",
        project_id=10,
        thread_id=None,
        filename="owned.txt",
        src_url="/media/documents/owned.txt",
        filesize=5,
        mime_type="text/plain",
        source_tag="uploaded",
        embedding_status="ready",
    )
    foreign = _row(
        id="foreign-upload",
        project_id=10,
        thread_id=None,
        filename="foreign.txt",
        src_url="/media/documents/foreign.txt",
        filesize=6,
        mime_type="text/plain",
        source_tag="uploaded",
        embedding_status="ready",
        user_id="user-2",
    )
    db = _make_db(
        {
            media_routes.ChatThread: [],
            media_routes.ProjectDocumentLink: [],
            media_routes.GeneratedDocument: [],
            media_routes.UploadedDocument: [owned, foreign],
        }
    )
    scope = RequestUserScope(
        user_id="user-1",
        account_id="user-1",
        multi_user_enabled=True,
    )

    with _client(monkeypatch, db, scope=scope) as client:
        response = client.get(
            "/api/media/document-artifacts", params={"project_id": 10}
        )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["documents"]] == ["owned-upload"]
