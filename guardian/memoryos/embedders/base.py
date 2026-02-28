from __future__ import annotations

from typing import Optional, Protocol


class MemoryOSEmbedder(Protocol):
    """Minimal embedding interface for MemoryOS internals."""

    name: str

    def embed(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


def get_embedder_provider_name(embedder: MemoryOSEmbedder) -> str:
    name = str(getattr(embedder, "name", "") or "").strip().lower()
    return name or "unknown"


def get_embedder_model_name(embedder: MemoryOSEmbedder) -> str | None:
    for attr in ("model_name", "model"):
        value = getattr(embedder, attr, None)
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                return cleaned
    return None
