"""Focused proof for the canonical, read-only Notion Knowledge connection."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.command_bus import invoke as command_invoke
from guardian.connections.notion import router as notion_routes
from guardian.connections.notion import service as notion_service
from guardian.connections.notion.service import (
    NotionAuthorizationError,
    NotionTransportError,
)
from guardian.db import models as db_models
from guardian.routes import command_bus, connections

_API_KEY = "notion-test-key"


class _TestDB:
    def __init__(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db_models.Base.metadata.create_all(
            self.engine,
            tables=[db_models.NotionConnectionCredential.__table__],
        )
        self._SessionLocal = sessionmaker(
            bind=self.engine, autocommit=False, autoflush=False
        )

    @contextmanager
    def get_session(self):
        session = self._SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def credential_for(self, user_id: str):
        with self.get_session() as session:
            return (
                session.query(db_models.NotionConnectionCredential)
                .filter_by(user_id=user_id)
                .one_or_none()
            )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _TestDB]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("LOCAL_DEV", "true")
    db = _TestDB()
    notion_routes.configure_db(db)
    connections.configure_db(db)
    app = FastAPI()
    app.include_router(connections.router)
    app.include_router(notion_routes.setup_router)
    app.include_router(notion_routes.operations_router)
    return TestClient(app), db


def _headers(user_id: str = "user-a") -> dict[str, str]:
    return {"X-API-Key": _API_KEY, "X-User-Id": user_id}


def _configure(client: TestClient, token: str = "notion-secret-token") -> None:
    response = client.post(
        "/api/connect/notion/configure",
        headers=_headers(),
        json={"settings": {"integration_token": token}},
    )
    assert response.status_code == 200, response.text


def test_configure_is_user_scoped_encrypted_and_connections_are_secret_free(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, db = client
    _configure(test_client)

    record = db.credential_for("user-a")
    assert record is not None
    assert record.encrypted_integration_token != "notion-secret-token"
    assert record.validation_status == "unvalidated"
    assert db.credential_for("user-b") is None

    listing = test_client.get("/api/connections/notion", headers=_headers())
    assert listing.status_code == 200
    item = listing.json()
    assert item["category"] == "knowledge"
    assert item["capabilities"] == ["content_read", "content_search"]
    assert item["setup_state"] == "configured"
    assert item["validation"] == {
        "configured": True,
        "state": "unvalidated",
        "last_validated_at": None,
    }
    for forbidden in (
        "notion-secret-token",
        "encrypted_integration_token",
    ):
        assert forbidden not in listing.text.lower()


def test_validation_distinguishes_success_authorization_and_transport_failures(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    _configure(test_client)

    def valid_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        assert method == "POST"
        assert path == "/search"
        return {"results": [], "has_more": False}

    monkeypatch.setattr(notion_service.NotionClient, "_request_json", valid_request)
    response = test_client.post("/api/connect/notion/validate", headers=_headers())
    assert response.status_code == 200
    assert response.json()["validation"]["state"] == "valid"
    assert db.credential_for("user-a").validation_status == "valid"

    def denied(self) -> None:
        raise NotionAuthorizationError("raw upstream response must not leak")

    monkeypatch.setattr(notion_service.NotionClient, "validate", denied)
    response = test_client.post("/api/connect/notion/validate", headers=_headers())
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "notion_authorization_failed"
    assert "raw upstream" not in response.text
    assert db.credential_for("user-a").validation_status == "authorization_error"

    def unavailable(self) -> None:
        raise NotionTransportError("raw timeout must not leak")

    monkeypatch.setattr(notion_service.NotionClient, "validate", unavailable)
    response = test_client.post("/api/connect/notion/validate", headers=_headers())
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "notion_transport_error"
    assert db.credential_for("user-a").validation_status == "transport_error"


def test_search_normalizes_pages_paginates_and_does_not_persist_content(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    _configure(test_client)
    captured: list[dict[str, Any]] = []

    def fake_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        captured.append({"method": method, "path": path, **kwargs})
        return {
            "has_more": True,
            "next_cursor": "cursor-next",
            "results": [
                {
                    "object": "page",
                    "id": "11111111-1111-1111-1111-111111111111",
                    "url": "https://www.notion.so/roadmap",
                    "created_time": "2026-08-20T00:00:00.000Z",
                    "last_edited_time": "2026-08-21T00:00:00.000Z",
                    "parent": {"type": "page_id", "page_id": "parent-page"},
                    "properties": {
                        "Name": {
                            "type": "title",
                            "title": [{"plain_text": "Roadmap"}],
                        }
                    },
                }
            ],
        }

    monkeypatch.setattr(notion_service.NotionClient, "_request_json", fake_request)
    response = test_client.get(
        "/api/knowledge/notion/search?query=roadmap&cursor=cursor-first&limit=2",
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["capability"] == "content_search"
    assert payload["next_cursor"] == "cursor-next"
    result = payload["results"][0]
    assert result["provider"] == "notion"
    assert result["source_system"] == "notion"
    assert result["external_object_id"] == "11111111-1111-1111-1111-111111111111"
    assert result["object_type"] == "page"
    assert result["title"] == "Roadmap"
    assert result["external_url"] == "https://www.notion.so/roadmap"
    assert result["retrieved_at"]
    assert captured[0]["json"]["filter"] == {
        "property": "object",
        "value": "page",
    }
    assert captured[0]["json"]["start_cursor"] == "cursor-first"
    assert db.credential_for("user-a") is not None
    with db.get_session() as session:
        assert session.query(db_models.NotionConnectionCredential).count() == 1


def test_read_normalizes_page_content_and_block_pagination(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, _ = client
    _configure(test_client)
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def fake_request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((method, path, kwargs))
        if path.startswith("/pages/"):
            return {
                "object": "page",
                "id": "22222222-2222-2222-2222-222222222222",
                "url": "https://www.notion.so/readable",
                "properties": {
                    "Name": {
                        "type": "title",
                        "title": [{"plain_text": "Readable page"}],
                    }
                },
            }
        if kwargs.get("params", {}).get("start_cursor") == "second":
            return {
                "has_more": False,
                "results": [
                    {
                        "id": "block-two",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"plain_text": "second"}]},
                    }
                ],
            }
        return {
            "has_more": True,
            "next_cursor": "second",
            "results": [
                {
                    "id": "block-one",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"plain_text": "first"}]},
                }
            ],
        }

    monkeypatch.setattr(notion_service.NotionClient, "_request_json", fake_request)
    response = test_client.get(
        "/api/knowledge/notion/read/22222222-2222-2222-2222-222222222222",
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["capability"] == "content_read"
    assert payload["content"] == "first\nsecond"
    assert payload["block_count"] == 2
    assert payload["object"]["source_system"] == "notion"
    assert payload["object"]["external_object_id"] == "22222222-2222-2222-2222-222222222222"
    assert any(
        path.endswith("/children") and params.get("params", {}).get("start_cursor") == "second"
        for _, path, params in calls
    )


def test_unconfigured_and_other_user_credentials_fail_safely(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.post("/api/connect/notion/validate", headers=_headers())
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "notion_not_configured"

    _configure(test_client)
    response = test_client.get(
        "/api/knowledge/notion/search?query=private", headers=_headers("user-b")
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "notion_not_configured"


def test_disconnect_and_operation_surface_remain_bounded(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, db = client
    _configure(test_client)
    response = test_client.post("/api/connect/notion/disconnect", headers=_headers())
    assert response.status_code == 200
    assert response.json()["removed"] is True
    assert db.credential_for("user-a") is None

    assert {
        (route.path, tuple(sorted(route.methods or ())))
        for route in notion_routes.operations_router.routes
    } == {
        ("/api/knowledge/notion/search", ("GET",)),
        ("/api/knowledge/notion/read/{object_id}", ("GET",)),
    }
    assert test_client.get(
        "/api/knowledge/notion/read/not-an-id", headers=_headers()
    ).status_code == 422
    assert test_client.get(
        "/api/knowledge/notion/search?query=%20%20%20", headers=_headers()
    ).status_code == 422


def test_command_bus_registers_bounded_read_commands_and_keeps_actor_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv(
        "GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999"
    )
    command_bus.configure_db(None)
    app = FastAPI()
    app.include_router(notion_routes.operations_router)
    app.include_router(command_bus.router)

    def current_user(request: Request) -> str:
        return request.headers.get("X-User-Id", "operator")

    app.dependency_overrides[command_bus.get_current_user] = current_user
    client = TestClient(app)
    manifest = client.get(
        "/api/guardian/commands/manifest", headers=_headers("operator")
    ).json()
    commands = {
        (command["method"], command["path_template"]): command
        for command in manifest["commands"]
    }
    search = commands[("GET", "/api/knowledge/notion/search")]
    read = commands[("GET", "/api/knowledge/notion/read/{object_id}")]
    assert search["effect"] == read["effect"] == "read"
    assert search["risk"] == read["risk"] == "read_only"
    assert search["approval_mode"] == read["approval_mode"] == "none"

    captured: list[dict[str, Any]] = []

    async def fake_loopback(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs)
        return {"status_code": 200, "body": {"connection_id": "notion"}}

    monkeypatch.setattr(command_invoke, "execute_loopback_request", fake_loopback)
    response = client.post(
        "/api/guardian/commands/invoke",
        headers=_headers("operator"),
        json={
            "invoke_version": "1.0",
            "command_id": search["command_id"],
            "actor": {"kind": "agent", "id": "operator"},
            "arguments": {"query": {"query": "roadmap"}},
            "idempotency_key": "notion-search-proof",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured[0]["method"] == "GET"
    assert captured[0]["path_template"] == "/api/knowledge/notion/search"
    assert captured[0]["query"] == {"query": "roadmap"}

    rejected = client.post(
        "/api/guardian/commands/invoke",
        headers=_headers("operator"),
        json={
            "invoke_version": "1.0",
            "command_id": search["command_id"],
            "actor": {"kind": "agent", "id": "other-user"},
            "arguments": {"query": {"query": "roadmap"}},
        },
    )
    assert rejected.status_code == 403


def test_canonical_notion_runtime_has_no_legacy_connector_dependency() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("guardian/connections/notion").glob("*.py")
    )
    assert "guardian.connectors.notion" not in source
    assert "/api/connectors" not in source
