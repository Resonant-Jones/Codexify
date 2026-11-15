"""Synthetic account isolation through the mounted voice router and real ORM reads."""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from guardian.core import dependencies
from guardian.core.dependencies import RequestUserScope
from guardian.routes import voice
from guardian.voice import audio_assets


@pytest.fixture(params=["get_session", "_sa_session"])
def boundary(request, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, thread_id INTEGER, user_id TEXT, role TEXT, content TEXT, event_at TEXT, kind TEXT, extra_meta JSON, hosted_room_participant_id TEXT, sender_display_name_snapshot TEXT, created_at TEXT, updated_at TEXT)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE message_audio_assets (id INTEGER PRIMARY KEY, message_id INTEGER, provider TEXT, voice TEXT, text_hash TEXT, src_url TEXT, internal_format TEXT, delivery_variants_json JSON, duration_seconds FLOAT, filesize_bytes INTEGER, created_at TEXT)"
            )
        )
        for message_id, thread_id in [(11, 1), (22, 2), (33, 3), (44, 4)]:
            connection.execute(
                text(
                    "INSERT INTO chat_messages (id, thread_id, user_id, role, content, kind, extra_meta) VALUES (:id, :thread_id, 'author-is-not-owner', 'assistant', 'synthetic voice text', 'chat', '{}')"
                ),
                {"id": message_id, "thread_id": thread_id},
            )
        for asset_id, message_id in [
            (111, 11),
            (222, 22),
            (333, 33),
            (444, 44),
            (555, 999),
        ]:
            connection.execute(
                text(
                    "INSERT INTO message_audio_assets (id, message_id, provider, voice, text_hash, src_url, internal_format, delivery_variants_json, created_at) VALUES (:id, :message_id, 'local_openai_compatible', 'alloy', :text_hash, 'synthetic.wav', 'wav', '{}', '2026-11-15 00:00:00')"
                ),
                {
                    "id": asset_id,
                    "message_id": message_id,
                    "text_hash": audio_assets.compute_text_hash("synthetic voice text"),
                },
            )
    sessions = sessionmaker(bind=engine)
    threads = {
        1: {"id": 1, "user_id": "account-a"},
        2: {"id": 2, "user_id": "account-b"},
        3: {"id": 3, "user_id": None},
    }

    @contextmanager
    def session_context():
        with sessions() as session:
            yield session
            if request.param == "_sa_session":
                session.commit()

    db = SimpleNamespace(get_chat_thread=lambda thread_id: threads.get(thread_id))
    setattr(db, request.param, session_context)
    monkeypatch.setattr(dependencies, "chatlog_db", db)
    monkeypatch.setattr(voice, "load_guardian_db_from_env", lambda: db)
    monkeypatch.setattr(voice, "STREAM_PROXY_ENABLED", True)
    cfg = SimpleNamespace(
        turns_enabled=True,
        tts_provider="local_openai_compatible",
        internal_format="wav",
        tts_timeout_seconds=1,
        stt_timeout_seconds=1,
        completion_timeout_seconds=1,
        turn_dedupe_ttl_seconds=60,
    )
    monkeypatch.setattr(voice, "get_voice_runtime_config", lambda: cfg)
    monkeypatch.setattr(voice, "_voice_worker_available", lambda: True)
    scope = {
        "value": RequestUserScope(
            user_id="account-a", account_id="account-a", multi_user_enabled=True
        )
    }
    app = FastAPI()
    app.include_router(voice.router)
    app.dependency_overrides[voice.require_api_key] = (
        lambda: "synthetic-account-session"
    )
    app.dependency_overrides[dependencies.get_request_user_scope] = lambda: scope[
        "value"
    ]
    calls = {
        name: Mock(name=name)
        for name in (
            "synthesize",
            "save_message_audio_asset",
            "normalize_audio_input",
            "_get_dedupe_hit",
            "acquire_turn_lock",
            "enqueue",
        )
    }
    for name, call in calls.items():
        monkeypatch.setattr(voice, name, call)
    calls["synthesize"].return_value = (b"synthetic-audio", "wav")
    calls["save_message_audio_asset"].return_value = {"id": 999}
    calls["normalize_audio_input"].return_value = (b"synthetic-audio", "audio/wav", {})
    calls["_get_dedupe_hit"].return_value = {
        "task_id": "synthetic-task",
        "deduped": True,
    }
    download = Mock(return_value=b"synthetic-audio")
    monkeypatch.setattr(voice, "_storage", SimpleNamespace(download_file=download))
    sign = Mock(return_value="/media/synthetic.wav?sig=synthetic")
    monkeypatch.setattr(audio_assets, "sign_media_url", sign)
    yield SimpleNamespace(
        app=app,
        client=TestClient(app),
        calls=calls,
        download=download,
        sign=sign,
        scope=scope,
        threads=threads,
        db=db,
    )
    engine.dispose()


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize(
    "message_id,status", [(22, 403), (33, 403), (44, 404), (999, 404)]
)
def test_denied_speak_has_no_sensitive_effects(boundary, force, message_id, status):
    response = boundary.client.post(
        f"/api/voice/messages/{message_id}/speak", json={"force_regenerate": force}
    )
    assert response.status_code == status, response.text
    assert not boundary.sign.called
    assert not any(call.called for call in boundary.calls.values())


