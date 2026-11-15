"""Prerecorded STT wire contract; synthetic input and mocked HTTP transport only."""

from __future__ import annotations

import io
import json
import socket
import wave
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
import requests

from guardian.voice import service


@pytest.fixture(autouse=True)
def _isolated_transport(monkeypatch):
    def deny_socket(*args, **kwargs):
        raise AssertionError("outbound sockets are forbidden in STT contract tests")

    monkeypatch.setattr(socket.socket, "connect", deny_socket)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_socket)
    monkeypatch.setattr(socket.socket, "sendto", deny_socket)
    monkeypatch.setenv("CODEXIFY_LOCAL_ONLY_MODE", "false")
    monkeypatch.setenv("ALLOW_CLOUD_PROVIDERS", "true")
    monkeypatch.setenv("CODEXIFY_EGRESS_ALLOWLIST", "deepgram")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "synthetic-stt-key")
    monkeypatch.delenv("DEEPGRAM_STT_ENDPOINT", raising=False)
    monkeypatch.delenv("DEEPGRAM_STT_MODEL", raising=False)
    monkeypatch.delenv("CODEXIFY_STT_MODEL", raising=False)


@pytest.fixture
def audio():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(b"\x00\x00" * 160)
    return buffer.getvalue()


def _payload(text="  synthetic transcript  "):
    return {"results": {"channels": [{"alternatives": [{"transcript": text}]}]}}


def _response(request, *, status=200, payload=None):
    response = requests.Response()
    response.status_code = status
    response.url = request.url
    response.request = request
    response._content = json.dumps(
        payload if payload is not None else _payload()
    ).encode()
    return response


@pytest.mark.parametrize("mime", ["audio/wav", "audio/x-wav", None])
@pytest.mark.parametrize("model", [None, "nova-2"])
def test_deepgram_prepared_request_contains_raw_audio_and_query_options(
    monkeypatch, audio, caplog, mime, model
):
    if model:
        monkeypatch.setenv("DEEPGRAM_STT_MODEL", model)
    captured = []

    def send(session, request, **kwargs):
        captured.append((request, kwargs))
        return _response(request)

    monkeypatch.setattr(requests.Session, "send", send)
    transcript = service.transcribe_audio(
        audio, mime, provider="deepgram", timeout_seconds=7
    )

    assert transcript == "synthetic transcript"
    assert len(captured) == 1
    request, options = captured[0]
    parsed = urlsplit(request.url)
    assert request.method == "POST"
    assert (parsed.scheme, parsed.netloc, parsed.path) == (
        "https",
        "api.deepgram.com",
        "/v1/listen",
    )
    assert parse_qs(parsed.query) == {
        "model": [model or "nova-3"],
        "smart_format": ["true"],
    }
    assert request.body == audio
    assert request.headers["Content-Type"] == (mime or "audio/wav")
    assert int(request.headers["Content-Length"]) == len(audio)
    assert request.headers["Authorization"] == "Token synthetic-stt-key"
    assert "synthetic-stt-key" not in request.url
    assert b"synthetic-stt-key" not in request.body
    assert "synthetic-stt-key" not in caplog.text
    assert options["timeout"] == 7.0


@pytest.mark.parametrize("status", [401, 429, 500])
def test_http_failure_stops_before_transcript_parsing(monkeypatch, audio, status):
    def send(session, request, **kwargs):
        response = _response(request, status=status)

        def unexpected_json():
            pytest.fail("HTTP errors must be handled before parsing a transcript")

        response.json = unexpected_json
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    with pytest.raises(
        service.VoiceProviderError, match="^stt_provider_error:"
    ) as error:
        service.transcribe_audio(audio, "audio/wav", provider="deepgram")
    assert "synthetic-stt-key" not in str(error.value)


@pytest.mark.parametrize(
    ("failure", "error", "message"),
    [
        (requests.Timeout("slow"), service.VoiceTimeoutError, "^stt_timeout$"),
        (
            requests.ConnectionError("offline"),
            service.VoiceProviderError,
            "^stt_provider_error:",
        ),
    ],
)
def test_transport_errors_keep_existing_mapping(
    monkeypatch, audio, failure, error, message
):
    def send(*args, **kwargs):
        raise failure

    monkeypatch.setattr(requests.Session, "send", send)
    with pytest.raises(error, match=message):
        service.transcribe_audio(audio, "audio/wav", provider="deepgram")


def test_json_parse_failure_keeps_existing_mapping(monkeypatch, audio):
    def send(session, request, **kwargs):
        response = _response(request)

        def invalid_json():
            raise ValueError("invalid JSON")

        response.json = invalid_json
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    with pytest.raises(service.VoiceProviderError, match="^stt_parse_error:"):
        service.transcribe_audio(audio, "audio/wav", provider="deepgram")


