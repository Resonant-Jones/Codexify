from __future__ import annotations

import os

from guardian.core.config import (
    get_settings,
    validate_embedding_provider_config,
)
from guardian.providers.registry import ProviderRegistry

from .local_embedder import LocalEmbedder
from .openai_embedder import OpenAIEmbedder
from .provider_adapter import ProviderEmbeddingsAdapter

_LOCAL_ALIASES = {"local", "local_api"}


def normalize_embedder_provider(provider: str | None) -> str:
    normalized = (provider or "").strip().lower()
    if not normalized:
        normalized = (os.getenv("EMBEDDER_PROVIDER") or "").strip().lower()
    if normalized in _LOCAL_ALIASES:
        return "local"
    return normalized


def _resolve_openai_embed_model(settings) -> str:
    model = (
        os.getenv("OPENAI_EMBED_MODEL")
        or os.getenv("OPENAI_EMBEDDING_MODEL")
        or (getattr(settings, "EMBEDDING_MODEL", None) or "")
    ).strip()
    if not model:
        raise ValueError(
            "OpenAI embedder requires OPENAI_EMBED_MODEL or OPENAI_EMBEDDING_MODEL."
        )
    return model


def build_memoryos_embedder(provider: str | None = None):
    """Resolve and construct the MemoryOS embedder from provider settings."""
    settings = get_settings()
    resolved = normalize_embedder_provider(
        provider or settings.EMBEDDER_PROVIDER
    )
    if not resolved:
        raise ValueError(
            "EMBEDDER_PROVIDER is not configured. Set EMBEDDER_PROVIDER in environment or config."
        )

    validate_embedding_provider_config(settings, provider_override=resolved)

    if resolved == "local":
        return LocalEmbedder()

    if resolved == "openai":
        return OpenAIEmbedder(
            api_key=settings.OPENAI_API_KEY,
            model=_resolve_openai_embed_model(settings),
        )

    registry = ProviderRegistry()
    provider_impl = registry.get_embeddings(resolved)
    return ProviderEmbeddingsAdapter(
        provider_impl,
        model=(getattr(settings, "EMBEDDING_MODEL", None) or "").strip()
        or None,
        name=resolved,
    )
