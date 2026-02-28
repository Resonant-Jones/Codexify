from __future__ import annotations

from typing import Optional

from guardian.providers.base import EmbeddingsProvider


class ProviderEmbeddingsAdapter:
    """Adapts a guardian EmbeddingsProvider to the MemoryOS embedder contract."""

    def __init__(
        self,
        provider: EmbeddingsProvider,
        *,
        model: str | None = None,
        name: str | None = None,
    ):
        self._provider = provider
        self.model_name = (model or "").strip() or None
        provider_name = (name or getattr(provider, "name", "") or "").strip()
        self.name = provider_name.lower() or "unknown"

    def embed(self, text: str) -> list[float]:
        vectors = self.embed_batch([text])
        return vectors[0] if vectors else []

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = [str(text or "") for text in texts]
        vectors = self._provider.embed(payload, model=self.model_name)
        # Always return plain list[list[float]] for downstream consistency.
        return [list(map(float, row)) for row in vectors]
