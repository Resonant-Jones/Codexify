"""Voice client facade used by backend orchestration."""

from __future__ import annotations

import base64
import logging
from typing import Optional

import requests

from guardian.voice.config import get_voice_runtime_config
from guardian.voice.service import (
    VoiceProviderError,
    VoiceTimeoutError,
    VoiceValidationError,
    enforce_audio_input_limits,
    synthesize_text,
    transcribe_audio,
)

logger = logging.getLogger(__name__)


def _service_url() -> str | None:
    cfg = get_voice_runtime_config()
    return cfg.service_url


def transcribe(
    audio_bytes: bytes,
    mime_type: str | None,
    *,
    provider: str | None = None,
    timeout_seconds: int | None = None,
) -> str:
    cfg = get_voice_runtime_config()
    enforce_audio_input_limits(audio_bytes, mime_type, cfg=cfg)

    service_url = _service_url()
    if not service_url:
        return transcribe_audio(
            audio_bytes,
            mime_type,
            provider=provider,
            timeout_seconds=timeout_seconds,
        )

    endpoint = f"{service_url.rstrip('/')}/transcribe"
    files = {
        "audio_file": ("voice-input.wav", audio_bytes, mime_type or "audio/wav")
    }
    data = {}
    if provider:
        data["provider"] = provider

    timeout = float(timeout_seconds or cfg.stt_timeout_seconds)
    try:
        resp = requests.post(endpoint, files=files, data=data, timeout=timeout)
        resp.raise_for_status()
        payload = resp.json()
        text = str(payload.get("text") or "").strip()
        if not text:
            raise VoiceProviderError("service_stt_empty_text")
        return text
    except requests.Timeout as exc:
        raise VoiceTimeoutError("stt_timeout") from exc
    except requests.RequestException as exc:
        raise VoiceProviderError(f"service_stt_error:{exc}") from exc


def synthesize(
    text: str,
    *,
    provider: str | None = None,
    voice: str | None = None,
    output_format: str | None = None,
    timeout_seconds: int | None = None,
) -> tuple[bytes, str]:
    cfg = get_voice_runtime_config()
    service_url = _service_url()
    if not service_url:
        return synthesize_text(
            text,
            provider=provider,
            voice=voice,
            output_format=output_format,
            timeout_seconds=timeout_seconds,
        )

    endpoint = f"{service_url.rstrip('/')}/synthesize"
    timeout = float(timeout_seconds or cfg.tts_timeout_seconds)
    payload = {
        "text": text,
        "provider": provider,
        "voice": voice,
        "output_format": output_format,
    }

    try:
        resp = requests.post(endpoint, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout as exc:
        raise VoiceTimeoutError("tts_timeout") from exc
    except requests.RequestException as exc:
        raise VoiceProviderError(f"service_tts_error:{exc}") from exc

    raw = data.get("audio_b64")
    if not isinstance(raw, str) or not raw.strip():
        raise VoiceProviderError("service_tts_missing_audio")

    try:
        audio = base64.b64decode(raw)
    except Exception as exc:
        raise VoiceProviderError("service_tts_invalid_audio_payload") from exc

    fmt = str(
        data.get("format") or output_format or cfg.internal_format or "wav"
    )
    if len(audio) > cfg.output_max_bytes:
        raise VoiceValidationError(
            f"tts_audio_too_large:{len(audio)}>{cfg.output_max_bytes}"
        )
    return audio, fmt
