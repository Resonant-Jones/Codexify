"""Deepgram voice provider tests.

Covers the provider adapter (TTS), the voice-runtime STT branch, the
provider-agnostic native-format resolution, and the cloud-posture gates.
"""

from __future__ import annotations

import json
import types

import pytest

from guardian.core.egress import EgressDeniedError
from guardian.tts.providers.deepgram_provider import (
    AURA_MAX_REQUEST_CHARS,
    AURA_VOICE_IDS,
    DeepgramProvider,
)
from guardian.tts.tts_manager import TTSManager
from guardian.tts.tts_service import (
    AuthenticationError,
    SynthesisError,
    VoiceNotFoundError,
)
from guardian.voice import service as voice_service
from guardian.voice.runtime import SUPPORTED_STT_PROVIDERS, SUPPORTED_TTS_PROVIDERS
from guardian.voice.service import (
    VoiceProviderError,
    VoiceTimeoutError,
    _provider_default_format,
    transcribe_audio,
)


@pytest.fixture(autouse=True)
def _cloud_posture(monkeypatch):
    """Allow the cloud posture for the duration of each test."""
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "false")
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "true")
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "deepgram")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.delenv("DEEPGRAM_TTS_MODEL", raising=False)
    monkeypatch.delenv("DEEPGRAM_STT_MODEL", raising=False)


class _Response:
    def __init__(self, status_code=200, content=b"", payload=None):
        self.status_code = status_code
        self.content = content
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _HTTPError(self.status_code, self.content)


class _HTTPError(Exception):
    def __init__(self, status_code, content=b""):
        super().__init__(f"http {status_code}")
        self.response = types.SimpleNamespace(
            status_code=status_code, text=content.decode("utf-8", "replace")
        )


# --- Registration -----------------------------------------------------------


def test_deepgram_is_registered_as_a_provider_not_a_backend():
    """Deepgram is a `providers/` adapter; the `backends/` registry is unchanged."""
    from guardian.tts import backends

    assert "deepgram" not in backends.registered_tts_backend_ids()
    manager = TTSManager()
    assert "deepgram" in manager.providers
    assert "deepgram" in SUPPORTED_TTS_PROVIDERS
    assert "deepgram" in SUPPORTED_STT_PROVIDERS


def test_deepgram_declares_mp3_as_its_native_container():
    assert DeepgramProvider.native_output_format == "mp3"
    assert TTSManager().native_output_format("deepgram") == "mp3"


def test_native_format_resolution_is_provider_agnostic():
    """The runtime resolves the container from the provider, not from a name map."""
    assert _provider_default_format("deepgram") == "mp3"
    assert _provider_default_format("elevenlabs") == "mp3"
    assert _provider_default_format("minimax") == "mp3"
    assert _provider_default_format("google") == "wav"
    assert _provider_default_format("qwen3_tts") == "wav"


# --- TTS adapter ------------------------------------------------------------


def test_synthesize_posts_to_deepgram_speak_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, params=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["json"] = json
        captured["timeout"] = timeout
        return _Response(200, content=b"ID3-mp3-bytes")

    monkeypatch.setattr("guardian.tts.providers.deepgram_provider.requests.post", fake_post)

    provider = DeepgramProvider()
    audio = provider.synthesize("hello there", "aura-2-thalia-en")

    assert audio == b"ID3-mp3-bytes"
    assert captured["url"] == "https://api.deepgram.com/v1/speak"
    assert captured["headers"]["Authorization"] == "Token test-deepgram-key"
    assert captured["params"] == {"model": "aura-2-thalia-en", "encoding": "mp3"}
    assert captured["json"] == {"text": "hello there"}


def test_list_voices_returns_the_aura_catalogue():
    voices = DeepgramProvider().list_voices()
    assert voices == list(AURA_VOICE_IDS)
    assert "aura-2-thalia-en" in voices
    assert len(voices) == 41


def test_missing_api_key_raises_authentication_error(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    with pytest.raises(AuthenticationError):
        DeepgramProvider()


def test_egress_denial_raises_synthesis_error(monkeypatch):
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "deepseek")
    with pytest.raises(SynthesisError):
        DeepgramProvider()


