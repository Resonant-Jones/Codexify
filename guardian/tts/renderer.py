"""Headless local voiceover renderer."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path

from guardian.tts.backends.qwen3 import Qwen3TTSBackend
from guardian.tts.config import LocalTTSConfig, get_local_tts_config
from guardian.tts.contracts import (
    TTS_BACKEND_QWEN3,
    TTSBackendStatus,
    TTSRenderRequest,
    TTSRenderResult,
)
from guardian.tts.voiceover import (
    VoiceoverChunk,
    VoiceoverChunkKind,
    plan_voiceover_chunks,
)


@dataclass(frozen=True)
class VoiceoverRenderPlan:
    backend_id: str
    output_path: Path
    output_format: str
    voice_id: str
    chunks: list[VoiceoverChunk]

    def to_dict(self) -> dict[str, object]:
        return {
            "backend_id": self.backend_id,
            "output_path": str(self.output_path),
            "output_format": self.output_format,
            "voice_id": self.voice_id,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


@dataclass(frozen=True)
class VoiceoverRenderResult:
    plan: VoiceoverRenderPlan
    dry_run: bool
    render_succeeded: bool
    output_path: Path | None = None
    failure_reason: str | None = None
    setup_hint: str | None = None
    chunk_results: list[TTSRenderResult] = field(default_factory=list)
    bytes_written: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "plan": self.plan.to_dict(),
            "dry_run": self.dry_run,
            "render_succeeded": self.render_succeeded,
            "output_path": str(self.output_path) if self.output_path else None,
            "failure_reason": self.failure_reason,
            "setup_hint": self.setup_hint,
            "chunk_results": [result.to_dict() for result in self.chunk_results],
            "bytes_written": self.bytes_written,
        }


def build_voiceover_plan(
    *,
    text: str,
    output_path: Path,
    backend_id: str | None = None,
    output_format: str = "wav",
    voice_id: str | None = None,
    config: LocalTTSConfig | None = None,
) -> VoiceoverRenderPlan:
    cfg = config or get_local_tts_config()
    resolved_backend = (backend_id or cfg.backend_id).strip().lower()
    resolved_voice = (voice_id or cfg.default_voice or "default").strip()
    fmt = output_format.strip().lower()
    if fmt not in {"wav", "mp3"}:
        raise ValueError("output_format must be wav or mp3")
    return VoiceoverRenderPlan(
        backend_id=resolved_backend,
        output_path=output_path,
        output_format=fmt,
        voice_id=resolved_voice,
        chunks=plan_voiceover_chunks(text, config=cfg),
    )


def render_voiceover(
    *,
    text: str,
    output_path: Path,
    backend_id: str | None = None,
    output_format: str = "wav",
    voice_id: str | None = None,
    dry_run: bool = False,
    config: LocalTTSConfig | None = None,
) -> VoiceoverRenderResult:
    cfg = config or get_local_tts_config()
    plan = build_voiceover_plan(
        text=text,
        output_path=output_path,
        backend_id=backend_id,
        output_format=output_format,
        voice_id=voice_id,
        config=cfg,
    )

    if dry_run:
        return VoiceoverRenderResult(
            plan=plan,
            dry_run=True,
            render_succeeded=False,
        )

    if plan.backend_id != TTS_BACKEND_QWEN3:
        return VoiceoverRenderResult(
            plan=plan,
            dry_run=False,
            render_succeeded=False,
            failure_reason=f"unsupported_tts_backend:{plan.backend_id}",
            setup_hint="Use CODEXIFY_TTS_BACKEND=qwen3_tts for this adapter.",
        )

    backend = Qwen3TTSBackend(cfg)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_wav = output_path if plan.output_format == "wav" else output_path.with_suffix(".wav")

    chunk_results: list[TTSRenderResult] = []
    with tempfile.TemporaryDirectory(prefix="codexify-tts-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        wav_segments: list[Path] = []
        speech_index = 0
        for index, chunk in enumerate(plan.chunks):
            if chunk.kind == VoiceoverChunkKind.SPEECH:
                chunk_path = tmp_dir / f"chunk-{speech_index:04d}.wav"
                result = backend.render(
                    TTSRenderRequest(
                        text=chunk.text,
                        output_path=chunk_path,
                        backend_id=plan.backend_id,
                        output_format="wav",
                        voice_id=plan.voice_id,
                    )
                )
                chunk_results.append(result)
                if not result.render_succeeded or result.output_path is None:
                    return VoiceoverRenderResult(
                        plan=plan,
                        dry_run=False,
                        render_succeeded=False,
                        failure_reason=result.failure_reason,
                        setup_hint=result.setup_hint,
                        chunk_results=chunk_results,
                    )
                wav_segments.append(result.output_path)
                speech_index += 1
            else:
                silence_path = tmp_dir / f"pause-{index:04d}.wav"
                _write_silence_wav(silence_path, chunk.pause_ms)
                wav_segments.append(silence_path)

        _stitch_wav_segments(wav_segments, target_wav)

    final_path = target_wav
    if plan.output_format == "mp3":
        mp3_result = _transcode_wav_to_mp3(target_wav, output_path)
        if mp3_result is not None:
            return VoiceoverRenderResult(
                plan=plan,
                dry_run=False,
                render_succeeded=False,
                output_path=target_wav,
                failure_reason=mp3_result,
                setup_hint="Install local ffmpeg to enable MP3 export.",
                chunk_results=chunk_results,
                bytes_written=target_wav.stat().st_size,
            )
        final_path = output_path

    return VoiceoverRenderResult(
        plan=plan,
        dry_run=False,
        render_succeeded=True,
        output_path=final_path,
        chunk_results=chunk_results,
        bytes_written=final_path.stat().st_size,
    )


def _write_silence_wav(path: Path, pause_ms: int) -> None:
    sample_rate = 24000
    frames = int(sample_rate * max(pause_ms, 1) / 1000)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frames)


def _stitch_wav_segments(segments: list[Path], output_path: Path) -> None:
    if not segments:
        _write_silence_wav(output_path, 1)
        return

    with wave.open(str(segments[0]), "rb") as first:
        params = first.getparams()
        frames = [first.readframes(first.getnframes())]

    for segment in segments[1:]:
        with wave.open(str(segment), "rb") as wav_file:
            if wav_file.getnchannels() != params.nchannels:
                raise ValueError("wav channel mismatch while stitching voiceover")
            if wav_file.getsampwidth() != params.sampwidth:
                raise ValueError("wav sample width mismatch while stitching voiceover")
            if wav_file.getframerate() != params.framerate:
                segment = _resample_with_ffmpeg(segment, params.framerate)
                with wave.open(str(segment), "rb") as resampled:
                    frames.append(resampled.readframes(resampled.getnframes()))
            else:
                frames.append(wav_file.readframes(wav_file.getnframes()))

    with wave.open(str(output_path), "wb") as out:
        out.setparams(params)
        for frame in frames:
            out.writeframes(frame)


def _resample_with_ffmpeg(path: Path, sample_rate: int) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg_required_for_wav_resample")
    target = path.with_name(f"{path.stem}-resampled.wav")
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(path), "-ar", str(sample_rate), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "ffmpeg_resample_failed")
    return target


def _transcode_wav_to_mp3(wav_path: Path, mp3_path: Path) -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "mp3_export_unavailable:ffmpeg_missing"
    proc = subprocess.run(
        [ffmpeg, "-y", "-i", str(wav_path), str(mp3_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return f"mp3_export_failed:{proc.stderr.strip() or proc.returncode}"
    return None
