from pathlib import Path
import sys

from guardian.tts.backends.qwen3 import Qwen3TTSBackend
from guardian.tts.config import LocalTTSConfig


def _cfg(
    tmp_path: Path,
    *,
    model_path: Path | None = None,
    render_script: Path | None = None,
) -> LocalTTSConfig:
    return LocalTTSConfig(
        backend_id="qwen3_tts",
        local_only=True,
        qwen3_model_path=model_path,
        qwen3_python=sys.executable,
        qwen3_render_script=render_script,
        output_dir=tmp_path,
        default_voice="default",
        chunk_max_chars=900,
        short_pause_ms=350,
        long_pause_ms=900,
    )


def test_qwen3_backend_reports_missing_model_path(tmp_path):
    backend = Qwen3TTSBackend(_cfg(tmp_path))

    probe = backend.health()

    assert probe.healthy is False
    assert probe.model_files_available is False
    assert probe.failure_reason == "qwen3_model_path_missing"
    assert "CODEXIFY_TTS_QWEN3_MODEL_PATH" in (probe.setup_hint or "")


def test_qwen3_backend_reports_missing_configured_model_dir(tmp_path):
    missing = tmp_path / "missing-model"
    backend = Qwen3TTSBackend(_cfg(tmp_path, model_path=missing))

    probe = backend.health()

    assert probe.healthy is False
    assert probe.model_files_available is False
    assert probe.failure_reason == "qwen3_model_path_missing"


def test_qwen3_backend_is_healthy_with_local_model_and_script(tmp_path):
    model_dir = tmp_path / "model"
    model_dir.mkdir()
    render_script = tmp_path / "render_qwen3.py"
    render_script.write_text("print('local renderer')", encoding="utf-8")
    backend = Qwen3TTSBackend(
        _cfg(tmp_path, model_path=model_dir, render_script=render_script)
    )

    probe = backend.health()

    assert probe.healthy is True
    assert probe.model_files_available is True
    assert probe.importable is True
