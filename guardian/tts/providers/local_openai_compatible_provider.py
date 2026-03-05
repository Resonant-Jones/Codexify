"""Local OpenAI-compatible TTS provider (Qwen/LFM/Ollama-style endpoints)."""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import requests

from ..tts_service import AuthenticationError, SynthesisError, TTSProvider

logger = logging.getLogger(__name__)


class LocalOpenAICompatibleProvider(TTSProvider):
    """TTS provider for local OpenAI-compatible `/audio/speech` endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (
            base_url
            or os.getenv("CODEXIFY_LOCAL_VOICE_BASE_URL")
            or os.getenv("CODEXIFY_LOCAL_TTS_BASE_URL")
            or os.getenv("LOCAL_BASE_URL")
            or "http://localhost:11434/v1"
        ).rstrip("/")
        self.api_key = api_key or os.getenv("LOCAL_API_KEY") or "local"
        self.model = (
            model
            or os.getenv("CODEXIFY_LOCAL_TTS_MODEL")
            or os.getenv("LOCAL_TTS_MODEL")
            or "qwen-tts"
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        }

    def list_voices(self) -> list[str]:
        raw = (os.getenv("CODEXIFY_LOCAL_TTS_VOICES") or "").strip()
        if raw:
            return [v.strip() for v in raw.split(",") if v.strip()]
        return ["alloy", "verse", "shimmer"]

    def synthesize(self, text: str, voice: str) -> bytes:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        endpoint = f"{self.base_url}/audio/speech"
        timeout = float(os.getenv("CODEXIFY_TTS_TIMEOUT_SECONDS", "30"))

        payload = {
            "model": self.model,
            "input": text,
            "voice": voice or "alloy",
            "response_format": "wav",
            "format": "wav",
        }

        try:
            response = requests.post(
                endpoint,
                headers=self._headers(),
                json=payload,
                timeout=timeout,
            )
            if response.status_code in {401, 403}:
                raise AuthenticationError(
                    "Local OpenAI-compatible TTS auth failed"
                )
            response.raise_for_status()
            if not response.content:
                raise SynthesisError("Empty audio response from local TTS")
            return response.content
        except AuthenticationError:
            raise
        except requests.RequestException as exc:
            raise SynthesisError(f"Local OpenAI-compatible TTS failed: {exc}")
