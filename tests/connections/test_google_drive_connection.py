"""Focused proof for the canonical Google Drive / Docs Knowledge connection."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.command_bus import invoke as command_invoke
from guardian.connections.google_drive import oauth
from guardian.connections.google_drive import router as google_drive_routes
from guardian.connections.google_drive import service as google_drive_service
from guardian.connections.google_drive.service import GoogleDriveTransportError
from guardian.db import models as db_models
from guardian.routes import command_bus, connections

_API_KEY = "google-drive-test-key"


class _TestDB:
    def __init__(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db_models.Base.metadata.create_all(
            self.engine,
            tables=[
                db_models.OAuthConnection.__table__,
                db_models.NotionConnectionCredential.__table__,
            ],
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

    @staticmethod
    def _to_dict(row: db_models.OAuthConnection) -> dict[str, Any]:
        return {
            "user_id": row.user_id,
            "provider": row.provider,
            "mode": row.mode,
            "scopes": list(row.scopes or []),
            "status": row.status,
            "encrypted_access_token": row.encrypted_access_token,
            "encrypted_refresh_token": row.encrypted_refresh_token,
            "relay_grant_id": row.relay_grant_id,
            "expires_at": row.expires_at,
            "last_refresh_at": row.last_refresh_at,
            "last_error": row.last_error,
        }

    def get_oauth_connection(
        self, *, user_id: str, provider: str, mode: str | None = None
    ) -> dict[str, Any] | None:
        with self.get_session() as session:
            query = session.query(db_models.OAuthConnection).filter_by(
                user_id=user_id, provider=provider
            )
            if mode:
                query = query.filter_by(mode=mode)
            row = query.order_by(db_models.OAuthConnection.id.desc()).first()
            return self._to_dict(row) if row is not None else None

    def upsert_oauth_connection(self, **kwargs: Any) -> dict[str, Any]:
        with self.get_session() as session:
            row = (
                session.query(db_models.OAuthConnection)
                .filter_by(
                    user_id=kwargs["user_id"],
                    provider=kwargs["provider"],
                    mode=kwargs["mode"],
                )
                .one_or_none()
            )
            if row is None:
                row = db_models.OAuthConnection(
                    id=(session.query(db_models.OAuthConnection).count() + 1),
                    user_id=kwargs["user_id"],
                    provider=kwargs["provider"],
                    mode=kwargs["mode"],
                )
                session.add(row)
            row.scopes = list(kwargs.get("scopes") or [])
            row.status = kwargs["status"]
            row.encrypted_access_token = kwargs.get("encrypted_access_token")
            row.encrypted_refresh_token = kwargs.get("encrypted_refresh_token")
            row.relay_grant_id = kwargs.get("relay_grant_id")
            row.expires_at = kwargs.get("expires_at")
            if kwargs.get("last_refresh_at") is not None:
                row.last_refresh_at = kwargs["last_refresh_at"]
            row.last_error = kwargs.get("last_error")
            session.commit()
            session.refresh(row)
            return self._to_dict(row)

    def disconnect_oauth_connection(
        self, *, user_id: str, provider: str, mode: str | None = None
    ) -> int:
        with self.get_session() as session:
            query = session.query(db_models.OAuthConnection).filter_by(
                user_id=user_id, provider=provider
            )
            if mode:
                query = query.filter_by(mode=mode)
            rows = query.all()
            for row in rows:
                row.status = "disconnected"
                row.encrypted_access_token = None
                row.encrypted_refresh_token = None
                row.relay_grant_id = None
                row.expires_at = None
                row.last_error = None
            session.commit()
            return len(rows)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _TestDB]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setenv("LOCAL_DEV", "true")
    monkeypatch.setenv("GOOGLE_DRIVE_OAUTH_CLIENT_ID", "google-drive-client")
    monkeypatch.setenv("GOOGLE_DRIVE_OAUTH_CLIENT_SECRET", "google-drive-secret")
    monkeypatch.setenv(
        "GOOGLE_DRIVE_OAUTH_REDIRECT_URI",
        "http://testserver/api/connect/google-drive/callback",
    )
    db = _TestDB()
    google_drive_routes.configure_db(db)
    connections.configure_db(db)
    app = FastAPI()
    app.include_router(connections.router)
    app.include_router(google_drive_routes.setup_router)
    app.include_router(google_drive_routes.operations_router)
    return TestClient(app), db


def _headers(user_id: str = "user-a") -> dict[str, str]:
    return {"X-API-Key": _API_KEY, "X-User-Id": user_id}


def _connected(db: _TestDB, user_id: str = "user-a") -> None:
    db.upsert_oauth_connection(
        user_id=user_id,
        provider="google_drive",
        mode="node_local",
        scopes=list(oauth.GOOGLE_DRIVE_OAUTH_SCOPES),
        status="connected",
        encrypted_access_token=oauth.encrypt_token("server-access-token"),
        encrypted_refresh_token=oauth.encrypt_token("server-refresh-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def test_catalog_identity_scopes_and_safe_projection(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get("/api/connections/google_drive", headers=_headers())
    assert response.status_code == 200
    item = response.json()
    assert item["id"] == "google_drive"
    assert item["display_name"] == "Google Drive / Docs"
    assert item["category"] == "knowledge"
    assert item["capabilities"] == ["content_read", "content_search"]
    assert item["auth_methods"] == ["oauth_browser"]
    assert item["oauth"]["launchable"] is True
    assert item["oauth_provider_key"] == "google_drive"
    assert item["scopes"] == list(oauth.GOOGLE_DRIVE_OAUTH_SCOPES)
    assert "client_secret" not in response.text
    assert "google-drive-secret" not in response.text


def test_start_callback_state_encryption_and_legacy_google_retirement(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    db.upsert_oauth_connection(
        user_id="user-a",
        provider="google",
        mode="node_local",
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
        status="connected",
        encrypted_access_token=oauth.encrypt_token("legacy-access"),
        encrypted_refresh_token=oauth.encrypt_token("legacy-refresh"),
    )
    started = test_client.post("/api/connect/google-drive/start", headers=_headers())
    assert started.status_code == 200, started.text
    payload = started.json()
    parsed = parse_qs(urlparse(payload["authorization_url"]).query)
    assert parsed["scope"] == [" ".join(oauth.GOOGLE_DRIVE_OAUTH_SCOPES)]
    assert parsed["code_challenge_method"] == ["S256"]
    assert "code_verifier" not in payload["authorization_url"]
    assert db.get_oauth_connection(
        user_id="user-a", provider="google_drive", mode="node_local"
    )["status"] == "pending"

    monkeypatch.setattr(
        oauth,
        "_token_response",
        lambda _data: {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600,
        },
    )
    monkeypatch.setattr(
        google_drive_service.GoogleDriveClient, "validate", lambda _self: None
    )
    callback = test_client.get(
        "/api/connect/google-drive/callback",
        params={"state": parsed["state"][0], "code": "provider-code"},
    )
    assert callback.status_code == 200, callback.text
    row = db.get_oauth_connection(
        user_id="user-a", provider="google_drive", mode="node_local"
    )
    assert row is not None
    assert row["status"] == "connected"
    assert row["encrypted_access_token"] != "google-access-token"
    assert oauth.decrypt_token(row["encrypted_access_token"]) == "google-access-token"
    legacy = db.get_oauth_connection(user_id="user-a", provider="google", mode="node_local")
    assert legacy is not None
    assert legacy["status"] == "disconnected"
    assert legacy["encrypted_access_token"] is None
    assert "google-access-token" not in callback.text
    assert "google-refresh-token" not in callback.text


def test_callback_token_failure_records_a_safe_error(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    started = test_client.post("/api/connect/google-drive/start", headers=_headers())
    state = parse_qs(urlparse(started.json()["authorization_url"]).query)["state"][0]

    def rejected(_data: dict[str, str]) -> dict[str, Any]:
        raise oauth.GoogleDriveOAuthAuthorizationError("raw provider detail")

    monkeypatch.setattr(oauth, "_token_response", rejected)
    callback = test_client.get(
        "/api/connect/google-drive/callback", params={"state": state, "code": "bad-code"}
    )
    assert callback.status_code == 401
    assert "raw provider detail" not in callback.text
    row = db.get_oauth_connection(
        user_id="user-a", provider="google_drive", mode="node_local"
    )
    assert row is not None
    assert row["status"] == "error"
    assert row["last_error"] == "google_drive_authorization_failed"


def test_invalid_state_refresh_and_user_isolation(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    assert test_client.get(
        "/api/connect/google-drive/callback", params={"state": "invalid", "code": "x"}
    ).status_code == 400

    _connected(db, "user-a")
    db.upsert_oauth_connection(
        user_id="user-a",
        provider="google_drive",
        mode="node_local",
        scopes=list(oauth.GOOGLE_DRIVE_OAUTH_SCOPES),
        status="connected",
        encrypted_access_token=oauth.encrypt_token("expired-access"),
        encrypted_refresh_token=oauth.encrypt_token("refresh-for-user-a"),
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    captured: list[dict[str, str]] = []

    def refresh(data: dict[str, str]) -> dict[str, Any]:
        captured.append(data)
        return {"access_token": "refreshed-access", "expires_in": 3600}

    monkeypatch.setattr(oauth, "_token_response", refresh)
    assert oauth.access_token_for_user(db, "user-a") == "refreshed-access"
    assert captured[0]["grant_type"] == "refresh_token"
    response = test_client.get(
        "/api/knowledge/google-drive/search?query=private", headers=_headers("user-b")
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"] == "google_drive_authorization_failed"


def test_search_normalizes_docs_pagination_provenance_and_no_persistence(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    _connected(db)
    captured: list[dict[str, Any]] = []

    def fake_request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        captured.append({"method": method, "url": url, **kwargs})
        return {
            "nextPageToken": "next-page",
            "incompleteSearch": False,
            "files": [
                {
                    "id": "doc_123",
                    "name": "Roadmap",
                    "mimeType": google_drive_service.GOOGLE_DOCUMENT_MIME_TYPE,
                    "parents": ["folder_123"],
                    "webViewLink": "https://docs.google.com/document/d/doc_123/edit",
                    "createdTime": "2026-08-20T00:00:00Z",
                    "modifiedTime": "2026-08-21T00:00:00Z",
                    "description": "Roadmap preview",
                    "driveId": "shared-drive-1",
                    "owners": [{"displayName": "Owner Name", "emailAddress": "private@example.com"}],
                },
                {"id": "sheet_1", "mimeType": "application/vnd.google-apps.spreadsheet"},
            ],
        }

    monkeypatch.setattr(google_drive_service.GoogleDriveClient, "_request_json", fake_request)
    response = test_client.get(
        "/api/knowledge/google-drive/search?query=roadmap&cursor=first-page&limit=2",
        headers=_headers(),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["capability"] == "content_search"
    assert payload["next_cursor"] == "next-page"
    assert payload["shared_drive_flags"] == {
        "supports_all_drives": True,
        "include_items_from_all_drives": True,
    }
    assert len(payload["results"]) == 1
    result = payload["results"][0]
    assert result["provider"] == result["source_system"] == "google_drive"
    assert result["external_object_id"] == "doc_123"
    assert result["object_type"] == "google_document"
    assert result["readable"] is True
    assert result["owner_display_names"] == ["Owner Name"]
    assert "private@example.com" not in response.text
    assert captured[0]["method"] == "GET"
    assert captured[0]["params"]["pageToken"] == "first-page"
    assert "mimeType" in captured[0]["params"]["q"]
    assert db.get_oauth_connection(
        user_id="user-a", provider="google_drive", mode="node_local"
    )["status"] == "connected"


def test_read_normalizes_docs_and_rejects_unsupported_types(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    _connected(db)

    def fake_request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        if "/drive/v3/files/" in url:
            return {
                "id": "doc_123",
                "name": "Design",
                "mimeType": google_drive_service.GOOGLE_DOCUMENT_MIME_TYPE,
                "parents": ["folder_123"],
            }
        return {
            "title": "Design",
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "paragraphStyle": {"namedStyleType": "HEADING_1"},
                            "elements": [{"textRun": {"content": "Plan\n"}}],
                        }
                    },
                    {
                        "paragraph": {
                            "bullet": {},
                            "elements": [{"textRun": {"content": "Ship\n"}}],
                        }
                    },
                    {
                        "table": {
                            "tableRows": [
                                {
                                    "tableCells": [
                                        {"content": [{"paragraph": {"elements": [{"textRun": {"content": "A\n"}}]}}]},
                                        {"content": [{"paragraph": {"elements": [{"textRun": {"content": "B\n"}}]}}]},
                                    ]
                                }
                            ]
                        }
                    },
                ]
            },
        }

    monkeypatch.setattr(google_drive_service.GoogleDriveClient, "_request_json", fake_request)
    response = test_client.get(
        "/api/knowledge/google-drive/read/doc_123", headers=_headers()
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["capability"] == "content_read"
    assert payload["content"] == "# Plan\n- Ship\nA | B"
    assert payload["object"]["mime_type"] == google_drive_service.GOOGLE_DOCUMENT_MIME_TYPE
    assert payload["object"]["source_system"] == "google_drive"
    assert payload["structure"]["document_tabs"] == "default_tab_only"

    monkeypatch.setattr(
        google_drive_service.GoogleDriveClient,
        "_file_metadata",
        lambda _self, _object_id: {"id": "sheet_1", "mimeType": "application/vnd.google-apps.spreadsheet"},
    )
    response = test_client.get(
        "/api/knowledge/google-drive/read/sheet_1", headers=_headers()
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "google_drive_unsupported_object_type"


def test_transport_error_is_sanitized_disconnects_safely_and_operations_are_read_only(
    client: tuple[TestClient, _TestDB], monkeypatch: pytest.MonkeyPatch
) -> None:
    test_client, db = client
    _connected(db)

    def unavailable(self, **kwargs: Any) -> dict[str, Any]:
        raise GoogleDriveTransportError("raw upstream timeout must not leak")

    monkeypatch.setattr(google_drive_service.GoogleDriveClient, "search", unavailable)
    response = test_client.get(
        "/api/knowledge/google-drive/search?query=roadmap", headers=_headers()
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "google_drive_transport_error"
    assert "raw upstream" not in response.text
    projected = test_client.get("/api/connections/google_drive", headers=_headers()).json()
    assert projected["oauth"]["connection"]["error_kind"] == "google_drive_transport_error"

    disconnected = test_client.post(
        "/api/connect/google-drive/disconnect", headers=_headers()
    )
    assert disconnected.status_code == 200
    assert disconnected.json()["removed"] is True
    row = db.get_oauth_connection(user_id="user-a", provider="google_drive", mode="node_local")
    assert row is not None and row["encrypted_access_token"] is None
    assert {
        (route.path, tuple(sorted(route.methods or ())))
        for route in google_drive_routes.operations_router.routes
    } == {
        ("/api/knowledge/google-drive/search", ("GET",)),
        ("/api/knowledge/google-drive/read/{object_id}", ("GET",)),
    }


def test_command_bus_registers_bounded_google_read_commands_and_keeps_actor_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("GUARDIAN_COMMAND_BUS_LOOPBACK_BASE", "http://127.0.0.1:9999")
    # CommandRun uses PostgreSQL JSONB and cannot be created in this focused
    # SQLite fixture. The CommandBusStore's canonical in-memory test seam
    # still records the completed run and ordered evidence below.
    command_bus.configure_db(None)
    app = FastAPI()
    app.include_router(google_drive_routes.operations_router)
    app.include_router(command_bus.router)

    def current_user(request: Request) -> str:
        return request.headers.get("X-User-Id", "operator")

    app.dependency_overrides[command_bus.get_current_user] = current_user
    test_client = TestClient(app)
    manifest = test_client.get(
        "/api/guardian/commands/manifest", headers=_headers("operator")
    ).json()
    commands = {(item["method"], item["path_template"]): item for item in manifest["commands"]}
    search = commands[("GET", "/api/knowledge/google-drive/search")]
    read = commands[("GET", "/api/knowledge/google-drive/read/{object_id}")]
    assert search["command_id"] == "op::google_drive_content_search"
    assert read["command_id"] == "op::google_drive_content_read"
    assert search["effect"] == read["effect"] == "read"
    assert search["approval_mode"] == read["approval_mode"] == "none"

    captured: list[dict[str, Any]] = []

    async def fake_loopback(**kwargs: Any) -> dict[str, Any]:
        captured.append(kwargs)
        return {"status_code": 200, "body": {"connection_id": "google_drive"}}

    monkeypatch.setattr(command_invoke, "execute_loopback_request", fake_loopback)
    response = test_client.post(
        "/api/guardian/commands/invoke",
        headers=_headers("operator"),
        json={
            "invoke_version": "1.0",
            "command_id": search["command_id"],
            "actor": {"kind": "agent", "id": "operator"},
            "arguments": {"query": {"query": "roadmap"}},
            "idempotency_key": "google-drive-search-proof",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured[0]["method"] == "GET"
    assert captured[0]["path_template"] == "/api/knowledge/google-drive/search"
    persisted_run = command_bus.get_store().get_run(response.json()["run_id"])
    assert persisted_run is not None
    assert persisted_run["command_id"] == "op::google_drive_content_search"
    assert persisted_run["auth_subject"] == "operator"
    assert persisted_run["status"] == "completed"
    assert command_bus.get_store().list_events_after(
        run_id=response.json()["run_id"], after_seq=0
    )
    assert test_client.post(
        "/api/guardian/commands/invoke",
        headers=_headers("operator"),
        json={
            "invoke_version": "1.0",
            "command_id": search["command_id"],
            "actor": {"kind": "agent", "id": "other-user"},
            "arguments": {"query": {"query": "roadmap"}},
        },
    ).status_code == 403


def test_canonical_google_drive_runtime_has_no_legacy_gsuite_or_connector_dependency() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("guardian/connections/google_drive").glob("*.py")
    )
    assert "guardian.connectors.gsuite" not in source
    assert "/api/connectors" not in source
    assert "prefect" not in source.lower()