def test_unauthorized_response_raises_authentication_error(monkeypatch):
    monkeypatch.setattr(
        "guardian.tts.providers.deepgram_provider.requests.post",
        lambda *args, **kwargs: _Response(401, content=b'{"err_msg":"bad key"}'),
    )
    with pytest.raises(AuthenticationError):
        DeepgramProvider().synthesize("hello", "aura-2-thalia-en")


def test_missing_voice_raises_voice_not_found(monkeypatch):
    monkeypatch.setattr(
        "guardian.tts.providers.deepgram_provider.requests.post",
        lambda *args, **kwargs: _Response(404, content=b"{}"),
    )
    with pytest.raises(VoiceNotFoundError):
        DeepgramProvider().synthesize("hello", "aura-2-does-not-exist-en")


def test_empty_text_is_rejected(monkeypatch):
    with pytest.raises(SynthesisError):
        DeepgramProvider().synthesize("   ", "aura-2-thalia-en")


def test_long_text_is_chunked_to_the_aura_request_limit(monkeypatch):
    captured = []

    def fake_post(url, headers=None, params=None, json=None, timeout=None):
        captured.append(json["text"])
        return _Response(200, content=b"mp3")

    monkeypatch.setattr("guardian.tts.providers.deepgram_provider.requests.post", fake_post)

    text = "word. " * 600
    DeepgramProvider().synthesize(text, "aura-2-thalia-en")

    assert len(captured) > 1
    assert all(len(chunk) <= AURA_MAX_REQUEST_CHARS for chunk in captured)
    assert "".join(captured).replace(" ", "") == text.replace(" ", "")


# --- STT branch -------------------------------------------------------------


def test_transcribe_uses_deepgram_listen_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["files"] = files
        captured["data"] = data
        return _Response(
            200,
            payload={
                "results": {
                    "channels": [{"alternatives": [{"transcript": "hello from deepgram"}]}]
                }
            },
        )

    monkeypatch.setattr("guardian.voice.service.requests.post", fake_post)

    transcript = transcribe_audio(b"RIFFfake", "audio/wav", provider="deepgram")

    assert transcript == "hello from deepgram"
    assert captured["url"] == "https://api.deepgram.com/v1/listen"
    assert captured["headers"]["Authorization"] == "Token test-deepgram-key"
    assert captured["data"]["model"] == "nova-3"


def test_transcribe_reports_an_empty_transcript(monkeypatch):
    monkeypatch.setattr(
        "guardian.voice.service.requests.post",
        lambda *args, **kwargs: _Response(
            200, payload={"results": {"channels": [{"alternatives": [{"transcript": "  "}]}]}}
        ),
    )
    with pytest.raises(VoiceProviderError) as excinfo:
        transcribe_audio(b"RIFFfake", "audio/wav", provider="deepgram")
    assert "stt_empty_transcript" in str(excinfo.value)


def test_transcribe_timeout_is_reported_as_a_voice_timeout(monkeypatch):
    import requests as requests_module

    def fake_post(*args, **kwargs):
        raise requests_module.Timeout("slow")

    monkeypatch.setattr("guardian.voice.service.requests.post", fake_post)

    with pytest.raises(VoiceTimeoutError) as excinfo:
        transcribe_audio(b"RIFFfake", "audio/wav", provider="deepgram")
    assert "stt_timeout" in str(excinfo.value)


def test_transcribe_requires_the_deepgram_credential(monkeypatch):
    monkeypatch.delenv("DEEPGRAM_API_KEY", raising=False)
    with pytest.raises(VoiceProviderError) as excinfo:
        transcribe_audio(b"RIFFfake", "audio/wav", provider="deepgram")
    assert "deepgram_api_key_missing" in str(excinfo.value)


def test_transcribe_respects_the_egress_posture(monkeypatch):
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "deepseek")
    with pytest.raises(VoiceProviderError) as excinfo:
        transcribe_audio(b"RIFFfake", "audio/wav", provider="deepgram")
    assert "stt_provider_error" in str(excinfo.value)


# --- Cloud posture gate -----------------------------------------------------


def test_cloud_provider_is_degraded_without_the_cloud_posture(monkeypatch):
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "false")
    manager = TTSManager()
    status, message, voices = manager._provider_status("deepgram")
    assert status == "degraded"
    assert "local-only" in message
    assert voices == []
