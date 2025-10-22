"""Vector store factory that chooses an implementation via configuration."""

from __future__ import annotations

import os
from typing import Any

from . import VectorStore


def get_vector_store(*, store_name: str | None = None, **kwargs: Any) -> VectorStore:
    """Instantiate the configured vector store backend.

    Args:
        store_name: Optional explicit backend name. When omitted, the
            ``VECTOR_STORE`` environment variable is consulted.
        **kwargs: Extra keyword arguments forwarded to the store constructor.

    Returns:
        A concrete :class:`VectorStore` implementation.

    Raises:
        ValueError: If the backend name is unknown.
    """

    configured = (store_name or os.getenv("VECTOR_STORE", "pgvector")).strip().lower()

    if configured == "pgvector":
        from .pgvector_store import PGVectorStore

        return PGVectorStore(**kwargs)

    if configured == "chroma":
        from .chroma_store import ChromaVectorStore

        return ChromaVectorStore(**kwargs)

    raise ValueError(
        "Unsupported VECTOR_STORE backend. Expected 'pgvector' or 'chroma', "
        f"got '{configured}'."
    )


__all__ = ["get_vector_store"]
