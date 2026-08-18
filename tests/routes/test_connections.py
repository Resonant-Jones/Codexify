"""Connections read API projection tests.

Verifies the aggregation seam: catalog + per-user channel config +
safe oauth projection + provider-registry authorization truth, with no
credential material ever serialized.
"""

from __future__ import annotations

import datetime
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db import models as db_models
from guardian.routes import connections

_API_KEY = "test-api-key"
_SERVER_USER_ID = "local_user"


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
                db_models.ChannelConfig.__table__,
                db_models.OAuthConnection.__table__,
            ],
        )
        self._SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

    @contextmanager
    def get_session(self):
        session = self._SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def add_channel_config(
        self, *, user_id: str, channel: str, config_json: dict | None = None
    ) -> None:
        with self.get_session() as session:
            session.add(
                db_models.ChannelConfig(
                    user_id=user_id,
                    channel=channel,
                    config_json=config_json or {},
                )
            )
            session.commit()

    def add_oauth_connection(
        self,
        *,
        oauth_id: int,
        user_id: str,
        provider: str,
        mode: str = "node_local",
        status: str = "connected",
        scopes: list[str] | None = None,
        expires_at: datetime.datetime | None = None,
        last_error: str | None = None,
    ) -> None:
        with self.get_session() as session:
            session.add(
                db_models.OAuthConnection(
                    id=oauth_id,
                    user_id=user_id,
                    provider=provider,
                    mode=mode,
                    scopes=scopes or [],
                    status=status,
                    encrypted_access_token="SHOULD_NEVER_BE_SERIALIZED",
                    encrypted_refresh_token="SHOULD_NEVER_BE_SERIALIZED",
                    expires_at=expires_at,
                    last_error=last_error,
                )
            )
            session.commit()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _TestDB]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", _SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")
    db = _TestDB()
    connections.configure_db(db)
    app = FastAPI()
    app.include_router(connections.router)
    return TestClient(app), db


def _headers() -> dict[str, str]:
    return {"X-API-Key": _API_KEY, "X-User-Id": "spoof-a"}


def _items_by_id(payload: dict) -> dict[str, dict]:
    return {item["id"]: item for item in payload["items"]}


