from __future__ import annotations

from fastapi.testclient import TestClient

from backend.tts_service import app as tts_app


class _StubBackend:
    def synthesize(
        self,
        *,
        text: str,
        voice=None,
        speed=None,
        ref_audio=None,
        ref_text=None,
    ):
        assert isinstance(text, str)
        return (b"RIFF....WAVE", 24000)


def _invoke_payload(
    *,
    capability: str = "tts",
    action: str = "speak",
    input_payload: dict | None = None,
):
    return {
        "protocol_version": "1.0",
        "plugin_id": "chatterbox",
        "capability": capability,
        "action": action,
        "input": input_payload or {"text": "hello"},
        "context": {
            "request_id": "req-1",
            "thread_id": "thread-1",
            "user_id": "user-1",
        },
    }


def test_health_route_works():
    client = TestClient(tts_app.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_invoke_accepts_canonical_envelope_and_returns_canonical_success(
    monkeypatch,
):
    monkeypatch.setattr(
        tts_app, "_resolve_backend", lambda provider: _StubBackend()
    )
    client = TestClient(tts_app.app)

    response = client.post("/invoke", json=_invoke_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["output"]["format"] == "wav"
    assert payload["output"]["mime_type"] == "audio/wav"
    assert payload["output"]["provider"] == "qwen3_1.7b"
    assert payload["output"]["sampling_rate"] == 24000
    assert isinstance(payload["output"]["audio_base64"], str)
    assert len(payload["output"]["audio_base64"]) > 0


def test_invoke_returns_canonical_failure_for_invalid_operation():
    client = TestClient(tts_app.app)

    response = client.post(
        "/invoke",
        json=_invoke_payload(capability="tts", action="voices"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["output"] is None
    assert payload["error"]["code"] == "unsupported_operation"


def test_invoke_returns_canonical_failure_for_payload_mismatch():
    client = TestClient(tts_app.app)

    response = client.post(
        "/invoke",
        json=_invoke_payload(input_payload={"message": "wrong_key"}),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["output"] is None
    assert payload["error"]["code"] == "invalid_input"


def test_invoke_returns_canonical_failure_when_backend_errors(monkeypatch):
    def _raise_provider(_provider: str):
        raise ValueError("provider broken")

    monkeypatch.setattr(tts_app, "_resolve_backend", _raise_provider)
    client = TestClient(tts_app.app)

    response = client.post("/invoke", json=_invoke_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["output"] is None
    assert payload["error"]["code"] == "invalid_provider"
