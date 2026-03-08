from __future__ import annotations

import pytest
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


@pytest.fixture(autouse=True)
def _reset_runtime_state(monkeypatch):
    monkeypatch.setenv("CODEXIFY_TTS_PRELOAD_ON_STARTUP", "0")
    tts_app._reset_runtime_state_for_tests()
    yield
    tts_app._reset_runtime_state_for_tests()


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
    tts_app._set_provider_phase(
        tts_app.DEFAULT_PROVIDER,
        tts_app.STARTUP_PHASE_MODEL_LOADING,
        ready=False,
    )
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "loading"
    assert payload["ready"] is False
    assert payload["startup_phase"] == "model_loading"
    assert payload["service"] == "Codexify Local TTS Service"
    assert payload["default_provider"] == tts_app.DEFAULT_PROVIDER
    assert payload["providers"] == list(tts_app.TTS_PROVIDERS.keys())
    assert payload["provider_states"][tts_app.DEFAULT_PROVIDER]["phase"] == (
        "model_loading"
    )


def test_health_route_reports_ready_once_model_is_available():
    client = TestClient(tts_app.app)
    tts_app._set_provider_phase(
        tts_app.DEFAULT_PROVIDER,
        tts_app.STARTUP_PHASE_MODEL_READY,
        ready=True,
    )

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["ready"] is True
    assert payload["startup_phase"] == "model_ready"
    assert payload["startup_error"] is None


def test_invoke_accepts_canonical_envelope_and_returns_canonical_success(
    monkeypatch,
):
    backend = _StubBackend()
    tts_app._set_provider_phase(
        tts_app.DEFAULT_PROVIDER,
        tts_app.STARTUP_PHASE_MODEL_READY,
        ready=True,
    )
    tts_app._BACKEND_CACHE[tts_app.DEFAULT_PROVIDER] = backend
    client = TestClient(tts_app.app)

    response = client.post("/invoke", json=_invoke_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["error"] is None
    assert payload["output"]["format"] == "wav"
    assert payload["output"]["mime_type"] == "audio/wav"
    assert payload["output"]["provider"] == tts_app.DEFAULT_PROVIDER
    assert payload["output"]["sampling_rate"] == 24000
    assert isinstance(payload["output"]["audio_base64"], str)
    assert len(payload["output"]["audio_base64"]) > 0


def test_invoke_rejects_clearly_when_service_is_not_ready(monkeypatch):
    tts_app._set_provider_phase(
        tts_app.DEFAULT_PROVIDER,
        tts_app.STARTUP_PHASE_MODEL_LOADING,
        ready=False,
    )
    monkeypatch.setattr(tts_app, "_start_provider_load", lambda *a, **k: None)
    client = TestClient(tts_app.app)

    response = client.post("/invoke", json=_invoke_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["output"] is None
    assert payload["error"]["code"] == "service_not_ready"
    assert payload["error"]["retryable"] is True
    assert "model_loading" in payload["error"]["message"]


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
    class _BrokenBackend:
        def synthesize(self, **kwargs):
            raise RuntimeError("provider broken")

    tts_app._set_provider_phase(
        tts_app.DEFAULT_PROVIDER,
        tts_app.STARTUP_PHASE_MODEL_READY,
        ready=True,
    )
    tts_app._BACKEND_CACHE[tts_app.DEFAULT_PROVIDER] = _BrokenBackend()
    client = TestClient(tts_app.app)

    response = client.post("/invoke", json=_invoke_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["output"] is None
    assert payload["error"]["code"] == "synthesis_failed"


def test_provider_preload_path_transitions_to_ready(monkeypatch):
    class _PreloadedBackend:
        @property
        def pipeline(self):
            return object()

    monkeypatch.setattr(
        tts_app, "_resolve_backend", lambda provider: _PreloadedBackend()
    )

    tts_app._load_provider_backend(tts_app.DEFAULT_PROVIDER, trigger="test")
    snapshot = tts_app._runtime_snapshot()

    assert snapshot["status"] == "healthy"
    assert snapshot["ready"] is True
    assert snapshot["startup_phase"] == "model_ready"
    assert (
        snapshot["provider_states"][tts_app.DEFAULT_PROVIDER]["phase"]
        == "model_ready"
    )
