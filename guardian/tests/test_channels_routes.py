from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.db import models as db_models
from guardian.routes import channels

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
                db_models.ChannelAllowlist.__table__,
                db_models.ChannelPairing.__table__,
                db_models.ChannelMessage.__table__,
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

    def add_message(
        self,
        *,
        user_id: str,
        channel: str,
        direction: str,
        content: str,
        external_id: str | None = None,
        thread_id: str | None = None,
    ) -> int:
        with self.get_session() as session:
            row = db_models.ChannelMessage(
                user_id=user_id,
                channel=channel,
                direction=direction,
                content=content,
                external_id=external_id,
                thread_id=thread_id,
                meta_json={"seeded": True},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.id)


def _client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _TestDB]:
    monkeypatch.setenv("GUARDIAN_API_KEY", _API_KEY)
    monkeypatch.setenv("CODEXIFY_SINGLE_USER_ID", _SERVER_USER_ID)
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("LOCAL_DEV", "false")
    db = _TestDB()
    channels.configure_db(db)
    app = FastAPI()
    app.include_router(channels.router)
    return TestClient(app), db


def test_channels_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _client(monkeypatch)
    response = client.get("/api/channels/configs", headers={"X-API-Key": ""})
    assert response.status_code == 401


def test_config_create_and_user_scoped_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _client(monkeypatch)
    headers = {"X-API-Key": _API_KEY, "X-User-Id": "spoof-a"}

    create_response = client.post(
        "/api/channels/configs",
        headers=headers,
        json={
            "channel": "slack",
            "config_json": {"token_ref": "vault://slack/token"},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["user_id"] == _SERVER_USER_ID
    assert created["channel"] == "slack"
    assert created["config_json"]["token_ref"] == "vault://slack/token"

    list_response = client.get("/api/channels/configs", headers=headers)
    assert list_response.status_code == 200
    rows = list_response.json()["items"]
    assert len(rows) == 1
    assert rows[0]["user_id"] == _SERVER_USER_ID
    assert rows[0]["channel"] == "slack"

    other_user = client.get(
        "/api/channels/configs",
        headers={"X-API-Key": _API_KEY, "X-User-Id": "spoof-b"},
    )
    assert other_user.status_code == 200
    assert len(other_user.json()["items"]) == 1
    assert other_user.json()["items"][0]["user_id"] == _SERVER_USER_ID


def test_channel_message_persistence_and_scoping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, db = _client(monkeypatch)
    db.add_message(
        user_id=_SERVER_USER_ID,
        channel="telegram",
        direction="inbound",
        content="hello from channel",
        external_id="msg-1",
        thread_id="thread-123",
    )
    db.add_message(
        user_id="foreign_user",
        channel="telegram",
        direction="outbound",
        content="other user",
        external_id="msg-2",
        thread_id="thread-999",
    )

    response = client.get(
        "/api/channels/messages/telegram?limit=50",
        headers={"X-API-Key": _API_KEY, "X-User-Id": "spoof-a"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["content"] == "hello from channel"
    assert payload["items"][0]["external_id"] == "msg-1"