def test_requests_json_decode_error_keeps_existing_provider_error_mapping(
    monkeypatch, audio
):
    def send(session, request, **kwargs):
        response = _response(request)
        response._content = b"{invalid JSON"
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    with pytest.raises(service.VoiceProviderError, match="^stt_provider_error:"):
        service.transcribe_audio(audio, "audio/wav", provider="deepgram")


def test_endpoint_override_is_preserved(monkeypatch, audio):
    monkeypatch.setenv(
        "DEEPGRAM_STT_ENDPOINT", "https://stt.invalid/v1/listen?tag=synthetic"
    )
    captured = []

    def send(session, request, **kwargs):
        captured.append(request)
        return _response(request)

    monkeypatch.setattr(requests.Session, "send", send)
    service.transcribe_audio(audio, "audio/wav", provider="deepgram")
    parsed = urlsplit(captured[0].url)
    assert (parsed.netloc, parsed.path) == ("stt.invalid", "/v1/listen")
    assert parse_qs(parsed.query) == {
        "tag": ["synthetic"],
        "model": ["nova-3"],
        "smart_format": ["true"],
    }
    assert captured[0].body == audio


@pytest.mark.parametrize(
    "payload", [{}, {"results": {}}, {"results": {"channels": []}}, _payload("")]
)
def test_missing_or_empty_transcript_is_rejected(monkeypatch, audio, payload):
    monkeypatch.setattr(
        requests.Session,
        "send",
        lambda session, request, **kwargs: _response(request, payload=payload),
    )
    with pytest.raises(service.VoiceProviderError, match="^stt_empty_transcript$"):
        service.transcribe_audio(audio, "audio/wav", provider="deepgram")


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        ("CODEXIFY_LOCAL_ONLY_MODE", "true", "stt_provider_error:"),
        ("ALLOW_CLOUD_PROVIDERS", "false", "stt_provider_error:"),
        ("CODEXIFY_EGRESS_ALLOWLIST", "deepseek", "stt_provider_error:"),
        ("DEEPGRAM_API_KEY", "", "deepgram_api_key_missing"),
    ],
)
def test_cloud_and_credential_gates_precede_transport(
    monkeypatch, audio, setting, value, message
):
    monkeypatch.setenv(setting, value)

    def unexpected_send(*args, **kwargs):
        pytest.fail("denied STT must not reach the HTTP transport")

    monkeypatch.setattr(requests.Session, "send", unexpected_send)
    with pytest.raises(service.VoiceProviderError, match=message):
        service.transcribe_audio(audio, "audio/wav", provider="deepgram")


@pytest.mark.parametrize(
    "provider", ["local_openai_compatible", "whisper_local", "whispercpp", "openai"]
)
def test_openai_compatible_stt_still_uses_multipart(monkeypatch, audio, provider):
    monkeypatch.setenv("CODEXIFY_LOCAL_VOICE_BASE_URL", "http://local-voice.invalid")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openai.invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-key")
    monkeypatch.setenv("LOCAL_API_KEY", "synthetic-local-key")
    captured = []

    def post(endpoint, **kwargs):
        captured.append((endpoint, kwargs))
        return types_response

    types_response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=lambda: {"text": "  other provider  "},
    )
    monkeypatch.setattr(service.requests, "post", post)
    assert (
        service.transcribe_audio(audio, "audio/wav", provider=provider)
        == "other provider"
    )
    endpoint, options = captured[0]
    cloud = provider == "openai"
    assert endpoint == (
        "https://openai.invalid/v1/audio/transcriptions"
        if cloud
        else "http://local-voice.invalid/v1/audio/transcriptions"
    )
    assert options["headers"] == {
        "Authorization": (
            "Bearer synthetic-openai-key" if cloud else "Bearer synthetic-local-key"
        )
    }
    assert options["files"] == {"file": ("voice-input.wav", audio, "audio/wav")}
    assert options["data"] == {
        "model": "whisper-1" if cloud else "whisper-small.en",
        "response_format": "json",
    }
    assert "params" not in options


def test_mock_stt_does_not_use_transport(monkeypatch, audio):
    monkeypatch.setenv("CODEXIFY_STT_MOCK_TEXT", "synthetic mock")

    def unexpected_post(*args, **kwargs):
        pytest.fail("mock STT must not use HTTP")

    monkeypatch.setattr(service.requests, "post", unexpected_post)
    assert (
        service.transcribe_audio(audio, "audio/wav", provider="mock")
        == "synthetic mock"
    )
