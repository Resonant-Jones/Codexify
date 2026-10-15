from pathlib import Path

from guardian.tts.contracts import (
    TTS_BACKEND_QWEN3,
    TTSBackendStatus,
    TTSHealthProbe,
    TTSRenderRequest,
)
from guardian.tts.config import get_local_tts_config
from guardian.tts.tts_manager import TTSManager


def test_tts_health_probe_serializes_status_token():
    probe = TTSHealthProbe(
        backend_id=TTS_BACKEND_QWEN3,
        status=TTSBackendStatus.UNAVAILABLE,
        installed=False,
        model_files_available=False,
        importable=False,
        healthy=False,
        failure_reason="qwen3_model_path_missing",
    )

    payload = probe.to_dict()

    assert payload["backend_id"] == "qwen3_tts"
    assert payload["status"] == "backend_unavailable"
    assert payload["healthy"] is False
    assert payload["failure_reason"] == "qwen3_model_path_missing"


def test_render_request_carries_voice_and_format():
    request = TTSRenderRequest(
        text="hello",
        output_path=Path("/tmp/example.wav"),
        backend_id=TTS_BACKEND_QWEN3,
        output_format="wav",
        voice_id="default",
    )

    assert request.backend_id == "qwen3_tts"
    assert request.output_format == "wav"
    assert request.voice_id == "default"


def test_config_defaults_to_qwen3_backend(monkeypatch):
    monkeypatch.delenv("CODEXIFY_TTS_BACKEND", raising=False)
    monkeypatch.delenv("CODEXIFY_TTS_PROVIDER", raising=False)

    cfg = get_local_tts_config()

    assert cfg.backend_id == "qwen3_tts"
    assert cfg.local_only is True


def test_tts_manager_default_ignores_legacy_json_mock_default(monkeypatch):
    monkeypatch.delenv("TTS_DEFAULT_PROVIDER", raising=False)
    monkeypatch.delenv("CODEXIFY_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("CODEXIFY_TTS_BACKEND", raising=False)

    manager = TTSManager()

    assert manager.default_provider == "qwen3_tts"
