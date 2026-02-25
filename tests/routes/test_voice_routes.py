from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock


def _dummy_audio_file():
    return {"audio_file": ("voice.wav", b"RIFF....WAVE", "audio/wav")}


def test_voice_turn_completed(test_client, mock_db, monkeypatch):
    monkeypatch.setattr("guardian.routes.voice.chatlog_db", mock_db)
    monkeypatch.setattr(
        "guardian.routes.voice.acquire_turn_lock", lambda *a, **k: True
    )
    monkeypatch.setattr("guardian.routes.voice.enqueue", lambda *a, **k: None)
    monkeypatch.setattr(
        "guardian.routes.voice.enforce_audio_input_limits", lambda *a, **k: 1.0
    )
    monkeypatch.setattr(
        "guardian.routes.voice.task_events.publish", lambda *a, **k: None
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
    assert payload["task_id"]


def test_voice_turn_lock_conflict(test_client, monkeypatch):
    monkeypatch.setattr(
        "guardian.routes.voice.chatlog_db",
        SimpleNamespace(get_chat_thread=lambda *_: {"id": 1}),
    )
    monkeypatch.setattr(
        "guardian.routes.voice.acquire_turn_lock", lambda *a, **k: False
    )
    monkeypatch.setattr(
        "guardian.routes.voice.enforce_audio_input_limits", lambda *a, **k: 1.0
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
