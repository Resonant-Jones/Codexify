"""Base contract for TTS backend adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from guardian.tts.contracts import (
    TTSBackendInfo,
    TTSHealthProbe,
    TTSRenderRequest,
    TTSRenderResult,
)


class TTSBackend(ABC):
    """Backend island mounted behind Codexify's shared TTS adapter."""

    @abstractmethod
    def info(self) -> TTSBackendInfo:
        """Return static backend metadata."""

    @abstractmethod
    def health(self) -> TTSHealthProbe:
        """Return only readiness evidence this adapter has established."""

    @abstractmethod
    def render(self, request: TTSRenderRequest) -> TTSRenderResult:
        """Render text to a local audio file."""

    def render_many(self, requests: list[TTSRenderRequest]) -> list[TTSRenderResult]:
        """Render in request order; adapters may override to batch efficiently."""

        return [self.render(request) for request in requests]