@pytest.mark.parametrize(
    "asset_id,status", [(222, 403), (333, 403), (444, 404), (555, 404), (999, 404)]
)
def test_denied_audio_has_no_download(boundary, asset_id, status):
    response = boundary.client.get(f"/api/voice/audio/{asset_id}")
    assert response.status_code == status, response.text
    boundary.download.assert_not_called()


@pytest.mark.parametrize("thread_id,status", [(2, 403), (3, 403), (4, 404)])
def test_denied_turn_precedes_audio_processing_and_queue(boundary, thread_id, status):
    response = boundary.client.post(
        "/api/voice/turn",
        data={"thread_id": thread_id},
        files={"audio_file": ("synthetic.wav", b"synthetic", "audio/wav")},
    )
    assert response.status_code == status, response.text
    assert not any(call.called for call in boundary.calls.values())


def test_owner_cached_speak_and_audio(boundary):
    response = boundary.client.post("/api/voice/messages/11/speak", json={})
    assert response.status_code == 200, response.text
    assert response.json()["cached"] is True
    assert response.json()["audio_asset"]["stream_url"] == "/api/voice/audio/111"
    assert "sig=synthetic" in response.json()["audio_asset"]["src_url"]
    response = boundary.client.get("/api/voice/audio/111")
    assert response.status_code == 200, response.text
    assert response.content == b"synthetic-audio"
    boundary.calls["synthesize"].assert_not_called()


def test_local_single_user_compatibility(boundary):
    boundary.scope["value"] = RequestUserScope(
        user_id="local", multi_user_enabled=False
    )
    assert (
        boundary.client.post("/api/voice/messages/22/speak", json={}).status_code == 200
    )
    assert boundary.client.get("/api/voice/audio/222").status_code == 200


