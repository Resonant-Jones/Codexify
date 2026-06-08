"""Base contract for local TTS backend islands."""

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
        """Probe local install/model/import readiness."""

    @abstractmethod
    def render(self, request: TTSRenderRequest) -> TTSRenderResult:
        """Render text to a local audio file."""
