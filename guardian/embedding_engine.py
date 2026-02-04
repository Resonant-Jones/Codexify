"""
Embedding Engine – modular and swappable.

Implements a deterministic dummy embedding generator for testing,
a live GPT‑OSS backend integration via HTTP, and a placeholder
for a Nomic local model.

The ``EMBEDDER`` constant can be set to:
- ``"dummy"``: returns deterministic vectors.
- ``"gpt_oss"``: fetches live embeddings from an external service.
- ``"nomic"``: (placeholder) for future local Nomic integration.

The function ``get_embedding`` returns a list of floats compatible
with FAISS or any vector store.

Future work:
- Implement local Nomic embedding support.
- Add caching, batching, and retry logic.
"""

from __future__ import annotations

import hashlib
import os
import random
from typing import List

_ENV_BACKEND = "CODEXIFY_EMBEDDINGS_BACKEND"
_ALLOWED_EMBEDDERS = {"dummy", "gpt_oss", "nomic"}


def _normalize_embedder(value: str) -> str:
    embedder = value.strip().lower()
    if embedder == "mock":
        embedder = "dummy"
    if embedder not in _ALLOWED_EMBEDDERS:
        raise ValueError(f"Unsupported embedder: {embedder}")
    return embedder


def _resolve_embedder(value: str | None) -> str:
    if value and value.strip():
        return _normalize_embedder(value)
    env_value = (
        os.getenv(_ENV_BACKEND)
        or os.getenv("EMBEDDING_BACKEND")
        or os.getenv("EMBEDDER")
        or ""
    )
    if not env_value:
        return "dummy"
    return _normalize_embedder(env_value)


def _dummy_embedding(text: str, dim: int = 768) -> list[float]:
    """
    Deterministic dummy embedding based on a hash of the input text.
    Returns a list of ``dim`` floats in the range [0, 1).
    """
    # Use a stable hash to seed the random generator
    # Compute a deterministic seed from the text
    # Compute a deterministic seed from the text
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dim)]


def get_embedding(text: str, *, embedder: str | None = None) -> list[float]:
    """
    Public API – returns an embedding vector for ``text``.
    Returns a deterministic dummy vector if ``EMBEDDER`` is set to
    ``"dummy"``, or fetches live embeddings from GPT-OSS if set to
    ``"gpt_oss"``. The Nomic backend is not yet implemented.

    Args:
        text: Input text to embed.

    Returns:
        List[float]: Embedding vector.
    """
    embedder = _resolve_embedder(embedder)
    if embedder == "dummy":
        return _dummy_embedding(text)
    elif embedder == "gpt_oss":
        import requests

        try:
            response = requests.post(
                "http://localhost:8000/embed",  # Change this URL if your GPT-OSS embed endpoint differs
                json={"text": text},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            return result["embedding"]
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch embedding from GPT-OSS: {e}")
    elif embedder == "nomic":
        # TODO: Call local Nomic model (e.g. via huggingface
        # or a local server) and return the embedding.
        raise NotImplementedError("Nomic embedder not implemented yet.")
    else:
        raise ValueError(f"Unsupported embedder: {embedder}")