def test_connections_requires_api_key(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get(
        "/api/connections", headers={"X-API-Key": ""}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


def test_list_returns_all_three_categories(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get("/api/connections", headers=_headers())
    assert response.status_code == 200
    payload = response.json()
    assert payload["categories"] == ["inference", "messaging", "web"]
    items = _items_by_id(payload)
    assert {"slack", "discord", "telegram"} <= set(items)
    assert {"firecrawl", "searxng", "brave", "ddgs", "tavily", "exa",
            "parallel", "xai_grok"} <= set(items)
    assert {"deepseek", "openai_api", "openrouter", "minimax_api",
            "codex_chatgpt"} <= set(items)


def test_channel_config_presence_marks_entry_configured(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, db = client
    db.add_channel_config(user_id=_SERVER_USER_ID, channel="telegram")
    db.add_channel_config(user_id="foreign_user", channel="slack")

    response = test_client.get("/api/connections", headers=_headers())
    items = _items_by_id(response.json())

    assert items["telegram"]["setup_state"] == "configured"
    # foreign user's config must never leak into this user's projection
    assert items["slack"]["setup_state"] == "unavailable"
    assert items["discord"]["setup_state"] == "unavailable"


def test_unimplemented_entries_report_unavailable(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get("/api/connections", headers=_headers())
    items = _items_by_id(response.json())
    for entry_id in ("whatsapp", "firecrawl", "openrouter", "qwen_oauth"):
        assert items[entry_id]["implementation_state"] == "unimplemented"
        assert items[entry_id]["setup_state"] == "unavailable"


def test_oauth_rows_project_only_safe_fields(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, db = client
    expires = datetime.datetime(
        2026, 9, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
    )
    db.add_oauth_connection(
        oauth_id=1,
        user_id=_SERVER_USER_ID,
        provider="minimax_oauth",
        status="connected",
        scopes=["chat"],
        expires_at=expires,
    )

    response = test_client.get(
        "/api/connections/minimax_oauth", headers=_headers()
    )
    assert response.status_code == 200
    item = response.json()
    # No Codexify OAuth flow exists for this entry, so setup stays
    # unavailable even though a safe oauth_connections row is projected.
    assert item["setup_state"] == "unavailable"
    oauth = item["oauth"]
    assert oauth["backend_handler_exists"] is False
    assert oauth["supported"] is False
    connection_row = oauth["connection"]
    assert connection_row["provider"] == "minimax_oauth"
    assert connection_row["status"] == "connected"
    assert connection_row["scopes"] == ["chat"]
    # SQLite stores timezone-aware timestamps without offset; compare
    # parsed instants rather than string forms.
    assert datetime.datetime.fromisoformat(
        connection_row["expires_at"]
    ) == expires.replace(tzinfo=None)
    assert connection_row["error_kind"] is None
    for key in ("encrypted_access_token", "encrypted_refresh_token",
                "access_token", "refresh_token", "relay_grant_id"):
        assert key not in connection_row


def test_oauth_error_is_sanitized_classification_only(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, db = client
    db.add_oauth_connection(
        oauth_id=1,
        user_id=_SERVER_USER_ID,
        provider="minimax_oauth",
        status="error",
        last_error="refresh_token exchange failed: invalid_grant <raw text>",
    )
    response = test_client.get(
        "/api/connections/minimax_oauth", headers=_headers()
    )
    item = response.json()
    assert item["setup_state"] == "unavailable"
    connection_row = item["oauth"]["connection"]
    assert connection_row["error_kind"] == "provider_error"
    # Raw error text must never be serialized.
    body_text = response.text.lower()
    assert "invalid_grant" not in body_text
    assert "refresh_token exchange failed" not in body_text
    assert "should_never_be_serialized" not in body_text


def test_no_secret_material_in_full_listing(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, db = client
    db.add_oauth_connection(
        oauth_id=1,
        user_id=_SERVER_USER_ID,
        provider="minimax_oauth",
        status="connected",
    )
    response = test_client.get("/api/connections", headers=_headers())
    assert response.status_code == 200
    body = response.text
    assert "encrypted_access_token" not in body
    assert "encrypted_refresh_token" not in body
    assert "SHOULD_NEVER_BE_SERIALIZED" not in body


def test_inference_entries_project_registry_authorization(
    client: tuple[TestClient, _TestDB],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client
    # This assertion exercises cloud-provider registry projection in
    # isolation; the supported local profile contract is covered separately.
    monkeypatch.setenv("CODEXIFY_SUPPORTED_PROFILE", "")
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "true")
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "false")
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-deepseek")

    response = test_client.get(
        "/api/connections/deepseek", headers=_headers()
    )
    item = response.json()
    authorization = item["authorization"]
    assert authorization["registered"] is True
    assert authorization["registry_provider_id"] == "deepseek"
    assert authorization["authorized"] is True
    assert authorization["available"] is True
    assert item["setup_state"] == "configured"
    # api-key only; never OAuth.
    assert item["auth_methods"] == ["api_key"]
    assert item["oauth"] is None


def test_inference_without_credentials_reports_needs_setup(
    client: tuple[TestClient, _TestDB],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, _ = client
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "true")
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "false")
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    response = test_client.get(
        "/api/connections/deepseek", headers=_headers()
    )
    item = response.json()
    authorization = item["authorization"]
    assert authorization["authorized"] is False
    assert item["setup_state"] == "needs_setup"


def test_unlisted_inference_entry_is_not_registry_authorized(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get(
        "/api/connections/openrouter", headers=_headers()
    )
    item = response.json()
    assert item["authorization"]["registered"] is False
    assert item["setup_state"] == "unavailable"


def test_unknown_connection_id_returns_404(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get(
        "/api/connections/does_not_exist", headers=_headers()
    )
    assert response.status_code == 404


def test_runtime_binding_reports_real_adapters_only(
    client: tuple[TestClient, _TestDB],
) -> None:
    test_client, _ = client
    response = test_client.get("/api/connections", headers=_headers())
    items = _items_by_id(response.json())
    assert (
        items["slack"]["runtime_binding"]["adapter"]
        == "guardian.channels.adapters.slack.SlackAdapter"
    )
    assert items["whatsapp"]["runtime_binding"]["adapter"] is None
    assert items["firecrawl"]["runtime_binding"]["adapter"] is None
    assert items["deepseek"]["runtime_binding"]["registry_provider_id"] == (
        "deepseek"
    )


def test_connections_router_is_read_only(
    client: tuple[TestClient, _TestDB],
) -> None:
    paths = {
        route.path: set(route.methods or ())
        for route in connections.router.routes
    }

    assert paths == {
        "/api/connections": {"GET"},
        "/api/connections/{connection_id}": {"GET"},
    }
