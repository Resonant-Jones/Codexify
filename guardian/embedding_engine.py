"""
Embedding Engine – modular and swappable.

Implements a deterministic dummy embedding generator for testing,
a live GPT-OSS backend integration via HTTP, and local embedding
models (BGE, Nomic).

The ``EMBEDDER`` constant can be set to:
- ``"dummy"``: returns deterministic vectors.
- ``"gpt_oss"``: fetches live embeddings from an external service.
- ``"bge"``: local BGE embedding model (bge-large-en-v1.5).
- ``"local"`` / ``"local_api"``: local sentence-transformer path via
  ``LOCAL_EMBED_MODEL`` when configured, otherwise the BGE default.
- ``"nomic"``: (placeholder) for future local Nomic integration.

The function ``get_embedding`` returns a list of floats compatible
with FAISS or any vector store.

Future work:
- Implement local Nomic embedding support.
- Add caching, batching, and retry logic.
"""

from __future__ import annotations

import hashlib
import logging
import os
import random
from typing import List, Optional

from guardian.utils.embed_paths import get_local_embed_model

logger = logging.getLogger(__name__)

_ENV_BACKEND = "CODEXIFY_EMBEDDINGS_BACKEND"
_ALLOWED_EMBEDDERS = {
    "dummy",
    "gpt_oss",
    "bge",
    "nomic",
    "local",
    "local_api",
}
_LOCAL_EMBEDDER_ALIASES = {"local", "local_api"}

# BGE model configuration
_BGE_MODEL_NAME = "BAAI/bge-large-en-v1.5"
_BGE_EMBEDDING_DIM = 1024

# Lazy-loaded model instance
_bge_model: object | None = None
_bge_model_name: str | None = None


def _normalize_embedder(value: str) -> str:
    embedder = value.strip().lower()
    if embedder in ("mock", "stub"):
        embedder = "dummy"
    if embedder in _LOCAL_EMBEDDER_ALIASES:
        embedder = "local"
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


def _resolve_local_model_name() -> str:
    return get_local_embed_model(strict=False) or _BGE_MODEL_NAME


def _dummy_embedding(text: str, dim: int = 768) -> list[float]:
    """
    Deterministic dummy embedding based on a hash of the input text.
    Returns a list of ``dim`` floats in the range [0, 1).
    """
    # Use a stable hash to seed the random generator
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return [rng.random() for _ in range(dim)]


def _get_bge_model(model_name: str | None = None):
    """
    Lazily load the BGE embedding model.
    Uses sentence-transformers for efficient local embedding generation.
    """
    global _bge_model, _bge_model_name
    resolved_model_name = (model_name or "").strip() or _BGE_MODEL_NAME
    if _bge_model is None or _bge_model_name != resolved_model_name:
        try:
            from sentence_transformers import SentenceTransformer

            _bge_model = SentenceTransformer(resolved_model_name)
            _bge_model_name = resolved_model_name
            logger.info(
                "Loaded embedding model: %s",
                resolved_model_name,
            )
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for BGE embeddings. "
                "Install with: pip install sentence-transformers"
            )
    return _bge_model


def _bge_embedding(text: str, *, model_name: str | None = None) -> list[float]:
    """
    Generate embedding using the BGE (BAAI/bge-large-en-v1.5) model.

    Args:
        text: Input text to embed.

    Returns:
        List of floats (1024 dimensions) representing the text embedding.
    """
    model = _get_bge_model(model_name)
    # Encode returns numpy array, convert to list of floats
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def get_embedding(text: str, *, embedder: str | None = None) -> list[float]:
    """
    Public API – returns an embedding vector for ``text``.
    Returns a deterministic dummy vector if ``EMBEDDER`` is set to
    ``"dummy"``, fetches live embeddings from GPT-OSS if set to
    ``"gpt_oss"``, or uses the local BGE/local model path if set to
    ``"bge"`` or ``"local"``.

    Args:
        text: Input text to embed.
        embedder: Optional embedder override.

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
    elif embedder == "bge":
        return _bge_embedding(text, model_name=_BGE_MODEL_NAME)
    elif embedder == "local":
        return _bge_embedding(text, model_name=_resolve_local_model_name())
    elif embedder == "nomic":
        # Nomic is not yet implemented - BGE is the recommended local alternative
        raise NotImplementedError(
            "Nomic embedder not implemented. Use 'bge' for local embeddings: "
            "set EMBEDDER=bge or CODEXIFY_EMBEDDINGS_BACKEND=bge"
        )
    else:
        raise ValueError(f"Unsupported embedder: {embedder}")
