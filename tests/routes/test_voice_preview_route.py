from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from guardian.routes import voice


@pytest.fixture
def test_client() -> TestClient:
    app = FastAPI()
    app.include_router(voice.router)
    return TestClient(app)


def test_voice_preview_happy_path_returns_ephemeral_playable_payload(
    test_client, monkeypatch
):
    class _DummyTTSManager:
        def preview_contract(self, provider_name):
            assert provider_name == "qwen3_tts"
            return {
                "providerId": "qwen3_tts",
                "voiceState": "available",
                "statusDetail": "Provider is available for Persona Studio voice selection.",
                "capabilities": {
                    "presetVoices": True,
                    "cloning": False,
                    "promptDefinedVoice": False,
                    "preview": True,
                },
                "voices": [
                    {
                        "voiceId": "default",
                        "label": "default",
                        "kind": "preset",
                        "previewSupported": True,
                        "bindingSupported": True,
                        "summary": None,
                    }
                ],
            }

    def _should_not_persist(*args, **kwargs):
        raise AssertionError("preview must not touch message-audio persistence")

    monkeypatch.setattr(
        "guardian.routes.voice.TTSManager", lambda: _DummyTTSManager()
    )
    monkeypatch.setattr(
        "guardian.routes.voice.synthesize",
        lambda *args, **kwargs: (b"RIFF....WAVE", "wav"),
    )
    monkeypatch.setattr(
        "guardian.routes.voice.save_message_audio_asset", _should_not_persist
    )
    monkeypatch.setattr(
        "guardian.routes.voice.find_cached_asset", _should_not_persist
    )
    monkeypatch.setattr(
        "guardian.routes.voice._load_message", _should_not_persist
    )

    response = test_client.post(
        "/api/voice/preview",
        json={
            "provider": "qwen3_tts",
            "voice_id": "default",
            "sample_text": "Preview this voice.",
            "speed": 1.0,
            "style": "neutral",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["providerId"] == "qwen3_tts"
    assert payload["voiceId"] == "default"
    assert payload["state"] == "available"
    assert payload["preview"]["contentType"] == "audio/wav"
    assert payload["preview"]["playbackUrl"].startswith(
        "data:audio/wav;base64,"
    )
    assert payload["ephemeral"] is True
    assert payload["persistsPersonaState"] is False
    assert payload["linksMessageHistory"] is False
    assert payload["statusDetail"] == "Preview generated for immediate playback only."


def test_voice_preview_returns_truthful_degraded_response_when_unsupported(
    test_client, monkeypatch
):
    class _DummyTTSManager:
        def preview_contract(self, provider_name):
            assert provider_name == "minimax"
            return {
                "providerId": "minimax",
                "voiceState": "degraded",
                "statusDetail": "Provider exposes selectable voices but does not support preview.",
                "capabilities": {
                    "presetVoices": False,
                    "cloning": False,
                    "promptDefinedVoice": False,
                    "preview": False,
                },
                "voices": [],
            }

    monkeypatch.setattr(
        "guardian.routes.voice.TTSManager", lambda: _DummyTTSManager()
    )

    response = test_client.post(
        "/api/voice/preview",
        json={
            "provider": "minimax",
            "voice_id": "calm",
            "sample_text": "Preview this voice.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "degraded"
    assert payload["preview"] is None
    assert payload["ephemeral"] is True
    assert payload["linksMessageHistory"] is False


def test_voice_preview_rejects_invalid_provider_and_voice_input(
    test_client, monkeypatch
):
    class _ProviderMissingManager:
        def preview_contract(self, provider_name):
            raise voice.ProviderNotFoundError(provider_name)

    monkeypatch.setattr(
        "guardian.routes.voice.TTSManager", lambda: _ProviderMissingManager()
    )

    missing_provider = test_client.post(
        "/api/voice/preview",
        json={
            "provider": "unknown_provider",
            "voice_id": "default",
            "sample_text": "Preview this voice.",
        },
    )

    assert missing_provider.status_code == 404
    assert missing_provider.json()["detail"] == "provider_not_found"

    class _VoiceMissingManager:
        def preview_contract(self, provider_name):
            assert provider_name == "qwen3_tts"
            return {
                "providerId": "qwen3_tts",
                "voiceState": "available",
                "statusDetail": "Provider is available for Persona Studio voice selection.",
                "capabilities": {
                    "presetVoices": True,
                    "cloning": False,
                    "promptDefinedVoice": False,
                    "preview": True,
                },
                "voices": [
                    {
                        "voiceId": "default",
                        "label": "default",
                        "kind": "preset",
                        "previewSupported": True,
                        "bindingSupported": True,
                        "summary": None,
                    }
                ],
            }

    monkeypatch.setattr(
        "guardian.routes.voice.TTSManager", lambda: _VoiceMissingManager()
    )

    missing_voice = test_client.post(
        "/api/voice/preview",
        json={
            "provider": "qwen3_tts",
            "voice_id": "narrator",
            "sample_text": "Preview this voice.",
        },
    )

    assert missing_voice.status_code == 400
    assert missing_voice.json()["detail"] == "voice_not_found"


def test_voice_preview_has_no_message_bound_persistence_side_effects(
    test_client, monkeypatch
):
    calls = {
        "synthesize": 0,
        "save_message_audio_asset": 0,
        "find_cached_asset": 0,
        "_load_message": 0,
    }

    class _DummyTTSManager:
        def preview_contract(self, provider_name):
            return {
                "providerId": provider_name,
                "voiceState": "available",
                "statusDetail": "Provider is available for Persona Studio voice selection.",
                "capabilities": {
                    "presetVoices": True,
                    "cloning": False,
                    "promptDefinedVoice": False,
                    "preview": True,
                },
                "voices": [
                    {
                        "voiceId": "default",
                        "label": "default",
                        "kind": "preset",
                        "previewSupported": True,
                        "bindingSupported": True,
                        "summary": None,
                    }
                ],
            }

    def _synthesize(*args, **kwargs):
        calls["synthesize"] += 1
        return (b"RIFF....WAVE", "wav")

    def _record_unexpected(name):
        def _inner(*args, **kwargs):
            calls[name] += 1
            raise AssertionError(f"{name} should not be called by preview")

        return _inner

    monkeypatch.setattr(
        "guardian.routes.voice.TTSManager", lambda: _DummyTTSManager()
    )
    monkeypatch.setattr("guardian.routes.voice.synthesize", _synthesize)
    monkeypatch.setattr(
        "guardian.routes.voice.save_message_audio_asset",
        _record_unexpected("save_message_audio_asset"),
    )
    monkeypatch.setattr(
        "guardian.routes.voice.find_cached_asset",
        _record_unexpected("find_cached_asset"),
    )
    monkeypatch.setattr(
        "guardian.routes.voice._load_message",
        _record_unexpected("_load_message"),
    )

    response = test_client.post(
        "/api/voice/preview",
        json={
            "provider": "qwen3_tts",
            "preset_id": "default",
            "sample_text": "Persona Studio preview only.",
        },
    )

    assert response.status_code == 200
    assert calls["synthesize"] == 1
    assert calls["save_message_audio_asset"] == 0
    assert calls["find_cached_asset"] == 0
    assert calls["_load_message"] == 0
