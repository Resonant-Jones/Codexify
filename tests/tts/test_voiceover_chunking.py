from pathlib import Path

from guardian.tts.config import LocalTTSConfig
from guardian.tts.renderer import render_voiceover
from guardian.tts.voiceover import VoiceoverChunkKind, plan_voiceover_chunks


def _cfg(tmp_path: Path) -> LocalTTSConfig:
    return LocalTTSConfig(
        backend_id="qwen3_tts",
        local_only=True,
        qwen3_model_path=None,
        qwen3_python="python",
        qwen3_render_script=None,
        output_dir=tmp_path,
        default_voice="default",
        chunk_max_chars=24,
        short_pause_ms=250,
        long_pause_ms=800,
    )


def test_voiceover_chunking_preserves_pause_marker(tmp_path):
    chunks = plan_voiceover_chunks(
        "Open the scene. [pause] Then continue.",
        config=_cfg(tmp_path),
    )

    assert [chunk.kind for chunk in chunks] == [
        VoiceoverChunkKind.SPEECH,
        VoiceoverChunkKind.LONG_PAUSE,
        VoiceoverChunkKind.SPEECH,
    ]
    assert chunks[1].pause_ms == 800


def test_voiceover_chunking_preserves_breath_marker(tmp_path):
    chunks = plan_voiceover_chunks(
        "Think about it... then answer.",
        config=_cfg(tmp_path),
    )

    assert [chunk.kind for chunk in chunks] == [
        VoiceoverChunkKind.SPEECH,
        VoiceoverChunkKind.SHORT_PAUSE,
        VoiceoverChunkKind.SPEECH,
    ]
    assert chunks[1].pause_ms == 250


def test_voiceover_chunking_splits_long_text(tmp_path):
    chunks = plan_voiceover_chunks(
        "This sentence is intentionally long enough to require chunking.",
        config=_cfg(tmp_path),
    )

    speech_chunks = [
        chunk for chunk in chunks if chunk.kind == VoiceoverChunkKind.SPEECH
    ]
    assert len(speech_chunks) > 1
    assert all(len(chunk.text) <= 24 for chunk in speech_chunks)


def test_dry_run_does_not_generate_audio(tmp_path):
    output = tmp_path / "dry-run.generated.wav"

    result = render_voiceover(
        text="Hello... world [pause] done.",
        output_path=output,
        backend_id="qwen3_tts",
        output_format="wav",
        dry_run=True,
        config=_cfg(tmp_path),
    )

    assert result.dry_run is True
    assert result.render_succeeded is False
    assert output.exists() is False
    assert result.plan.chunks


def test_renderer_does_not_import_chat_memory_retrieval_or_persona(monkeypatch, tmp_path):
    blocked = {
        "guardian.core.chat_completion_service",
        "guardian.context.broker",
        "guardian.memoryos.retriever",
        "guardian.routes.persona_profiles",
    }
    original_import = __import__

    def guarded_import(name, *args, **kwargs):
        if name in blocked:
            raise AssertionError(f"renderer imported forbidden module {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", guarded_import)

    result = render_voiceover(
        text="Isolation dry run.",
        output_path=tmp_path / "isolated.generated.wav",
        backend_id="qwen3_tts",
        output_format="wav",
        dry_run=True,
        config=_cfg(tmp_path),
    )

    assert result.dry_run is True
