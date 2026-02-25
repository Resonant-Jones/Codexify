"""Model-agnostic voice execution layer (STT/TTS only).

This module intentionally excludes thread/task orchestration concerns.
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

import requests

from guardian.tts.tts_manager import TTSManager
from guardian.voice.config import VoiceRuntimeConfig, get_voice_runtime_config
from guardian.voice.manifest import load_manifest

logger = logging.getLogger(__name__)


class VoiceServiceError(RuntimeError):
    """Base voice service exception."""


class VoiceValidationError(VoiceServiceError):
    """Input/output validation failure."""


class VoiceTimeoutError(VoiceServiceError):
    """Execution timeout failure."""


class VoiceProviderError(VoiceServiceError):
    """Provider-level execution failure."""


def _openai_endpoint(base_url: str, suffix: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}{suffix}"
    return f"{base}/v1{suffix}"


def detect_audio_duration_seconds(
    audio_bytes: bytes, mime_type: str | None
) -> float | None:
    """Best-effort duration detection for size guardrails."""
    mime = (mime_type or "").strip().lower()

    if mime in {"audio/wav", "audio/x-wav"}:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav_fp:
                frames = wav_fp.getnframes()
                rate = wav_fp.getframerate()
                if rate > 0:
                    return float(frames) / float(rate)
        except Exception:
            return None

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".audio") as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        cmd = [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            tmp_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            return None
        payload = json.loads(proc.stdout or "{}")
        raw = (
            payload.get("format", {}).get("duration")
            if isinstance(payload, dict)
            else None
        )
        if raw is None:
            return None
        return float(raw)
    except Exception:
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def enforce_audio_input_limits(
    audio_bytes: bytes,
    mime_type: str | None,
    *,
    cfg: VoiceRuntimeConfig | None = None,
) -> float | None:
    config = cfg or get_voice_runtime_config()
    size = len(audio_bytes)
    if size <= 0:
        raise VoiceValidationError("empty_audio")
    if size > config.input_max_bytes:
        raise VoiceValidationError(
            f"audio_too_large:{size}>{config.input_max_bytes}"
        )

    duration = detect_audio_duration_seconds(audio_bytes, mime_type)
    if duration is None:
        raise VoiceValidationError(
            "audio_duration_unknown:provide wav or install ffprobe"
        )
    if duration > config.max_duration_seconds:
        raise VoiceValidationError(
            f"audio_too_long:{duration:.2f}>{config.max_duration_seconds}"
        )
    return duration


def _request_transcription_openai_compatible(
    *,
    base_url: str,
    api_key: str,
    model: str,
    audio_bytes: bytes,
    mime_type: str,
    timeout_seconds: int,
) -> str:
    endpoint = _openai_endpoint(base_url, "/audio/transcriptions")
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("voice-input.wav", audio_bytes, mime_type or "audio/wav")}
    data = {
        "model": model,
        "response_format": "json",
    }

    try:
        resp = requests.post(
            endpoint,
            headers=headers,
            files=files,
            data=data,
            timeout=float(timeout_seconds),
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.Timeout as exc:
        raise VoiceTimeoutError("stt_timeout") from exc
    except requests.RequestException as exc:
        raise VoiceProviderError(f"stt_provider_error:{exc}") from exc
    except Exception as exc:
        raise VoiceProviderError(f"stt_parse_error:{exc}") from exc

    text = str(payload.get("text") or "").strip()
    if not text:
        raise VoiceProviderError("stt_empty_transcript")
    return text


def transcribe_audio(
    audio_bytes: bytes,
    mime_type: str | None,
    *,
    provider: str | None = None,
    timeout_seconds: int | None = None,
) -> str:
    """Transcribe audio bytes using configured STT provider."""
    cfg = get_voice_runtime_config()
    active_provider = (provider or cfg.stt_provider).strip().lower()
    timeout = int(timeout_seconds or cfg.stt_timeout_seconds)

    if active_provider == "mock":
        return (
            os.getenv("CODEXIFY_STT_MOCK_TEXT") or "mock transcript"
        ).strip()

    if active_provider == "whisper_local":
        base_url = (
            os.getenv("CODEXIFY_STT_BASE_URL")
            or os.getenv("CODEXIFY_LOCAL_STT_BASE_URL")
            or os.getenv("LOCAL_BASE_URL")
            or "http://localhost:11434"
        )
        api_key = os.getenv("LOCAL_API_KEY") or "local"
        model = os.getenv("CODEXIFY_STT_MODEL") or "whisper-small.en"
        return _request_transcription_openai_compatible(
            base_url=base_url,
            api_key=api_key,
            model=model,
            audio_bytes=audio_bytes,
            mime_type=mime_type or "audio/wav",
            timeout_seconds=timeout,
        )

    if active_provider == "openai":
        base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com"
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            raise VoiceProviderError("openai_api_key_missing")
        model = os.getenv("CODEXIFY_STT_MODEL") or "whisper-1"
        return _request_transcription_openai_compatible(
            base_url=base_url,
            api_key=api_key,
            model=model,
            audio_bytes=audio_bytes,
            mime_type=mime_type or "audio/wav",
            timeout_seconds=timeout,
        )

    raise VoiceProviderError(f"unsupported_stt_provider:{active_provider}")


def _transcode_with_ffmpeg(
    audio_bytes: bytes,
    *,
    source_ext: str,
    target_ext: str,
) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise VoiceProviderError("ffmpeg_not_available_for_transcode")

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{source_ext}"
    ) as src:
        src.write(audio_bytes)
        src_path = Path(src.name)

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{target_ext}"
    ) as dst:
        dst_path = Path(dst.name)

    try:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(src_path),
            str(dst_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise VoiceProviderError(
                f"ffmpeg_transcode_failed:{proc.stderr.strip() or proc.returncode}"
            )
        return dst_path.read_bytes()
    finally:
        for path in (src_path, dst_path):
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def _provider_default_format(provider: str) -> str:
    if provider in {"elevenlabs", "minimax"}:
        return "mp3"
    return "wav"


def synthesize_text(
    text: str,
    *,
    provider: str | None = None,
    voice: str | None = None,
    output_format: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[bytes, str]:
    """Synthesize text and return `(audio_bytes, format)`."""
    cfg = get_voice_runtime_config()
    active_provider = (provider or cfg.tts_provider).strip().lower()
    fmt_requested = (
        (output_format or cfg.internal_format or "wav").strip().lower()
    )

    if timeout_seconds is not None:
        os.environ.setdefault(
            "CODEXIFY_TTS_TIMEOUT_SECONDS", str(timeout_seconds)
        )

    manager = TTSManager()
    if not voice:
        voices = manager.list_voices(active_provider)
        voice = voices[0] if voices else "alloy"

    audio = manager.synthesize(
        text=text, voice=voice, provider_name=active_provider
    )
    source_fmt = _provider_default_format(active_provider)

    if source_fmt != fmt_requested:
        audio = _transcode_with_ffmpeg(
            audio,
            source_ext=source_fmt,
            target_ext=fmt_requested,
        )
        source_fmt = fmt_requested

    if len(audio) > cfg.output_max_bytes:
        raise VoiceValidationError(
            f"tts_audio_too_large:{len(audio)}>{cfg.output_max_bytes}"
        )

    return audio, source_fmt


def list_voice_models() -> dict[str, Any]:
    """Return manifest model metadata for diagnostics."""
    manifest = load_manifest()
    return {
        "version": manifest.get("version"),
        "models": manifest.get("models", []),
    }
