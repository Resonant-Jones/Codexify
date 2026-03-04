from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock


def _dummy_audio_file():
    return {"audio_file": ("voice.wav", b"RIFF....WAVE", "audio/wav")}


def _runtime_cfg(**overrides):
    base = {
        "mode": "off",
        "routes_enabled": True,
        "turns_enabled": False,
        "stt_provider": "local_openai_compatible",
        "tts_provider": "local_openai_compatible",
        "local_voice_base_url": "http://localhost:11434",
        "stream_proxy_enabled": False,
        "stt_timeout_seconds": 1,
        "completion_timeout_seconds": 1,
        "tts_timeout_seconds": 1,
        "input_max_bytes": 15 * 1024 * 1024,
        "output_max_bytes": 15 * 1024 * 1024,
        "max_duration_seconds": 120,
        "turn_dedupe_ttl_seconds": 600,
        "internal_format": "wav",
        "delivery_formats": ("wav",),
        "bake_models": False,
        "service_url": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_voice_capabilities_contract(test_client, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.get_voice_runtime_config",
        lambda: _runtime_cfg(turns_enabled=False),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._voice_worker_available", lambda: False
    )

    response = test_client.get("/api/voice/capabilities")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, max-age=30"
    payload = response.json()
    assert payload["read_aloud_enabled"] is True
    assert payload["turn_based_enabled"] is False
    assert payload["turn_based_reason"] == "feature_gated"
    assert payload["voice_routes_enabled"] is True
    assert payload["voice_turns_enabled"] is False
    assert payload["providers_supported"]["tts"]
    assert payload["providers_supported"]["stt"]
    assert payload["providers_configured"]["tts"] == "local_openai_compatible"
    assert payload["providers_configured"]["stt"] == "local_openai_compatible"
    assert payload["limits"]["max_upload_bytes"] == 15 * 1024 * 1024
    assert payload["limits"]["max_duration_s"] == 120


def test_voice_capabilities_marks_local_provider_misconfigured(
    test_client, monkeypatch
):
    monkeypatch.setattr(
        "guardian.routes.voice.get_voice_runtime_config",
        lambda: _runtime_cfg(local_voice_base_url=None),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._voice_worker_available", lambda: True
    )

    response = test_client.get("/api/voice/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_aloud_enabled"] is False
    assert payload["read_aloud_reason"] == "misconfigured"
    assert payload["providers_configured"]["tts"] is None
    assert payload["providers_configured"]["stt"] is None


def test_voice_turn_worker_missing_fails_before_lock(test_client, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.get_voice_runtime_config",
        lambda: _runtime_cfg(turns_enabled=True),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._voice_worker_available", lambda: False
    )

    lock_calls = {"count": 0}

    def _acquire_lock(*args, **kwargs):
        lock_calls["count"] += 1
        return True

    monkeypatch.setattr(
        "guardian.routes.voice.acquire_turn_lock", _acquire_lock
    )

    response = test_client.post(
        "/api/voice/turn",
        data={"thread_id": "1", "tts_enabled": "true"},
        files=_dummy_audio_file(),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "voice_worker_missing"
    assert lock_calls["count"] == 0


def test_voice_turn_dedupe_hit(test_client, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.get_voice_runtime_config",
        lambda: _runtime_cfg(turns_enabled=True),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._voice_worker_available", lambda: True
    )
    monkeypatch.setattr(
        "guardian.routes.voice.chatlog_db",
        SimpleNamespace(get_chat_thread=lambda *_: {"id": 1}),
    )
    monkeypatch.setattr(
        "guardian.routes.voice.normalize_audio_input",
        lambda *_a, **_k: (
            b"wav-bytes",
            "audio/wav",
            {
                "duration_seconds": 1.0,
                "sample_rate_hz": 16000,
                "channels": 1,
                "size_bytes": 9,
            },
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._get_dedupe_hit",
        lambda **_k: {
            "deduped": True,
            "task_id": "existing-task",
            "status": "in_flight",
        },
    )

    lock_calls = {"count": 0}

    def _acquire_lock(*args, **kwargs):
        lock_calls["count"] += 1
        return True

    monkeypatch.setattr(
        "guardian.routes.voice.acquire_turn_lock", _acquire_lock
    )

    response = test_client.post(
        "/api/voice/turn",
        data={"thread_id": "1", "tts_enabled": "true"},
        files=_dummy_audio_file(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "deduped": True,
        "task_id": "existing-task",
        "status": "in_flight",
    }
    assert lock_calls["count"] == 0


def test_voice_turn_completed(test_client, mock_db, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.get_voice_runtime_config",
        lambda: _runtime_cfg(turns_enabled=True),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._voice_worker_available", lambda: True
    )
    monkeypatch.setattr("guardian.routes.voice.chatlog_db", mock_db)
    monkeypatch.setattr(
        "guardian.routes.voice.normalize_audio_input",
        lambda *_a, **_k: (
            b"wav-bytes",
            "audio/wav",
            {
                "duration_seconds": 1.0,
                "sample_rate_hz": 16000,
                "channels": 1,
                "size_bytes": 9,
            },
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._get_dedupe_hit", lambda **_k: None
    )
    monkeypatch.setattr(
        "guardian.routes.voice.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr("guardian.routes.voice.enqueue", lambda *a, **k: None)
    monkeypatch.setattr(
        "guardian.routes.voice.task_events.publish", lambda *a, **k: None
    )
    monkeypatch.setattr(
        "guardian.routes.voice._set_dedupe_record", lambda **_k: None
    )

    class _DummyVoiceTurnTask:
        type = "voice_turn"

        def __init__(self, **kwargs):
            self.task_id = "voice-task-1"
            self.origin = kwargs.get("origin", "test")
            self.turn_lock_owner = kwargs.get("turn_lock_owner")
            self.thread_id = kwargs.get("thread_id", 0)
            for key, value in kwargs.items():
                setattr(self, key, value)

    monkeypatch.setattr(
        "guardian.routes.voice._get_voice_turn_task_cls",
        lambda: _DummyVoiceTurnTask,
    )

    await_mock = AsyncMock(
        return_value=(
            "task.completed",
            {
                "status": "succeeded",
                "thread_id": 1,
                "transcript": "hello",
                "user_message_id": 11,
                "assistant_message_id": 12,
                "assistant_text": "world",
                "audio_asset": None,
            },
        )
    )
    monkeypatch.setattr(
        "guardian.routes.voice._await_terminal_task_event", await_mock
    )

    response = test_client.post(
        "/api/voice/turn",
        data={"thread_id": "1", "tts_enabled": "true"},
        files=_dummy_audio_file(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["thread_id"] == 1
    assert payload["task_id"] == "voice-task-1"


def test_voice_turn_lock_conflict(test_client, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.get_voice_runtime_config",
        lambda: _runtime_cfg(turns_enabled=True),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._voice_worker_available", lambda: True
    )
    monkeypatch.setattr(
        "guardian.routes.voice.chatlog_db",
        SimpleNamespace(get_chat_thread=lambda *_: {"id": 1}),
    )
    monkeypatch.setattr(
        "guardian.routes.voice.acquire_turn_lock", lambda *a, **k: False
    )
    monkeypatch.setattr(
        "guardian.routes.voice.normalize_audio_input",
        lambda *_a, **_k: (
            b"wav-bytes",
            "audio/wav",
            {
                "duration_seconds": 1.0,
                "sample_rate_hz": 16000,
                "channels": 1,
                "size_bytes": 9,
            },
        ),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._get_dedupe_hit", lambda **_k: None
    )

    response = test_client.post(
        "/api/voice/turn",
        data={"thread_id": "1", "tts_enabled": "true"},
        files=_dummy_audio_file(),
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "turn_in_flight"


def test_speak_message_returns_cached_asset(test_client, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.STREAM_PROXY_ENABLED",
        True,
    )
    monkeypatch.setattr(
        "guardian.routes.voice._load_message",
        lambda *_: SimpleNamespace(id=55, content="hello world"),
    )
    monkeypatch.setattr(
        "guardian.routes.voice.find_cached_asset",
        lambda **_: {
            "id": 9,
            "message_id": 55,
            "provider": "local_openai_compatible",
            "voice": "alloy",
            "text_hash": "abc",
            "src_url": "/media/audio/messages/55.wav",
            "url_expires_at": None,
            "internal_format": "wav",
        },
    )

    response = test_client.post(
        "/api/voice/messages/55/speak",
        json={"provider": "local_openai_compatible", "voice": "alloy"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message_id"] == 55
    assert payload["cached"] is True
    assert payload["audio_asset"]["src_url"].endswith("55.wav")
    assert payload["audio_asset"]["url_expires_at"] is None
    assert payload["audio_asset"]["stream_url"] == "/api/voice/audio/9"
