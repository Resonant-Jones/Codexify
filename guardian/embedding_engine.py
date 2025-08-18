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
import random
from typing import List

# Switch between back‑ends.  For the MVP we use the dummy
# implementation, but the constant makes it easy to
# swap out later.
EMBEDDER = "dummy"  # Options: "dummy", "gpt_oss", "nomic"


def _dummy_embedding(text: str, dim: int = 768) -> List[float]:
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


def get_embedding(text: str) -> List[float]:
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
    if EMBEDDER == "dummy":
        return _dummy_embedding(text)
    elif EMBEDDER == "gpt_oss":
        import requests

        try:
            response = requests.post(
                "http://localhost:8000/embed",  # Change this URL if your GPT-OSS embed endpoint differs
                json={"text": text},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            return result["embedding"]
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch embedding from GPT-OSS: {e}")
    elif EMBEDDER == "nomic":
        # TODO: Call local Nomic model (e.g. via huggingface
        # or a local server) and return the embedding.
        raise NotImplementedError("Nomic embedder not implemented yet.")
    else:
        raise ValueError(f"Unsupported embedder: {EMBEDDER}")
