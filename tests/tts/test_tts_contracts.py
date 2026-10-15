import json
import sys
import wave
from dataclasses import replace
from pathlib import Path

import pytest

from guardian.tts import backends
from guardian.tts.backends import TTSBackend, resolve_tts_backend
from guardian.tts.backends.qwen3 import Qwen3TTSBackend
from guardian.tts.config import get_local_tts_config
from guardian.tts.contracts import (
    TTS_BACKEND_QWEN3,
    TTSBackendCapability,
    TTSBackendInfo,
    TTSBackendStatus,
    TTSHealthProbe,
    TTSRenderRequest,
    TTSRenderResult,
)
from guardian.tts.renderer import render_voiceover
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


class _TestRemoteBackend(TTSBackend):
    """Test-only adapter: no network or credential handling."""

    def __init__(self, config):
        self.config = config
        self.requests = []

    def info(self):
        return TTSBackendInfo(
            backend_id="test_remote", display_name="Test remote", local_only=False
        )

    def health(self):
        return TTSHealthProbe(
            backend_id="test_remote",
            status=TTSBackendStatus.UNKNOWN,
            configured=True,
            credential_available=True,
            egress_allowed=False,
        )

    def render(self, request):
        self.requests.append(request)
        with wave.open(str(request.output_path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b"\x00\x00" * 24)
        return TTSRenderResult(
            backend_id=request.backend_id,
            status=TTSBackendStatus.RENDER_SUCCEEDED,
            output_path=request.output_path,
            output_format=request.output_format,
            voice_id=request.voice_id,
            render_succeeded=True,
        )


def test_metadata_declares_capability_without_health_claim():
    info = Qwen3TTSBackend().info()
    assert info.local_only is True
    assert info.output_formats == ("wav",)
    assert info.capabilities == (TTSBackendCapability.VOICE_SAMPLE_PATH,)
    payload = json.loads(json.dumps(info.to_dict()))
    assert payload["capabilities"] == ["voice_sample_path"]
    assert "healthy" not in payload
    remote = _TestRemoteBackend(None).info().to_dict()
    assert remote["local_only"] is False
    assert remote["capabilities"] == ()


def test_remote_readiness_serializes_independent_evidence():
    payload = json.loads(json.dumps(_TestRemoteBackend(None).health().to_dict()))
    assert payload["status"] == "unknown"
    assert payload["configured"] is True
    assert payload["credential_available"] is True
    assert payload["egress_allowed"] is False
    for key in (
        "installed",
        "model_files_available",
        "importable",
        "healthy",
        "reachable",
        "synthesis_proven",
    ):
        assert payload[key] is None
    probed = TTSHealthProbe(
        backend_id="test_remote",
        status=TTSBackendStatus.UNAVAILABLE,
        reachable=False,
        synthesis_proven=False,
    ).to_dict()
    assert probed["reachable"] is False
    assert probed["synthesis_proven"] is False
    assert probed["credential_available"] is None


def test_only_qwen_registered_and_unknown_id_never_falls_back():
    assert backends.registered_tts_backend_ids() == (TTS_BACKEND_QWEN3,)
    cfg = get_local_tts_config()
    backend = resolve_tts_backend(TTS_BACKEND_QWEN3, cfg)
    assert isinstance(backend, Qwen3TTSBackend)
    assert backend.config is cfg
    for backend_id in ("deepgram", "local", "local_openai_compatible", "unknown"):
        with pytest.raises(backends.UnsupportedTTSBackendError):
            resolve_tts_backend(backend_id, cfg)


def test_renderer_resolves_test_adapter_and_default_batch(monkeypatch, tmp_path):
    cfg = replace(get_local_tts_config(), chunk_max_chars=900)
    backend = _TestRemoteBackend(cfg)
    monkeypatch.setitem(
        backends._BACKEND_FACTORIES, "test_remote", lambda config: backend
    )
    result = render_voiceover(
        text="One. [pause] Two.",
        output_path=tmp_path / "voice.wav",
        backend_id="test_remote",
        config=cfg,
        voice_id="test_voice",
        language="en",
        backend_params={"test_control": 1},
    )
    assert result.render_succeeded is True
    assert [r.text for r in backend.requests] == ["One.", "Two."]
    assert all(r.backend_id == "test_remote" for r in backend.requests)
    assert all(r.voice_id == "test_voice" for r in backend.requests)
    assert all(r.language == "en" for r in backend.requests)
    assert all(r.backend_params == {"test_control": 1} for r in backend.requests)
    assert all(r.backend_id == "test_remote" for r in result.chunk_results)
    with wave.open(str(result.output_path), "rb") as audio:
        assert audio.getframerate() == 24000
        assert audio.getnframes() > 48


def test_renderer_unknown_backend_fails_before_artifact_creation(tmp_path):
    output = tmp_path / "new" / "voice.wav"
    result = render_voiceover(text="Hello", output_path=output, backend_id="deepgram")
    assert result.failure_reason == "unsupported_tts_backend:deepgram"
    assert result.render_succeeded is False
    assert not output.parent.exists()


@pytest.mark.parametrize(
    "python_ok,model_ok,import_ok,reason,installed",
    [
        (False, False, False, "qwen3_python_missing", False),
        (True, False, True, "qwen3_model_path_missing", True),
        (True, True, False, "qwen3_runtime_not_importable", False),
        (True, True, True, None, True),
    ],
)
def test_qwen_health_preserves_local_evidence(
    monkeypatch, python_ok, model_ok, import_ok, reason, installed
):
    backend = resolve_tts_backend(TTS_BACKEND_QWEN3)
    monkeypatch.setattr(backend, "_python_available", lambda: python_ok)
    monkeypatch.setattr(backend, "_model_path_available", lambda: model_ok)
    monkeypatch.setattr(backend, "_render_script_available", lambda: False)
    monkeypatch.setattr(
        backend, "_first_importable_module", lambda: "qwen_tts" if import_ok else None
    )
    probe = backend.health()
    assert probe.installed is installed
    assert probe.model_files_available is model_ok
    assert probe.importable is (python_ok and import_ok)
    assert probe.healthy is (python_ok and model_ok and import_ok)
    assert probe.failure_reason == reason
    assert probe.reachable is None
    assert probe.synthesis_proven is None


def test_qwen_registry_render_preserves_batch_override(monkeypatch, tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    script = tmp_path / "render.py"
    script.write_text(
        "import argparse, wave\n"
        "p = argparse.ArgumentParser()\n"
        "for name in ('input', 'output', 'model-path', 'voice'): p.add_argument('--' + name)\n"
        "args = p.parse_args()\n"
        "with wave.open(args.output, 'wb') as audio:\n"
        "    audio.setnchannels(1)\n"
        "    audio.setsampwidth(2)\n"
        "    audio.setframerate(24000)\n"
        "    audio.writeframes(b'\\x00\\x00' * 24)\n"
    )
    cfg = replace(
        get_local_tts_config(),
        qwen3_python=sys.executable,
        qwen3_model_path=model,
        qwen3_render_script=script,
    )
    batches = []
    original = Qwen3TTSBackend.render_many

    def tracked_batch(self, requests):
        batches.append(requests)
        return original(self, requests)

    monkeypatch.setattr(Qwen3TTSBackend, "render_many", tracked_batch)
    result = render_voiceover(
        text="One. [pause] Two.", output_path=tmp_path / "qwen.wav", config=cfg
    )
    assert result.render_succeeded is True
    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert all(
        r.status == TTSBackendStatus.RENDER_SUCCEEDED for r in result.chunk_results
    )
    assert all(r.metadata["health"]["healthy"] is True for r in result.chunk_results)
    assert result.bytes_written > 44


def test_tts_evidence_tokens_are_canonical():
    assert {status.value for status in TTSBackendStatus} == {
        "installed",
        "model_files_available",
        "importable",
        "healthy",
        "backend_unavailable",
        "render_succeeded",
        "render_failed",
        "unknown",
    }
    assert {cap.value for cap in TTSBackendCapability} == {"voice_sample_path"}


def test_adapter_failure_propagates_without_fallback(monkeypatch, tmp_path):
    cfg = get_local_tts_config()
    backend = _TestRemoteBackend(cfg)
    monkeypatch.setitem(
        backends._BACKEND_FACTORIES, "test_remote", lambda config: backend
    )
    monkeypatch.setattr(
        backend,
        "render",
        lambda request: TTSRenderResult(
            backend_id=request.backend_id,
            status=TTSBackendStatus.RENDER_FAILED,
            output_path=None,
            output_format="wav",
            voice_id=request.voice_id,
            render_succeeded=False,
            failure_reason="test_failure",
            setup_hint="Test hint",
        ),
    )

    def forbidden_qwen(config):
        raise AssertionError("adapter failure triggered fallback")

    monkeypatch.setitem(backends._BACKEND_FACTORIES, TTS_BACKEND_QWEN3, forbidden_qwen)
    output = tmp_path / "failed.wav"
    result = render_voiceover(
        text="Hello", output_path=output, backend_id="test_remote", config=cfg
    )
    assert result.render_succeeded is False
    assert result.failure_reason == "test_failure"
    assert result.setup_hint == "Test hint"
    assert not output.exists()