@pytest.mark.parametrize("force", [False, True])
def test_owner_synthesis_on_cache_miss_or_regeneration(boundary, force):
    response = boundary.client.post(
        "/api/voice/messages/11/speak",
        json={"force_regenerate": force, "voice": "uncached-voice"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["cached"] is False
    boundary.calls["synthesize"].assert_called_once()
    boundary.calls["save_message_audio_asset"].assert_called_once()


def test_cross_account_uncached_speak_denied(boundary):
    response = boundary.client.post(
        "/api/voice/messages/22/speak", json={"voice": "uncached-voice"}
    )
    assert response.status_code == 403, response.text
    assert not any(call.called for call in boundary.calls.values())
    assert not boundary.sign.called


def test_owner_turn_binds_account_through_queue_round_trip(boundary, monkeypatch):
    from unittest.mock import AsyncMock

    from guardian.tasks.types import task_from_dict

    boundary.scope["value"] = RequestUserScope(
        user_id="old-subject", account_id="account-a", multi_user_enabled=True
    )
    boundary.calls["_get_dedupe_hit"].return_value = None
    boundary.calls["acquire_turn_lock"].return_value = True
    monkeypatch.setattr(voice, "_set_dedupe_record", Mock())
    monkeypatch.setattr(voice.task_events, "publish", Mock())
    monkeypatch.setattr(
        voice,
        "_await_terminal_task_event",
        AsyncMock(
            return_value=("task.completed", {"assistant_text": "synthetic answer"})
        ),
    )
    response = boundary.client.post(
        "/api/voice/turn",
        data={"thread_id": 1, "account_id": "account-b", "user_id": "account-b"},
        headers={"X-User-Id": "account-b"},
        files={"audio_file": ("synthetic.wav", b"synthetic", "audio/wav")},
    )
    assert response.status_code == 200, response.text
    task = boundary.calls["enqueue"].call_args.args[0]
    restored = task_from_dict(task.to_dict())
    assert restored.account_id == restored.user_id == "account-a"
    assert restored.thread_id == 1
    assert (
        boundary.calls["_get_dedupe_hit"].call_args.kwargs["account_id"] == "account-a"
    )


def test_dedupe_isolated_from_previous_owner_and_local_lane():
    args = (1, "same-turn", "same-audio")
    assert (
        len(
            {
                voice._dedupe_key(*args),
                voice._dedupe_key(*args, "account-a"),
                voice._dedupe_key(*args, "account-b"),
            }
        )
        == 3
    )


def test_disabled_stream_proxy_preserves_route_error(boundary, monkeypatch):
    monkeypatch.setattr(voice, "STREAM_PROXY_ENABLED", False)
    response = boundary.client.get("/api/voice/audio/111")
    assert response.status_code == 404
    assert response.json()["detail"] == "route_not_found"
    boundary.download.assert_not_called()


@pytest.mark.parametrize("account,status", [("account-a", 200), ("account-b", 403)])
def test_real_remote_account_session_and_scope(boundary, monkeypatch, account, status):
    from tests.identity.test_account_user_jwt_identity import (
        JWT_SECRET,
        _account_jwt,
        _SessionStore,
    )

    boundary.app.dependency_overrides.clear()
    monkeypatch.setenv("GUARDIAN_SESSION_SECRET", JWT_SECRET)
    monkeypatch.setenv("GUARDIAN_AUTH_MODE", "remote")
    monkeypatch.delenv("GUARDIAN_EXPOSURE_MODE", raising=False)
    store = _SessionStore()
    monkeypatch.setattr("guardian.core.session_store.get_session_store", lambda: store)
    monkeypatch.setattr(
        "guardian.core.auth_dependencies.get_session_store", lambda: store
    )
    headers = {
        "X-API-Key": "",
        "X-User-Id": "account-a",
        "Authorization": f"Bearer {_account_jwt(account)}",
    }
    response = boundary.client.post(
        "/api/voice/messages/11/speak", json={}, headers=headers
    )
    assert response.status_code == status, response.text
    if status == 403:
        boundary.sign.assert_not_called()


@pytest.mark.asyncio
async def test_denied_turn_does_not_read_upload(boundary):
    from unittest.mock import AsyncMock

    from fastapi import HTTPException

    upload = SimpleNamespace(read=AsyncMock(), content_type="audio/wav")
    with pytest.raises(HTTPException) as denied:
        await voice.voice_turn(
            thread_id=2, audio_file=upload, request_user_scope=boundary.scope["value"]
        )
    assert denied.value.status_code == 403
    upload.read.assert_not_called()
