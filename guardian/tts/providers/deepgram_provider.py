"""
Deepgram TTS Provider
---------------------
Implementation of :class:`~guardian.tts.tts_service.TTSProvider` backed by the
Deepgram Aura text-to-speech API.

Provider-agnostic notes
-----------------------
Nothing in this module leaks into Guardian runtime semantics. The provider is
selected purely by name through the registry in
:mod:`guardian.tts.tts_manager`; the native container it emits is declared on
the class (``native_output_format``) instead of being hardcoded by provider
name in the voice runtime.
"""

from __future__ import annotations

from guardian.metering.runtime import deny_unqualified_spend

import logging
import os
from typing import List, Optional

import requests

from guardian.core.egress import EgressDeniedError, assert_egress_allowed

from ..tts_service import (
    NATIVE_OUTPUT_FORMAT_MP3,
    AuthenticationError,
    SynthesisError,
    TTSProvider,
    VoiceNotFoundError,
)

logger = logging.getLogger(__name__)

#: Deepgram Aura English voice catalogue (Aura 2 family).
#:
#: The identifier encodes family, voice and language: ``aura-2-thalia-en`` is
#: Thalia from Aura 2 speaking English. This catalogue is static on purpose:
#: the provider must be able to enumerate voices without a network round trip,
#: and the Aura-2 English set is stable.
AURA_VOICE_IDS: tuple[str, ...] = (
    "aura-2-thalia-en",
    "aura-2-andromeda-en",
    "aura-2-helena-en",
    "aura-2-apollo-en",
    "aura-2-arcas-en",
    "aura-2-aries-en",
    "aura-2-amalthea-en",
    "aura-2-asteria-en",
    "aura-2-athena-en",
    "aura-2-atlas-en",
    "aura-2-aurora-en",
    "aura-2-callista-en",
    "aura-2-cora-en",
    "aura-2-cordelia-en",
    "aura-2-delia-en",
    "aura-2-draco-en",
    "aura-2-electra-en",
    "aura-2-harmonia-en",
    "aura-2-hera-en",
    "aura-2-hermes-en",
    "aura-2-hyperion-en",
    "aura-2-iris-en",
    "aura-2-janus-en",
    "aura-2-juno-en",
    "aura-2-jupiter-en",
    "aura-2-luna-en",
    "aura-2-mars-en",
    "aura-2-minerva-en",
    "aura-2-neptune-en",
    "aura-2-odysseus-en",
    "aura-2-ophelia-en",
    "aura-2-orion-en",
    "aura-2-orpheus-en",
    "aura-2-pandora-en",
    "aura-2-phoebe-en",
    "aura-2-pluto-en",
    "aura-2-saturn-en",
    "aura-2-selene-en",
    "aura-2-theia-en",
    "aura-2-vesta-en",
    "aura-2-zeus-en",
)

#: Aura rejects a synthesis request longer than this many characters.
AURA_MAX_REQUEST_CHARS = 2000


class DeepgramProvider(TTSProvider):
    """Deepgram Aura implementation of :class:`TTSProvider`."""

    API_BASE = "https://api.deepgram.com/v1"
    DEFAULT_MODEL = "aura-2-thalia-en"
    DEFAULT_ENCODING = "mp3"

    #: Deepgram returns the encoded audio stream directly; mp3 is the
    #: container this provider asks for, so the runtime must not assume WAV.
    native_output_format = NATIVE_OUTPUT_FORMAT_MP3

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        try:
            assert_egress_allowed("deepgram")
        except EgressDeniedError as exc:
            raise SynthesisError(str(exc)) from exc

        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise AuthenticationError("Deepgram API key not found")

        self.model = model or os.getenv("DEEPGRAM_TTS_MODEL") or self.DEFAULT_MODEL
        self.base_url = (
            base_url or os.getenv("DEEPGRAM_API_BASE_URL") or self.API_BASE
        ).rstrip("/")
        self.timeout_seconds = float(
            os.getenv("CODEXIFY_TTS_TIMEOUT_SECONDS", "60")
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def list_voices(self) -> List[str]:
        """Return the Aura voice identifiers available to this provider."""
        return list(AURA_VOICE_IDS)

    def synthesize(self, text: str, voice: str) -> bytes:
        """
        Synthesize text to speech.

        Args:
            text: The text to synthesize
            voice: Aura model identifier (e.g. ``aura-2-thalia-en``)

        Returns:
            bytes: Audio data in the provider's native container (mp3)

        Raises:
            AuthenticationError: If the provider rejects the credential
            VoiceNotFoundError: If the requested voice is not an Aura voice
            SynthesisError: If synthesis fails
        """
        deny_unqualified_spend()
        content = (text or "").strip()
        if not content:
            raise SynthesisError("Deepgram synthesis requires non-empty text")

        selected_voice = (voice or self.model).strip()
        if not selected_voice:
            raise VoiceNotFoundError("Deepgram requires a voice model identifier")

        audio = b"".join(
            self._synthesize_chunk(chunk, selected_voice)
            for chunk in self._chunk_text(content)
        )
        if not audio:
            raise SynthesisError("Deepgram returned an empty audio payload")
        return audio

    def _synthesize_chunk(self, chunk: str, voice: str) -> bytes:
        deny_unqualified_spend()
        endpoint = f"{self.base_url}/speak"
        params = {
            "model": voice,
            "encoding": self.DEFAULT_ENCODING,
        }

        try:
            response = requests.post(
                endpoint,
                headers=self._headers(),
                params=params,
                json={"text": chunk},
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise SynthesisError("Deepgram synthesis timed out") from exc
        except requests.RequestException as exc:
            raise SynthesisError(f"Deepgram synthesis request failed: {exc}") from exc

        status = response.status_code
        if status in (401, 403):
            raise AuthenticationError("Deepgram rejected the API credential")
        if status == 404:
            raise VoiceNotFoundError(f"Deepgram voice not found: {voice}")
        if status >= 400:
            raise SynthesisError(
                f"Deepgram synthesis failed with status {status}: "
                f"{self._error_detail(response)}"
            )

        return response.content

    @staticmethod
    def _error_detail(response) -> str:
        try:
            payload = response.json()
        except Exception:
            return (response.text or "")[:200]
        if isinstance(payload, dict):
            err = payload.get("err_msg") or payload.get("error") or payload.get("message")
            if err:
                return str(err)[:200]
        return (response.text or "")[:200]

    @staticmethod
    def _chunk_text(
        text: str, max_chars: int = AURA_MAX_REQUEST_CHARS
    ) -> List[str]:
        """
        Split text into chunks Aura will accept.

        Prefers a sentence boundary, then whitespace, then a hard cut so a
        single oversized token can never produce an over-length request.
        """
        if len(text) <= max_chars:
            return [text]

        chunks: List[str] = []
        remaining = text.strip()
        while len(remaining) > max_chars:
            window = remaining[:max_chars]
            cut = window.rfind(". ")
            if cut < max_chars // 2:
                cut = window.rfind(" ")
            if cut <= 0:
                chunks.append(remaining[:max_chars].strip())
                remaining = remaining[max_chars:].strip()
                continue
            chunks.append(remaining[: cut + 1].strip())
            remaining = remaining[cut + 1 :].strip()

        if remaining:
            chunks.append(remaining)
        return [chunk for chunk in chunks if chunk]
